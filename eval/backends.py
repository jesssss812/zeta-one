"""What turns a case and a configuration into a decision.

A backend owns everything about the engine: fresh data for each case, signing with the case's agent,
the evaluation's own setup ops (see eval/cases.py) and any follow-up steps. `ReplayBackend` runs the
five demo cases through the kernel's replay stand-ins; it exists to test the runner and report before
the real stages land. The real backend is added when W1, W2 and W5 are on main.
"""

import dataclasses
from dataclasses import dataclass, field
from typing import Protocol

from eval import cases as hand_cases
from zeta_one.contracts import Case, Configuration, Decision, EvidenceRecord
from zeta_one.gateway import scenarios
from zeta_one.testing.replay import replay_engine, request_for


class Unsupported(Exception):
    """The backend cannot run this case; the report counts it as not run."""


@dataclass
class Outcome:
    decision: Decision
    record: EvidenceRecord | None = None
    # Decisions of every send, when the case repeats its request.
    decisions: list[Decision] = field(default_factory=list)
    model_calls: int | None = None


class Backend(Protocol):
    name: str

    def run(self, case: Case, configuration: Configuration) -> Outcome: ...


class ReplayBackend:
    name = "replay"

    def __init__(self) -> None:
        self._fixture_of = {case_id: fixture for fixture, (case_id, *_rest) in hand_cases._DEMO.items()}

    def run(self, case: Case, configuration: Configuration) -> Outcome:
        fixture = self._fixture_of.get(case.id)
        if fixture is None:
            raise Unsupported("the replay backend only knows the five demo cases")
        scenario = scenarios.load_fixture(fixture)
        engine = dataclasses.replace(replay_engine(scenario), configuration=configuration)
        record, _ = engine.evaluate(request_for(scenario))
        return Outcome(decision=record.decision, record=record, decisions=[record.decision])


def get_backend(name: str) -> Backend:
    if name == "replay":
        return ReplayBackend()
    raise ValueError(f"backend {name!r} is not available yet; choose from: replay")
