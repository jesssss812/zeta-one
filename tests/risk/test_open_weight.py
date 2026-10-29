"""The open-weight comparison tier against a stubbed OpenAI-compatible API, and one live call behind --live-models."""

import json

import pytest

from tests.risk.test_claude import answer, risk_input
from zeta_one import settings
from zeta_one.risk import claude, open_weight
from zeta_one.risk.open_weight import OpenWeightTier


def reply(content, finish="stop", refusal=None, usage=True):
    body = {"choices": [{"finish_reason": finish, "message": {"role": "assistant", "content": content, "refusal": refusal}}]}
    if usage:
        body["usage"] = {"prompt_tokens": 2100, "completion_tokens": 180}
    return body


class Post:
    def __init__(self, payload, status=200):
        self.payload, self.status, self.calls = payload, status, []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.status, self.payload


def run(payload, status=200):
    post = Post(payload, status)
    tier = OpenWeightTier(post=post, key="k", model_id="org/open-model", base_url="https://example.test/v1")
    return tier.assess(risk_input()), post.calls


def test_an_answer_becomes_an_open_weight_result_handled_like_the_strong_tier():
    output, calls = run(reply(answer()))
    result = output.result
    assert (result.tier, result.model, result.level, result.confidence, result.error) == (
        "open_weight", "org/open-model", "high", None, None)
    assert result.signals[0] == "injection_detected" and all(s.source == "open_weight" for s in output.signals)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (2100, 180)


def test_the_request_is_the_strong_tiers_prompt_and_rendering_with_the_schema():
    _, calls = run(reply(answer()))
    url, headers, body = calls[0]
    assert url == "https://example.test/v1/chat/completions" and headers == {"Authorization": "Bearer k"}
    system, user = body["messages"]
    assert system["content"].startswith(claude.SYSTEM_PROMPT) and '"risk_level"' in system["content"]
    assert "<untrusted_data boundary=" in user["content"] and body["temperature"] == 0


def test_the_request_enforces_the_answer_schema_and_asks_for_no_thinking():
    _, calls = run(reply(answer()))
    body = calls[0][2]
    assert body["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "risk_answer", "schema": claude.StrongAnswer.model_json_schema()}}
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


def test_a_fenced_answer_is_read():
    output, _ = run(reply("```json\n" + answer() + "\n```"))
    assert output.result.error is None and output.result.level == "high"


def test_a_reported_injection_raises_a_low_answer_to_high():
    output, _ = run(reply(answer(risk_level="low", recommended_decision="allow", signals=[])))
    assert output.result.level == "high" and output.result.answered_level == "low"


@pytest.mark.parametrize("payload, status, error", [
    (reply(answer()), 429, "http_429"),
    (TimeoutError("slow"), 200, "TimeoutError"),
    (reply(answer(), finish="length"), 200, "invalid_output: finish_reason length"),
    (reply(None, refusal="I can't help with that."), 200, "refusal"),
    (reply("not json"), 200, "invalid_output"),
    (reply(json.dumps({"risk_level": "catastrophic"})), 200, "invalid_output"),
    ({"choices": []}, 200, "invalid_output: no choice"),
])
def test_each_failure_is_an_error_and_no_level(payload, status, error):
    output, _ = run(payload, status)
    assert output.result.error.startswith(error) and output.result.level is None


def test_no_key_is_an_error_without_a_call(monkeypatch, tmp_path):
    for name in ("OPEN_WEIGHT_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "ROOT", tmp_path)

    def never(*args):
        raise AssertionError("a test without a key made a real call")

    monkeypatch.setattr(open_weight, "_http_post", never)
    assert OpenWeightTier().assess(risk_input()).result.error == "OPEN_WEIGHT_API_KEY is not set"


def test_missing_usage_is_estimated_high_not_free():
    output, _ = run(reply(answer(), usage=False))
    assert output.result.usage.estimated is True and output.result.usage.input_tokens > 1000


def test_prices_are_unset_until_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.delenv("OPEN_WEIGHT_PRICES", raising=False)
    assert open_weight.prices() == {}
    monkeypatch.setenv("OPEN_WEIGHT_PRICES", "0.2,0.6")
    monkeypatch.setenv("OPEN_WEIGHT_MODEL", "org/open-model")
    assert open_weight.prices() == {"org/open-model": (0.2, 0.6)}


@pytest.mark.live_models
def test_live_open_weight_call():
    """One real call to the configured provider and model. Needs OPEN_WEIGHT_API_KEY or OPENROUTER_API_KEY."""
    if not (open_weight.setting("OPEN_WEIGHT_API_KEY") or open_weight.setting("OPENROUTER_API_KEY")):
        pytest.skip("no open-weight key set")
    output = OpenWeightTier().assess(risk_input())
    assert output.result.error is None, output.result.error
    assert output.result.level in ("elevated", "high")

