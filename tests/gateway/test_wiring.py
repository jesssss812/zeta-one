import sqlite3

import pytest

from tests.gateway.fakes import HELD, NOW, FakeWorld
from zeta_one.gateway.wiring import Stages, StagesMissing, build_engine, real_stages
from zeta_one.risk.claude import PRICES, StrongTier
from zeta_one.testing.replay import request_for


def _no_spend(agent_id, since, currency):
    return 0


def test_real_stages_are_complete_and_include_both_model_tiers_and_their_prices():
    from zeta_one.risk import jev
    from zeta_one.risk.jev import JevTier
    from zeta_one.gateway.wiring import CONFIGURATIONS

    for configuration in CONFIGURATIONS.values():
        stages = real_stages(sqlite3.connect(":memory:", check_same_thread=False), configuration=configuration)
        assert stages.missing() == []
    assert isinstance(stages.tiers["strong"], StrongTier) and isinstance(stages.tiers["cheap"], JevTier)
    assert stages.prices == {**PRICES, **jev.PRICES}
    assert stages.seed_version


@pytest.mark.parametrize("value, escalation", [(None, "engineered"), ("engineered", "engineered"), ("jev", "jev")])
def test_the_live_configuration_comes_from_the_environment(monkeypatch, value, escalation):
    from zeta_one.gateway.wiring import CONFIGURATION_NAME, configuration_from_env

    if value is None:
        monkeypatch.delenv(CONFIGURATION_NAME, raising=False)
    else:
        monkeypatch.setenv(CONFIGURATION_NAME, value)
    assert configuration_from_env().escalation == escalation


def test_an_unknown_configuration_name_is_refused(monkeypatch):
    from zeta_one.gateway.wiring import CONFIGURATION_NAME, configuration_from_env

    monkeypatch.setenv(CONFIGURATION_NAME, "cheapest")
    with pytest.raises(ValueError):
        configuration_from_env()


def test_the_demo_agent_is_registered_once_from_its_local_key(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    from zeta_one.gateway.wiring import register_demo_agents

    key = Ed25519PrivateKey.generate()
    (tmp_path / "ap_assistant.pem").write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    stages = real_stages(sqlite3.connect(":memory:", check_same_thread=False))
    assert register_demo_agents(stages, tmp_path, NOW) == ["agent_ap_assistant_01"]
    assert register_demo_agents(stages, tmp_path, NOW) == []
    agent = stages.registry.get("agent_ap_assistant_01")
    assert agent.status == "active" and agent.public_key == key.public_key().public_bytes_raw()
    assert stages.authorizations.load(agent.business_id, agent.agent_id).authorization_id == "auth_0001"


def test_no_key_means_no_demo_agent(tmp_path):
    from zeta_one.gateway.wiring import register_demo_agents

    stages = real_stages(sqlite3.connect(":memory:", check_same_thread=False))
    assert register_demo_agents(stages, tmp_path, NOW) == []


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
