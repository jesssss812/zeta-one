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
from datetime import UTC, datetime
from typing import Any, Literal

from zeta_one.contracts import IdentityEvidence, SignedRequest
from zeta_one.gateway import admin
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.pipeline import Engine
from zeta_one.gateway.reuse import RiskReuse
from zeta_one.gateway.wiring import ContextCapture, Stages, build_engine


class EngineNotReady(RuntimeError):
    pass


class UnknownChallenge(KeyError):
    pass


class NotHeld(RuntimeError):
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

    def __post_init__(self) -> None:
        self._capture: ContextCapture | None = None
        self._engine: Engine | None = None
        self._missing = self.stages.missing()
        if not self._missing:
            self._capture = ContextCapture(self.stages.load_context)
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
        self, challenge_id: str, outcome: Literal["approve", "reject"], by: str, note: str | None = None
    ) -> dict[str, Any]:
        """A person approves or rejects a held payment. Approval executes it only if nothing changed."""
        with self.lock:
            return self._resolve(challenge_id, outcome, by, note)

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
            changes = admin.recheck(held, identity, self.stages, self.ledger, now)
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

