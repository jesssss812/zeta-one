"""The evidence record's cost: cache tokens priced, unpriced models named."""

import pytest

from zeta_one.contracts import RiskEvidence, TierResult, Usage
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
