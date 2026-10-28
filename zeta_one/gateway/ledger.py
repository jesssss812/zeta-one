"""Decisions and simulated payments, in the gateway's SQLite file.

Every decision's evidence record is written here before its payment is executed, held or blocked.
No money moves: a payment row is the simulated execution (decision 0002). A held payment keeps the
authorization version and payment-method state it was decided on, so resolving it can recheck them
(security.md, S9). The executed and held rows are the rolling limit's input (`spend_source`).
Verified outcomes a person records later are appended, never edited (decision 0012).
"""

import json
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zeta_one.contracts import (
    Context,
    EvidenceRecord,
    ExecutionStatus,
    PaymentRecord,
    Proposal,
    SpendSource,
    VerifiedOutcome,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    record TEXT NOT NULL,
    review TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE REFERENCES decisions(decision_id),
    challenge_id TEXT UNIQUE,
    agent_id TEXT,
    business_id TEXT,
    proposal TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    executed_at TEXT,
    authorization_id TEXT,
    authorization_version INTEGER,
    payment_method_state TEXT
);
CREATE INDEX IF NOT EXISTS payments_spend ON payments (agent_id, currency, status);
CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL REFERENCES decisions(decision_id),
    at TEXT NOT NULL,
    outcome TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS outcomes_decision ON outcomes (decision_id);
"""


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def payment_method_state(context: Context) -> dict[str, Any]:
    """What a held payment or a reused risk result depends on: the payee's methods and their changes."""
    return {
        "counterparty_id": context.counterparty.id,
        "methods": [method.model_dump(mode="json") for method in context.counterparty.payment_methods],
        "changes": [change.id for change in context.payment_method_history],
    }


@dataclass(frozen=True)
class HeldPayment:
    payment_id: str
    decision_id: str
    challenge_id: str
    agent_id: str
    business_id: str
    proposal: Proposal
    status: ExecutionStatus
    authorization_id: str | None
    authorization_version: int | None
    payment_method_state: dict[str, Any] | None


