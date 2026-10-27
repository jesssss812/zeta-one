"""No re-rolling a decision (security.md, S3).

A proposal with the same fingerprint (agent, counterparty, payment method, amount, currency, bill)
under the same configuration within 24 hours reuses the earlier risk result instead of asking the
models again, provided the payee's payment methods haven't changed since. Identity and
authorization still run every time. The reused result names the decision it came from in
`risk.reused_from` and carries no token usage, since no model was called for it.
"""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from zeta_one.contracts import Configuration, Context, EvidenceRecord, IdentityEvidence, Proposal, RiskEvidence
from zeta_one.gateway.ledger import payment_method_state
from zeta_one.gateway.pipeline import Engine

WINDOW = timedelta(hours=24)

SCHEMA = """
CREATE TABLE IF NOT EXISTS risk_results (
    decision_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    configuration TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payment_method_state TEXT NOT NULL,
    risk TEXT NOT NULL
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


def _configuration_key(configuration: Configuration) -> str:
    return configuration.model_dump_json()


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


class RiskReuse:
    """An `Engine.assess_risk` that reuses recent results; `remember` stores one once it is decided."""

    def __init__(self, connection: sqlite3.Connection, window: timedelta = WINDOW):
        self._db = connection
        self._window = window
        self._db.executescript(SCHEMA)

    def __call__(
        self, engine: Engine, proposal: Proposal, context: Context, now: datetime, identity: IdentityEvidence
    ) -> RiskEvidence:
        earlier = self._find(identity.claimed_agent_id, proposal, context, now, engine.configuration)
        if earlier is None:
            return engine.run_tiers(proposal, context, now, identity)
        decision_id, risk = earlier
        results = [result.model_copy(update={"usage": None, "latency_ms": None}) for result in risk.tier_results]
        return risk.model_copy(update={"reused_from": decision_id, "tier_results": results})

    def remember(self, record: EvidenceRecord, proposal: Proposal | None, context: Context | None) -> None:
        """Keep a decision's risk result for reuse, unless risk didn't run or was itself reused."""
        if proposal is None or context is None or not record.risk.tiers_run or record.risk.reused_from:
            return
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO risk_results VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.decision_id,
                    fingerprint(record.identity.claimed_agent_id, proposal),
                    _configuration_key(record.configuration),
                    _iso(record.created_at),
                    json.dumps(payment_method_state(context)),
                    record.risk.model_dump_json(by_alias=True),
                ),
            )

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
