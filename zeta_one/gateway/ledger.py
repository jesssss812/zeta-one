"""Decisions and simulated payments, in the gateway's SQLite file.

Every decision's evidence record is written here before its payment is executed, held or blocked.
No money moves: a payment row is the simulated execution (decision 0002). A held payment keeps the
authorization version and payment-method state it was decided on, so resolving it can recheck them
(security.md, S9). The executed and held rows are the rolling limit's input (`spend_source`).
"""

import json
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zeta_one.contracts import Context, EvidenceRecord, ExecutionStatus, PaymentRecord, Proposal, SpendSource

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
        """The evidence record as served, with the payment's current status and any review."""
        row = self._db.execute(
            """SELECT d.record, d.review, p.status FROM decisions d
               LEFT JOIN payments p ON p.decision_id = d.decision_id WHERE d.decision_id = ?""",
            (decision_id,),
        ).fetchone()
        return _served(row) if row else None

    def decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.execute(
            """SELECT d.record, d.review, p.status FROM decisions d
               LEFT JOIN payments p ON p.decision_id = d.decision_id
               ORDER BY d.created_at DESC, d.rowid DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [_served(row) for row in rows]

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
        """Executed and held payments by an agent since a time, in one currency, in minor units."""
        row = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM payments
               WHERE agent_id = ? AND currency = ? AND status IN ('executed', 'held')
               AND created_at >= ? AND payment_id IS NOT ?""",
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


def _served(row: sqlite3.Row) -> dict[str, Any]:
    record = json.loads(row["record"])
    if row["status"]:
        record["execution"]["status"] = row["status"]
    if row["review"]:
        record["review"] = json.loads(row["review"])
    return record