class Ledger:
    def __init__(self, connection: sqlite3.Connection, new_id: Callable[[str], str] = _new_id):
        self._db = connection
        self.connection = connection
        self._new_id = new_id
        self._db.executescript(SCHEMA)

    def record(
        self,
        record: EvidenceRecord,
        proposal: Proposal | None,
        *,
        context: Context | None = None,
    ) -> str | None:
        """Write the evidence record and, when there is a proposal, its simulated payment.

        Returns the challenge id for a held payment, else None.
        """
        challenge_id = self._new_id("chl") if record.execution.status == "held" else None
        with self._db:
            self._db.execute(
                "INSERT INTO decisions (decision_id, created_at, record) VALUES (?, ?, ?)",
                (record.decision_id, _iso(record.created_at), record.model_dump_json(by_alias=True)),
            )
            if proposal is not None:
                status = record.execution.status
                self._db.execute(
                    """INSERT INTO payments (payment_id, decision_id, challenge_id, agent_id, business_id,
                       proposal, amount, currency, status, created_at, executed_at, authorization_id,
                       authorization_version, payment_method_state)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self._new_id("pay"),
                        record.decision_id,
                        challenge_id,
                        record.identity.claimed_agent_id,
                        record.identity.business_id,
                        proposal.model_dump_json(),
                        proposal.amount.amount,
                        proposal.amount.currency,
                        status,
                        _iso(record.created_at),
                        _iso(record.created_at) if status == "executed" else None,
                        record.authorization.authorization_id,
                        record.authorization.version,
                        json.dumps(payment_method_state(context)) if context else None,
                    ),
                )
        return challenge_id

    def save_record(self, record: EvidenceRecord) -> None:
        """Keep a record for reading only, with no payment: a demo scenario run in its own sandbox."""
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO decisions (decision_id, created_at, record) VALUES (?, ?, ?)",
                (record.decision_id, _iso(record.created_at), record.model_dump_json(by_alias=True)),
            )

    def decision(self, decision_id: str) -> dict[str, Any] | None:
        """The evidence record as served, with the payment's current status, any review and outcomes."""
        row = self._db.execute(
            """SELECT d.decision_id, d.record, d.review, p.status FROM decisions d
               LEFT JOIN payments p ON p.decision_id = d.decision_id WHERE d.decision_id = ?""",
            (decision_id,),
        ).fetchone()
        return self._served(row) if row else None

    def decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.execute(
            """SELECT d.decision_id, d.record, d.review, p.status FROM decisions d
               LEFT JOIN payments p ON p.decision_id = d.decision_id
               ORDER BY d.created_at DESC, d.rowid DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._served(row) for row in rows]

    def add_outcome(self, decision_id: str, outcome: VerifiedOutcome) -> bool:
        """Append a person's finding to a decision. False if there is no such decision."""
        if self._db.execute("SELECT 1 FROM decisions WHERE decision_id = ?", (decision_id,)).fetchone() is None:
            return False
        with self._db:
            self._db.execute("INSERT INTO outcomes (decision_id, at, outcome) VALUES (?, ?, ?)",
                             (decision_id, _iso(outcome.at), outcome.model_dump_json()))
        return True

    def outcomes(self, decision_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT outcome FROM outcomes WHERE decision_id = ? ORDER BY outcome_id",
                                (decision_id,)).fetchall()
        return [json.loads(row["outcome"]) for row in rows]

    def stats(self) -> dict[str, Any]:
        """Friction and feedback from real decisions: how often challenges end up approved, and what
        verified outcomes say about allows and challenges. Sandbox scenario records are left out."""
        rows = self._db.execute(
            """SELECT d.decision_id, d.record, d.review, p.status FROM decisions d
               LEFT JOIN payments p ON p.decision_id = d.decision_id""").fetchall()
        records = [record for record in (self._served(row) for row in rows) if not record.get("sandbox")]
        decided = {name: sum(r["decision"] == name for r in records) for name in ("allow", "challenge", "block")}
        challenged = [r for r in records if r["decision"] == "challenge"]
        reviewed = [r for r in challenged if r.get("review")]
        approved = sum(r["review"]["outcome"] == "approved" for r in reviewed)
        latest = {r["decision_id"]: _latest_verified(r.get("outcomes", [])) for r in records}
        fraud = ("payee_fraud", "manipulated_agent", "unauthorized")
        return {
            "decisions": decided,
            "challenges": {"total": len(challenged), "resolved": len(reviewed), "approved": approved,
                           "rejected": sum(r["review"]["outcome"] == "rejected" for r in reviewed),
                           "blocked_on_recheck": sum(r["review"]["outcome"] == "blocked" for r in reviewed),
                           "approval_rate": approved / len(reviewed) if reviewed else None},
            "verified_outcomes": {finding: sum(o is not None and o["finding"] == finding for o in latest.values())
                                  for finding in ("legitimate", *fraud)},
            "unverified_reports": sum(1 for r in records for o in r.get("outcomes", []) if not o["verified"]),
            "missed_fraud": sorted(r["decision_id"] for r in records if r["decision"] == "allow"
                                   and (latest[r["decision_id"]] or {}).get("finding") in fraud),
            "unneeded_challenges": sorted(r["decision_id"] for r in challenged
                                          if (latest[r["decision_id"]] or {}).get("finding") == "legitimate"),
        }

    def _served(self, row: sqlite3.Row) -> dict[str, Any]:
        record = _served(row)
        outcomes = self.outcomes(row["decision_id"])
        if outcomes:
            record["outcomes"] = outcomes
        return record

    def held(self, challenge_id: str) -> HeldPayment | None:
        row = self._db.execute("SELECT * FROM payments WHERE challenge_id = ?", (challenge_id,)).fetchone()
        if row is None:
            return None
        return HeldPayment(
            payment_id=row["payment_id"],
            decision_id=row["decision_id"],
            challenge_id=row["challenge_id"],
            agent_id=row["agent_id"],
            business_id=row["business_id"],
            proposal=Proposal.model_validate_json(row["proposal"]),
            status=row["status"],
            authorization_id=row["authorization_id"],
            authorization_version=row["authorization_version"],
            payment_method_state=json.loads(row["payment_method_state"]) if row["payment_method_state"] else None,
        )

    def resolve(self, payment: HeldPayment, status: ExecutionStatus, review: dict[str, Any], now: datetime) -> bool:
        """Move a held payment to executed or blocked and attach the review. False if it was no longer held."""
        with self._db:
            changed = self._db.execute(
                "UPDATE payments SET status = ?, executed_at = ? WHERE payment_id = ? AND status = 'held'",
                (status, _iso(now) if status == "executed" else None, payment.payment_id),
            ).rowcount
            if changed:
                self._db.execute(
                    "UPDATE decisions SET review = ? WHERE decision_id = ?",
                    (json.dumps(review), payment.decision_id),
                )
        return bool(changed)

    def spend(self, agent_id: str, since: datetime, currency: str, exclude: str | None = None) -> int:
        """Executed spend since a time plus all outstanding held reservations, in minor units.

        A hold reserves its amount until resolved; execution starts its rolling spend window.
        """
        row = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM payments
               WHERE agent_id = ? AND currency = ?
               AND (status = 'held' OR (status = 'executed' AND executed_at >= ?))
               AND payment_id IS NOT ?""",
            (agent_id, currency, _iso(since), exclude),
        ).fetchone()
        return int(row[0])

    def payments_to(self, business_id: str, counterparty_id: str, since: datetime) -> list[PaymentRecord]:
        """The business's executed and held simulated payments to one payee since a time, newest first."""
        rows = self._db.execute(
            """SELECT payment_id, proposal, created_at, status FROM payments
               WHERE business_id = ? AND status IN ('executed', 'held') AND created_at >= ?
               ORDER BY created_at DESC""",
            (business_id, _iso(since)),
        ).fetchall()
        records = []
        for row in rows:
            proposal = Proposal.model_validate_json(row["proposal"])
            if proposal.counterparty_id == counterparty_id:
                records.append(PaymentRecord(id=row["payment_id"], posted_at=row["created_at"],
                                             amount=proposal.amount, bill_id=proposal.bill_id, status=row["status"]))
        return records

    def spend_source(self, exclude: str | None = None) -> SpendSource:
        """A SpendSource; `exclude` leaves out one payment, so a held payment isn't counted against itself."""

        def spend(agent_id: str, since: datetime, currency: str) -> int:
            return self.spend(agent_id, since, currency, exclude)

        return spend


def _latest_verified(outcomes: list[dict[str, Any]]) -> dict[str, Any] | None:
    verified = [outcome for outcome in outcomes if outcome.get("verified")]
    return verified[-1] if verified else None


def _served(row: sqlite3.Row) -> dict[str, Any]:
    record = json.loads(row["record"])
    if row["status"]:
        record["execution"]["status"] = row["status"]
    if row["review"]:
        record["review"] = json.loads(row["review"])
    return record
