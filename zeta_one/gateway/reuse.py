"""No re-rolling a decision (security.md, S3).

A proposal with the same fingerprint (agent, counterparty, payment method, amount, currency, bill)
under the same configuration within 24 hours reuses the earlier risk result instead of asking the
models again, provided the payee's payment methods haven't changed since. Identity, authorization
and tier 0 still run every time: the earlier result is reused only if tier 0 finds exactly what it
found then, so a hard flag raised since (a bill that opened, new instruction text) is never skipped.
The reused result names the decision it came from in `risk.reused_from` and carries no token usage,
since no model was called for it.

Changing the amount by a cent is a new proposal, so an agent could re-roll that way. After
MAX_FRESH_ASSESSMENTS fresh assessments that reached a model for the same agent, payee and payment
method within the window, a further different proposal skips the models: tier 0 still runs, and the policy challenges
it (`risk.repeat_limit_reached`).
"""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from zeta_one.contracts import (
    Configuration,
    Context,
    EvidenceRecord,
    IdentityEvidence,
    Proposal,
    RiskEvidence,
    Tier0Output,
)
from zeta_one.gateway.ledger import payment_method_state
from zeta_one.gateway.pipeline import Engine
from zeta_one.risk import assess

WINDOW = timedelta(hours=24)
MAX_FRESH_ASSESSMENTS = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS risk_results (
    decision_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    configuration TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payment_method_state TEXT NOT NULL,
    risk TEXT NOT NULL,
    payee_key TEXT
);
CREATE INDEX IF NOT EXISTS risk_results_lookup ON risk_results (fingerprint, configuration, created_at);
"""


def fingerprint(agent_id: str | None, proposal: Proposal) -> str:
    parts = [
        agent_id,
        proposal.counterparty_id,
        proposal.payment_method_id,
        proposal.amount.amount,
        proposal.amount.currency,
        proposal.bill_id,
    ]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def payee_key(agent_id: str | None, proposal: Proposal) -> str:
    """Agent, payee and payment method: what stays the same while an agent varies the amount."""
    parts = [agent_id, proposal.counterparty_id, proposal.payment_method_id]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def _configuration_key(configuration: Configuration) -> str:
    return configuration.model_dump_json()


def _same_tier0(fresh: Tier0Output, risk: RiskEvidence) -> bool:
    earlier = next((result for result in risk.tier_results if result.tier == "tier0"), None)
    features = {name: feature.model_dump(mode="json") for name, feature in fresh.features.items()}
    return (
        earlier is not None
        and fresh.result.level == earlier.level
        and features == {name: feature.model_dump(mode="json") for name, feature in risk.features.items()}
    )


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


class RiskReuse:
    """An `Engine.assess_risk` that reuses recent results; `remember` stores one once it is decided."""

    def __init__(self, connection: sqlite3.Connection, window: timedelta = WINDOW):
        self._db = connection
        self._window = window
        self._db.executescript(SCHEMA)
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(risk_results)")}
        if "payee_key" not in columns:  # a gateway file from before the repeat limit
            with self._db:
                self._db.execute("ALTER TABLE risk_results ADD COLUMN payee_key TEXT")

    def __call__(
        self, engine: Engine, proposal: Proposal, context: Context, now: datetime, identity: IdentityEvidence
    ) -> RiskEvidence:
        earlier = self._find(identity.claimed_agent_id, proposal, context, now, engine.configuration)
        if earlier is None:
            if self._fresh_count(identity.claimed_agent_id, proposal, now, engine.configuration) >= MAX_FRESH_ASSESSMENTS:
                tier0_only = assess.assess(proposal, context, now, engine.tier0, {}, Configuration(tiers=["tier0"]))
                return tier0_only.model_copy(update={"repeat_limit_reached": True})
            return engine.run_tiers(proposal, context, now, identity)
        decision_id, risk = earlier
        if not _same_tier0(engine.tier0(proposal, context, now), risk):
            return engine.run_tiers(proposal, context, now, identity)
        results = [result.model_copy(update={"usage": None, "latency_ms": None}) for result in risk.tier_results]
        return risk.model_copy(update={"reused_from": decision_id, "tier_results": results})

    def remember(self, record: EvidenceRecord, proposal: Proposal | None, context: Context | None) -> None:
        """Keep a decision's risk result for reuse, unless risk didn't run or was itself reused."""
        risk = record.risk
        if proposal is None or context is None or not risk.tiers_run or risk.reused_from or risk.repeat_limit_reached:
            return
        with self._db:
            self._db.execute(
                """INSERT OR REPLACE INTO risk_results
                   (decision_id, fingerprint, configuration, created_at, payment_method_state, risk, payee_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.decision_id,
                    fingerprint(record.identity.claimed_agent_id, proposal),
                    _configuration_key(record.configuration),
                    _iso(record.created_at),
                    json.dumps(payment_method_state(context)),
                    risk.model_dump_json(by_alias=True),
                    payee_key(record.identity.claimed_agent_id, proposal),
                ),
            )

    def _fresh_count(self, agent_id: str | None, proposal: Proposal, now: datetime, configuration: Configuration) -> int:
        """Fresh assessments in the window that reached a model; tier-0-only ones re-roll nothing."""
        rows = self._db.execute(
            """SELECT risk FROM risk_results
               WHERE payee_key = ? AND configuration = ? AND created_at > ? AND created_at <= ?""",
            (payee_key(agent_id, proposal), _configuration_key(configuration), _iso(now - self._window), _iso(now)),
        ).fetchall()
        return sum(any(tier != "tier0" for tier in RiskEvidence.model_validate_json(row["risk"]).tiers_run)
                   for row in rows)

    def _find(
        self, agent_id: str | None, proposal: Proposal, context: Context, now: datetime, configuration: Configuration
    ) -> tuple[str, RiskEvidence] | None:
        row = self._db.execute(
            """SELECT decision_id, payment_method_state, risk FROM risk_results
               WHERE fingerprint = ? AND configuration = ? AND created_at > ? AND created_at <= ?
               ORDER BY created_at DESC LIMIT 1""",
            (fingerprint(agent_id, proposal), _configuration_key(configuration), _iso(now - self._window), _iso(now)),
        ).fetchone()
        if row is None or json.loads(row["payment_method_state"]) != payment_method_state(context):
            return None
        return row["decision_id"], RiskEvidence.model_validate_json(row["risk"])
