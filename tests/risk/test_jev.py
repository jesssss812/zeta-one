"""The Jev cheap tier against a stubbed HTTP call, its escalation rule, and one live call behind --live-models."""

import json

import pytest

from tests.risk.test_claude import risk_input, scenario, tier0_output
from zeta_one.contracts import Configuration
from zeta_one.decide import policy
from zeta_one.risk import escalation, jev
from zeta_one.risk.assess import assess
from zeta_one.risk.jev import JevTier

JEV = Configuration(tiers=["tier0", "cheap", "strong"], escalation="jev")


def payload(level="low", p=0.95, targets=False, matches=True, impersonation=False, findings_p=0.97, shape="nested"):
    answers = {
        "risk_level": {"value": level, "probability": p},
        "document_targets_agent": {"value": targets, "probability": findings_p},
        "proposal_matches_documents": {"value": matches, "probability": findings_p},
        "vendor_impersonation_signs": {"value": impersonation, "probability": findings_p},
    }
    if shape == "nested":
        return {"answers": answers, "usage": {"input_tokens": 812}}
    if shape == "typed":
        return {"choices": {"risk_level": answers["risk_level"]},
                "nouls": {k: v for k, v in answers.items() if k != "risk_level"}, "usage": {"prompt_tokens": 812}}
    if shape == "distribution":
        dist = {"low": 0.05, "elevated": 0.15, "high": 0.8}
        return {"answers": {**answers, "risk_level": {"probabilities": dist}}}
    raise AssertionError(shape)


class Post:
    def __init__(self, reply, status=200):
        self.reply, self.status, self.calls = reply, status, []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.status, self.reply


def run(reply, status=200, name="invoice_redirect_instructions"):
    post = Post(reply, status)
    return JevTier(post=post, key="test-key").assess(risk_input(name)), post.calls


@pytest.mark.parametrize("shape", ["nested", "typed"])
def test_an_answer_becomes_a_cheap_tier_result_with_its_probabilities(shape):
    output, calls = run(payload(shape=shape))
    result = output.result
    assert (result.tier, result.model, result.level, result.confidence, result.error) == ("cheap", "jev-latest", "low", 0.95, None)
    assert result.probabilities["risk_level"] == 0.95 and result.answers["document_targets_agent"] is False
    assert result.usage.input_tokens == 812 and output.signals == []


def test_a_probability_distribution_is_read_as_its_most_likely_level():
    output, _ = run(payload(shape="distribution"))
    assert (output.result.level, output.result.confidence) == ("high", 0.8)


def test_the_request_sends_the_rendered_state_and_the_four_questions():
    _, calls = run(payload())
    url, headers, body = calls[0]
    assert url == jev.ENDPOINT and headers == {"Authorization": "Bearer test-key"}
    assert body["model"] == "jev-latest" and set(body["questions"]) == set(jev.QUESTIONS)
    assert "<gateway_facts>" in body["state"] and "<untrusted_data boundary=" in body["state"]
    assert scenario("invoice_redirect_instructions").context.bill.document_excerpt in body["state"]


def test_a_document_targeting_the_agent_raises_a_low_answer_to_high():
    output, _ = run(payload(level="low", targets=True))
    assert output.result.level == "high" and output.result.answered_level == "low"
    assert [s.name for s in output.signals] == ["document_targets_agent"]


def test_a_mismatch_and_impersonation_are_elevated_findings():
    output, _ = run(payload(level="low", matches=False, impersonation=True))
    assert output.result.level == "elevated"
    assert {s.name for s in output.signals} == {"proposal_mismatches_documents", "vendor_impersonation_signs"}


@pytest.mark.parametrize("reply, status, error", [
    (payload(), 401, "http_401"),
    (TimeoutError("slow"), 200, "TimeoutError"),
    ({"answers": {}}, 200, "invalid_output"),
    ({"answers": {**payload()["answers"], "risk_level": {"value": "catastrophic", "probability": 0.9}}}, 200, "invalid_output"),
    ({"answers": {**payload()["answers"], "risk_level": {"value": "low", "probability": 1.7}}}, 200, "invalid_output"),
    ({"answers": {**payload()["answers"], "document_targets_agent": {"value": "maybe", "probability": 0.9}}}, 200, "invalid_output"),
    (None, 200, "invalid_output"),
])
def test_each_failure_is_an_error_and_no_level(reply, status, error):
    output, _ = run(reply, status)
    assert output.result.error.startswith(error) and output.result.level is None


def test_no_key_is_an_error_without_a_call(monkeypatch, tmp_path):
    monkeypatch.delenv(jev.KEY_NAME, raising=False)
    monkeypatch.setattr(jev, "ROOT", tmp_path)

    def never(*args):
        raise AssertionError("a test without a key made a real Jev call")

    monkeypatch.setattr(jev, "_http_post", never)
    output = JevTier().assess(risk_input())
    assert output.result.error == f"{jev.KEY_NAME} is not set"


def test_the_key_is_read_from_the_environment_or_env_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("export TYPESAFE_API_KEY='from-file'\n")
    monkeypatch.delenv(jev.KEY_NAME, raising=False)
    assert jev.api_key(env) == "from-file"
    monkeypatch.setenv(jev.KEY_NAME, "from-env")
    assert jev.api_key(env) == "from-env"


def test_the_key_never_appears_in_an_error():
    output, _ = run(RuntimeError("Bearer test-key rejected"))
    assert "test-key" not in output.result.error


