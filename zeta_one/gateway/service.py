"""What the gateway does with a request: decide it, record it, then execute, hold or block (simulated).

The HTTP layer in app.py only translates to and from JSON; this holds the order of operations.

Every use of the gateway's database goes through `Gateway.lock`, one request at a time. The
modules share one SQLite connection, whose transactions are not per thread, and a decision must
read the rolling spend and the reuse table and write its record without another decision in
between (security.md, S3 and S8). The demo's volume makes the lost concurrency, including while a
model call runs, a fair price.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from zeta_one.contracts import (
    Context,
    ContextSource,
    Finding,
    IdentityEvidence,
    Proposal,
    SignedRequest,
    Verification,
    VerifiedOutcome,
)
from zeta_one.gateway.recheck import recheck
from zeta_one.gateway.adjustments import Adjustments
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.pipeline import Engine
from zeta_one.gateway.reuse import RiskReuse
from zeta_one.gateway.wiring import ContextCapture, Stages, build_engine


# How far back the context's `gateway_payments` reach: what the duplicate check can see. A bill paid
# by the gateway stays open in Rho's stand-in records, so this covers any bill a demo could repeat.
GATEWAY_PAYMENT_WINDOW = timedelta(days=365)


def with_gateway_payments(load_context: ContextSource, ledger: Ledger,
                          adjustments: Adjustments | None = None) -> ContextSource:
    """A ContextSource that adds the gateway's own recent simulated payments to the payee, drops the
    bills it has already paid from `open_bills`, and adds the business's active risk adjustments."""

    def load(proposal: Proposal, business_id: str, now: datetime) -> Context:
        context = load_context(proposal, business_id, now)
        payments = ledger.payments_to(business_id, proposal.counterparty_id, now - GATEWAY_PAYMENT_WINDOW)
        paid = {payment.bill_id for payment in payments if payment.bill_id and payment.status == "executed"}
        open_bills = [bill for bill in context.open_bills if bill.id not in paid]
        active = adjustments.active(business_id, now) if adjustments else []
        return context.model_copy(update={"gateway_payments": payments, "open_bills": open_bills,
                                          "adjustments": active})

    return load


class EngineNotReady(RuntimeError):
    pass


class UnknownChallenge(KeyError):
    pass


class NotHeld(RuntimeError):
    pass


class UnknownDecision(KeyError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Gateway:
    stages: Stages
    ledger: Ledger
    clock: Callable[[], datetime] = _now
    reuse: RiskReuse | None = None
    version: str | None = None
    lock: threading.RLock = field(default_factory=threading.RLock)
    adjustments: Adjustments | None = None

    def __post_init__(self) -> None:
        if self.adjustments is None:
            self.adjustments = Adjustments(self.ledger.connection)
        self._capture: ContextCapture | None = None
        self._engine: Engine | None = None
        self._missing = self.stages.missing()
        if not self._missing:
            self._capture = ContextCapture(with_gateway_payments(self.stages.load_context, self.ledger, self.adjustments))
            captured = replace(self.stages, load_context=self._capture)
            self._engine = build_engine(
                captured, self.ledger.spend_source(), assess_risk=self.reuse, clock=self.clock, version=self.version
            )

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise EngineNotReady(f"stages not built yet: {', '.join(self._missing)}")
        return self._engine

    def propose(self, request: SignedRequest) -> dict[str, Any]:
        """Decide and record one agent request; the agent learns only the decision and its ids (S4).

        Raises InvalidProposal for a malformed body, before anything is recorded.
        """
        engine = self.engine
        with self.lock:
            with self._capture.recording() as seen:
                record, proposal = engine.evaluate(request)
            context = seen[-1] if seen else None
            challenge_id = self.ledger.record(record, proposal, context=context)
            if self.reuse:
                self.reuse.remember(record, proposal, context)
        return {"decision": record.decision, "decision_id": record.decision_id, "challenge_id": challenge_id}

    def resolve(
        self, challenge_id: str, outcome: Literal["approve", "reject"], by: str, note: str | None = None,
        finding: Finding | None = None, verification: Verification = "none",
    ) -> dict[str, Any]:
        """A person approves or rejects a held payment. Approval executes it only if nothing changed.
        With `finding`, what they established is recorded as an outcome, with how they know."""
        with self.lock:
            resolved = self._resolve(challenge_id, outcome, by, note)
            if finding is not None:
                self._record_outcome(resolved["decision_id"], VerifiedOutcome(
                    finding=finding, verification=verification, by=by, at=self.clock(), note=note, source="resolve"))
            return resolved

    def report_outcome(
        self, decision_id: str, finding: Finding, verification: Verification, by: str, note: str | None = None
    ) -> VerifiedOutcome:
        """A person records what they later found about any decision, an allowed payment disputed as
        fraud included. Raises UnknownDecision if there is no such decision."""
        outcome = VerifiedOutcome(finding=finding, verification=verification, by=by, at=self.clock(), note=note,
                                  source="report")
        with self.lock:
            if not self._record_outcome(decision_id, outcome):
                raise UnknownDecision(decision_id)
        return outcome

    def _record_outcome(self, decision_id: str, outcome: VerifiedOutcome) -> bool:
        """Append the outcome and, if it is verified and implies one, the risk adjustment (decision 0013)."""
        if not self.ledger.add_outcome(decision_id, outcome):
            return False
        self.adjustments.derive(self.ledger.decision(decision_id), outcome)
        return True

    def _resolve(
        self, challenge_id: str, outcome: Literal["approve", "reject"], by: str, note: str | None
    ) -> dict[str, Any]:
        held = self.ledger.held(challenge_id)
        if held is None:
            raise UnknownChallenge(challenge_id)
        if held.status != "held":
            raise NotHeld(f"challenge {challenge_id} is already {held.status}")
        now = self.clock()
        reasons: list[str] = []
        changes: list[str] = []
        if outcome == "reject":
            status, result = "blocked", "rejected"
        else:
            identity = IdentityEvidence.model_validate(self.ledger.decision(held.decision_id)["identity"])
            changes = recheck(held, identity, self.stages, self.ledger, now)
            if changes:
                status, result, reasons = "blocked", "blocked", ["resolve:state_changed"]
            else:
                status, result = "executed", "approved"
        review = {
            "by": by,
            "at": now.isoformat(),
            "outcome": result,
            "note": note,
            "provenance": "admin_token",
            "challenge_id": challenge_id,
            "reasons": reasons,
            "changes": changes,
        }
        if not self.ledger.resolve(held, status, review, now):
            raise NotHeld(f"challenge {challenge_id} was resolved meanwhile")
        return {"decision_id": held.decision_id, "challenge_id": challenge_id, "status": status, "reasons": reasons}

