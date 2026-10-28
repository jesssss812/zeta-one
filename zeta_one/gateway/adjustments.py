"""Risk adjustments: how verified outcomes change one business's risk, recorded append-only (decision 0013).

A verified fraud finding blocks the payment method the money went to. A verified legitimate finding
on a payment floored by a recent bank change confirms that one change for CONFIRMATION_DAYS. Rows
are never edited; a revocation is a later row. Only `derive` (from a person's verified outcome) and
`revoke` (by a person) write here.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any

from zeta_one.contracts import RiskAdjustment, VerifiedOutcome

CONFIRMATION_DAYS = 90
FRAUD_FINDINGS = ("payee_fraud", "manipulated_agent")

SCHEMA = """
CREATE TABLE IF NOT EXISTS risk_adjustments (
    adjustment_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    at TEXT NOT NULL,
    adjustment TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS risk_adjustments_business ON risk_adjustments (business_id, at);
"""


def _new_id() -> str:
    return f"adj_{uuid.uuid4().hex[:16]}"


class Adjustments:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection
        self._db.executescript(SCHEMA)

    def append(self, adjustment: RiskAdjustment) -> RiskAdjustment:
        with self._db:
            self._db.execute("INSERT INTO risk_adjustments VALUES (?, ?, ?, ?)",
                             (adjustment.adjustment_id, adjustment.business_id, adjustment.at.isoformat(),
                              adjustment.model_dump_json()))
        return adjustment

    def all(self, business_id: str | None = None) -> list[RiskAdjustment]:
        query = "SELECT adjustment FROM risk_adjustments" + (" WHERE business_id = ?" if business_id else "")
        rows = self._db.execute(query + " ORDER BY at, rowid", (business_id,) if business_id else ()).fetchall()
        return [RiskAdjustment.model_validate_json(row[0]) for row in rows]

    def active(self, business_id: str, now: datetime) -> list[RiskAdjustment]:
        """Unrevoked, unexpired blocks and confirmations for the business."""
        rows = self.all(business_id)
        revoked = {row.subject for row in rows if row.kind == "revoke"}
        return [row for row in rows if row.kind != "revoke" and row.adjustment_id not in revoked
                and (row.expires_at is None or row.expires_at > now)]

    def derive(self, record: dict[str, Any], outcome: VerifiedOutcome) -> RiskAdjustment | None:
        """The adjustment a person's verified outcome on a decision implies, appended; None if none.

        A claim (unverified) implies nothing, nor does a finding on a decision with no proposal or
        context to point at."""
        if not outcome.verified or not record.get("proposal") or not record.get("context"):
            return None
        business = record["identity"].get("business_id")
        proposal, context = record["proposal"], record["context"]
        common = {"adjustment_id": _new_id(), "business_id": business, "decision_id": record["decision_id"],
                  "finding": outcome.finding, "verification": outcome.verification, "by": outcome.by,
                  "at": outcome.at}
        if outcome.finding in FRAUD_FINDINGS:
            return self.append(RiskAdjustment(kind="blocked_payment_method", subject=proposal["payment_method_id"],
                                              reason="verified fraud on a payment to this method", **common))
        floor = (record.get("risk") or {}).get("floor") or {}
        if outcome.finding == "legitimate" and "payment_method_changed_days_ago" in floor.get("flags", []):
            changes = [change for change in context.get("payment_method_history", [])
                       if change["method_id"] == proposal["payment_method_id"]]
            if not changes:
                return None
            latest = max(changes, key=lambda change: change["changed_at"])
            return self.append(RiskAdjustment(kind="confirmed_method_change", subject=latest["id"],
                                              expires_at=outcome.at + timedelta(days=CONFIRMATION_DAYS),
                                              reason="the bank change on this payment was verified legitimate",
                                              **common))
        return None

    def revoke(self, adjustment_id: str, by: str, now: datetime, reason: str | None = None) -> RiskAdjustment | None:
        target = next((row for row in self.all() if row.adjustment_id == adjustment_id and row.kind != "revoke"), None)
        if target is None:
            return None
        return self.append(RiskAdjustment(adjustment_id=_new_id(), business_id=target.business_id, kind="revoke",
                                          subject=adjustment_id, by=by, at=now, reason=reason))