# --- The Jev escalation rule --------------------------------------------------------------------


def cheap(level="low", p=0.95, **findings):
    output, _ = run(payload(level=level, p=p, **findings))
    return output


@pytest.mark.parametrize("answer, escalates", [
    (dict(level="low", p=0.95), False),                       # confident and close to tier 0
    (dict(level="low", p=0.6), True),                         # not confident enough
    (dict(level="elevated", p=0.95), True),                   # elevated always goes to a person or the model
    (dict(level="high", p=0.95, targets=True), False),        # sure finding, sure level
    (dict(level="high", p=0.95, targets=True, findings_p=0.7), True),  # a finding it isn't sure of
])
def test_the_strong_tier_runs_after_jev_on_the_rule(answer, escalates):
    tier0 = tier0_output("vendor_payment_method_changed")  # elevated
    assert escalation.should_escalate_after_cheap(JEV, tier0, cheap(**answer)) is escalates


def test_jev_far_from_tier_0_escalates():
    tier0 = tier0_output("invoice_redirect_instructions")  # high
    assert escalation.should_escalate_after_cheap(JEV, tier0, cheap(level="low", p=0.99)) is True


def test_a_failed_jev_escalates_nothing_and_is_challenged():
    tier0 = tier0_output("vendor_payment_method_changed")
    failed, _ = run(payload(), status=500)
    assert escalation.should_escalate_after_cheap(JEV, tier0, failed) is False


class CountingStrong:
    name = "strong"

    def __init__(self):
        self.calls = 0

    def assess(self, risk_input):
        from zeta_one.contracts import TierOutput, TierResult
        self.calls += 1
        return TierOutput(result=TierResult(tier="strong", model="stand-in", level="high"))


def _assess(name, reply):
    fixture = scenario(name)
    t0 = tier0_output(name)
    strong = CountingStrong()
    risk = assess(fixture.proposal, fixture.context, fixture.decision_record.created_at,
                  lambda *_: t0, {"cheap": JevTier(post=Post(reply), key="k"), "strong": strong}, JEV)
    return risk, strong.calls


def test_a_confident_jev_saves_the_strong_call_and_its_lowering_is_recorded():
    """A soft-signal-only case: Jev may clear it, and the record says Jev did."""
    from zeta_one.contracts import Feature, Tier0Output, TierResult
    fixture = scenario("routine_bill_payment")
    soft = Tier0Output(result=TierResult(tier="tier0", level="elevated"),
                       features={"amount_ratio_to_vendor_median": Feature(value=3.0, raw_value=3.0)})
    strong = CountingStrong()
    risk = assess(fixture.proposal, fixture.context, fixture.decision_record.created_at, lambda *_: soft,
                  {"cheap": JevTier(post=Post(payload(level="low", p=0.97)), key="k"), "strong": strong}, JEV)
    assert strong.calls == 0 and risk.tiers_run == ["tier0", "cheap"]
    assert risk.level == "low" and risk.lowered.by == "cheap"


def test_jev_cannot_lower_a_tier_0_floor():
    risk, calls = _assess("vendor_payment_method_changed", payload(level="low", p=0.99))
    assert risk.level == "elevated" and risk.floor is not None


def test_an_unsure_jev_hands_over_to_the_strong_tier():
    risk, calls = _assess("vendor_payment_method_changed", payload(level="low", p=0.5))
    assert calls == 1 and risk.tiers_run == ["tier0", "cheap", "strong"] and risk.level_set_by == "strong"


def test_a_failed_jev_is_challenged_without_calling_the_strong_tier():
    risk, calls = _assess("vendor_payment_method_changed", None)
    outcome = policy.decide(policy.PolicyInput(_verified(), _no_violations(), _grant(), risk, scenario("vendor_payment_method_changed").proposal))
    assert calls == 0 and outcome.decision == "challenge" and "risk:model_unavailable" in outcome.reasons


def test_the_thresholds_are_recorded_with_the_configuration():
    assert json.loads(JEV.model_dump_json())["jev_min_confidence"] == 0.8


def _verified():
    from zeta_one.contracts import IdentityEvidence
    return IdentityEvidence(result="verified", claimed_agent_id="agent", business_id="biz")


def _no_violations():
    from zeta_one.contracts import AuthorizationEvidence
    return AuthorizationEvidence()


def _grant():
    from zeta_one.contracts import Authorization
    return Authorization(authorization_id="a", version=1, policy_version="p", business_id="biz", agent_id="agent",
                         granted_by="owner", granted_at="2026-10-01T00:00:00Z")


@pytest.mark.live_models
def test_live_jev_call():
    """One real call, to settle TypeSafe's request and response shapes. Needs TYPESAFE_API_KEY."""
    if not jev.api_key():
        pytest.skip("TYPESAFE_API_KEY is not set")
    output = JevTier().assess(risk_input())
    assert output.result.error is None, output.result.error
    assert output.result.level in ("elevated", "high")


def test_missing_usage_is_estimated_high_not_free():
    output, calls = run({"answers": payload()["answers"]})
    state = calls[0][2]["state"]
    assert output.result.usage.input_tokens >= len(state) // 4 and output.result.usage.estimated is True


def test_the_missing_key_test_never_reads_the_checkouts_env(monkeypatch, tmp_path):
    monkeypatch.delenv(jev.KEY_NAME, raising=False)
    monkeypatch.setattr(jev, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("")
    assert jev.api_key() is None
