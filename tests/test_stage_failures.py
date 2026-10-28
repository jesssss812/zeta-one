"""A stage that raises is recorded and challenged, never a crash and never an allow (decision 0010)."""

from zeta_one.gateway.scenarios import load_fixture
from zeta_one.testing.replay import replay_engine, request_for


def _engine(name="routine_bill_payment"):
    scenario = load_fixture(name)
    return replay_engine(scenario), request_for(scenario)


def test_tier0_raising_is_a_recorded_challenge():
    engine, request = _engine()

    def broken(*args):
        raise RuntimeError("feature failed")

    engine.tier0 = broken
    record, _ = engine.evaluate(request)
    assert record.decision == "challenge" and record.reasons == ["risk:tier0_unavailable"]
    assert record.risk.tier_results[0].error == "RuntimeError: feature failed"


def test_the_context_failing_is_a_recorded_challenge():
    engine, request = _engine()

    def broken(*args):
        raise OSError("store unavailable")

    engine.load_context = broken
    record, _ = engine.evaluate(request)
    assert record.decision == "challenge" and record.reasons == ["risk:tier0_unavailable"]
    assert record.risk.tier_results[0].error.startswith("context: OSError")


def test_an_escalation_rule_that_fails_is_a_recorded_challenge(monkeypatch):
    from zeta_one.risk import escalation

    def broken(configuration, tier0):
        raise RuntimeError("rule failed")

    monkeypatch.setattr(escalation, "should_escalate", broken)
    engine, request = _engine("vendor_payment_method_changed")
    record, _ = engine.evaluate(request)
    assert record.decision == "challenge" and "risk:model_unavailable" in record.reasons
    assert record.risk.tier_results[-1].error.startswith("escalation: RuntimeError")
