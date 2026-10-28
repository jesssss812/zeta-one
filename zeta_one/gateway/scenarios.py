"""The five demo scenarios. Until the seed and the real stages land, each runs by replaying its
fixture through the real merge and policy, so its result stays marked illustrative."""

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path

from zeta_one.contracts import EvidenceRecord, ScenarioResult
from zeta_one.gateway.pipeline import new_decision_id
from zeta_one.testing.replay import replay_engine, request_for

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
ORDER = [
    "vendor_payment_method_changed",
    "routine_bill_payment",
    "over_per_payment_limit",
    "unknown_agent",
    "invoice_redirect_instructions",
]


def load_fixture(name: str) -> ScenarioResult:
    return ScenarioResult.model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


def list_scenarios() -> list[dict]:
    return [load_fixture(name).scenario.model_dump() for name in ORDER]


def run(name: str) -> ScenarioResult:
    if name not in ORDER:
        raise KeyError(name)
    scenario = load_fixture(name)
    # Each run is a new decision: its own id and the time it ran, not the fixture's.
    engine = dataclasses.replace(replay_engine(scenario), new_id=new_decision_id, clock=lambda: datetime.now(UTC))
    record, _ = engine.evaluate(request_for(scenario))
    return scenario.model_copy(update={"decision_record": record, "illustrative": True})


def dump(record: EvidenceRecord | ScenarioResult) -> dict:
    """The JSON shape served to the site, with aliases applied (`risk.lowered.from`)."""
    return record.model_dump(mode="json", by_alias=True)
