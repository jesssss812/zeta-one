"""What the gateway does with a request: decide it, record it, then execute, hold or block (simulated).

The HTTP layer in app.py only translates to and from JSON; this holds the order of operations.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from zeta_one.contracts import SignedRequest
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.pipeline import Engine
from zeta_one.gateway.wiring import ContextCapture, Stages, build_engine


class EngineNotReady(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Gateway:
    stages: Stages
    ledger: Ledger
    clock: Callable[[], datetime] = _now
    assess_risk: Callable | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        self._capture: ContextCapture | None = None
        self._engine: Engine | None = None
        self._missing = self.stages.missing()
        if not self._missing:
            self._capture = ContextCapture(self.stages.load_context)
            captured = replace(self.stages, load_context=self._capture)
            self._engine = build_engine(
                captured, self.ledger.spend_source(), assess_risk=self.assess_risk, clock=self.clock, version=self.version
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
        with self._capture.recording() as seen:
            record, proposal = engine.evaluate(request)
        challenge_id = self.ledger.record(record, proposal, context=seen[-1] if seen else None)
        return {"decision": record.decision, "decision_id": record.decision_id, "challenge_id": challenge_id}
