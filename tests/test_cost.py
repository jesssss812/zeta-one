"""The evidence record's cost: cache tokens priced, unpriced models named."""

import pytest

from zeta_one.contracts import GpuRate, RiskEvidence, TierResult, Usage
from zeta_one.decide.evidence import _cost

PRICES = {"claude-opus-5-5": (4.0, 20.0)}


def _risk(model="claude-opus-5-5", **usage) -> RiskEvidence:
    return RiskEvidence(tier_results=[TierResult(tier="tier0"), TierResult(tier="strong", model=model, usage=Usage(**usage))])


def test_cache_reads_and_writes_are_priced_from_the_input_price():
    cost = _cost(_risk(input_tokens=100, output_tokens=10, cache_read_input_tokens=50_000,
                       cache_creation_input_tokens=3_000), PRICES)
    expected = (100 + 50_000 * 0.1 + 3_000 * 1.25) * 4.0 / 1e6 + 10 * 20.0 / 1e6
    assert cost.usd == pytest.approx(expected)
    assert (cost.cache_read_input_tokens, cost.cache_creation_input_tokens) == (50_000, 3_000)


def test_an_unpriced_model_is_named_not_silently_free():
    cost = _cost(_risk(model="claude-other", input_tokens=100, output_tokens=10), PRICES)
    assert cost.usd == 0.0 and cost.input_tokens == 100
    assert cost.unpriced_models == ["claude-other"] and cost.prices_used == {}


def test_no_model_call_costs_nothing():
    cost = _cost(RiskEvidence(tier_results=[TierResult(tier="tier0")]), PRICES)
    assert (cost.usd, cost.input_tokens, cost.unpriced_models) == (0.0, 0, [])


def test_a_self_hosted_model_is_charged_its_gpu_time_per_call_failed_calls_included():
    risk = RiskEvidence(tier_results=[
        TierResult(tier="tier0"),
        TierResult(tier="open_weight", model="own-model", latency_ms=18_000, usage=Usage(input_tokens=4000, output_tokens=300)),
        TierResult(tier="open_weight", model="own-model", latency_ms=3_600, error="http_500"),
    ])
    cost = _cost(risk, {"own-model": GpuRate(0.59)})
    assert cost.usd == pytest.approx((18_000 + 3_600) / 3_600_000 * 0.59)
    assert cost.input_tokens == 4000 and cost.unpriced_models == []
    assert cost.prices_used["own-model"]["gpu_usd_per_hour"] == 0.59
