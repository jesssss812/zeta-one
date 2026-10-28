"""Payment proposals must name a positive, bounded amount in an ISO currency code."""
import json

import pytest

from zeta_one.contracts import MAX_PAYMENT_MINOR_UNITS, InvalidProposal, Proposal
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.testing.replay import replay_engine, request_for


def _request_with(amount=None, currency=None):
    scenario = load_fixture('routine_bill_payment')
    request = request_for(scenario)
    body = json.loads(request.body)
    if amount is not None:
        body['amount']['amount'] = amount
    if currency is not None:
        body['amount']['currency'] = currency
    request.body = json.dumps(body).encode()
    return scenario, request


def _rejected_before_authorization(scenario, request, match):
    engine = replay_engine(scenario)
    def forbidden(*args):
        raise AssertionError('invalid amount must not reach authorization or spend')
    engine.load_authorization = forbidden
    with pytest.raises(InvalidProposal, match=match):
        engine.evaluate(request)


@pytest.mark.parametrize('amount', [0, -1, -499900])
def test_nonpositive_proposal_is_rejected_before_authorization(amount):
    _rejected_before_authorization(*_request_with(amount=amount), match='positive')


@pytest.mark.parametrize('amount', [MAX_PAYMENT_MINOR_UNITS + 1, 10**19])
def test_an_oversized_amount_is_rejected_before_authorization(amount):
    _rejected_before_authorization(*_request_with(amount=amount), match='too large')


def test_the_largest_amount_is_accepted():
    _, request = _request_with(amount=MAX_PAYMENT_MINOR_UNITS)
    assert Proposal.model_validate_json(request.body).amount.amount == MAX_PAYMENT_MINOR_UNITS


@pytest.mark.parametrize('currency', ['usd', 'US', 'USDX', 'xyz', ''])
def test_a_malformed_currency_is_rejected_before_authorization(currency):
    _rejected_before_authorization(*_request_with(currency=currency), match='ISO 4217')
