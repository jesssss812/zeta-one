import pytest

from tests.gateway.fakes import HELD, NOW, FakeWorld
from zeta_one.gateway.wiring import Stages, StagesMissing, build_engine, real_stages
from zeta_one.risk.claude import PRICES, StrongTier
from zeta_one.testing.replay import request_for


def _no_spend(agent_id, since, currency):
    return 0


def test_real_stages_include_the_strong_tier_and_its_prices():
    stages = real_stages()
    assert isinstance(stages.tiers["strong"], StrongTier)
    assert stages.prices == PRICES


def test_the_live_engine_needs_every_stage():
    with pytest.raises(StagesMissing, match="verify_identity"):
        build_engine(Stages(), _no_spend)
    world = FakeWorld()
    stages = world.stages()
    stages.tiers = {}
    assert stages.missing() == ["tiers.strong"]


def test_a_scenario_replays_the_stages_that_are_missing():
    record, _ = build_engine(Stages(), _no_spend, replay=HELD).evaluate(request_for(HELD))
    assert record.decision == HELD.decision_record.decision
    assert record.decision_id == HELD.decision_record.decision_id


def test_a_real_stage_replaces_its_stand_in():
    world = FakeWorld()
    stages = Stages(tier0=world.tier0, tiers={"strong": world._Strong(world)})
    engine = build_engine(stages, _no_spend, replay=HELD, clock=lambda: NOW)
    record, _ = engine.evaluate(request_for(HELD))
    assert world.strong_calls == 1
    assert record.decision == "challenge"
