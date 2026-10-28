"""Payment proposals must name a positive, bounded amount in an ISO currency code."""
import json

import pytest

from zeta_one.contracts import (
    MAX_ID_LENGTH,
    MAX_MEMO_LENGTH,
    MAX_PAYMENT_MINOR_UNITS,
    MAX_RATIONALE_LENGTH,
    MAX_SOURCE_DOCUMENTS,
    InvalidProposal,
    Proposal,
)
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.testing.replay import replay_engine, request_for


def _request_with(amount=None, currency=None, **fields):
    scenario = load_fixture('routine_bill_payment')
    request = request_for(scenario)
    body = json.loads(request.body)
    if amount is not None:
        body['amount']['amount'] = amount
    if currency is not None:
        body['amount']['currency'] = currency
    body.update(fields)
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


@pytest.mark.parametrize('field, value', [
    ('memo', 'x' * (MAX_MEMO_LENGTH + 1)),
    ('agent_rationale', 'x' * (MAX_RATIONALE_LENGTH + 1)),
    ('counterparty_id', 'c' * (MAX_ID_LENGTH + 1)),
    ('source_document_ids', ['bill'] * (MAX_SOURCE_DOCUMENTS + 1)),
    ('source_document_ids', ['b' * (MAX_ID_LENGTH + 1)]),
])
def test_oversized_text_is_rejected_before_authorization(field, value):
    _rejected_before_authorization(*_request_with(**{field: value}), match='at most')


def test_text_at_the_caps_is_accepted():
    _, request = _request_with(memo='x' * MAX_MEMO_LENGTH, agent_rationale='x' * MAX_RATIONALE_LENGTH)
    assert len(Proposal.model_validate_json(request.body).agent_rationale) == MAX_RATIONALE_LENGTH


@pytest.mark.parametrize('amount', [True, '185000', 185000.0])
def test_an_amount_that_is_not_a_json_integer_is_refused(amount):
    _rejected_before_authorization(*_request_with(amount=amount), match='integer|valid')


@pytest.mark.parametrize('window_days', [0, -5])
def test_a_rolling_limit_needs_a_window_of_at_least_a_day(window_days):
    from pydantic import ValidationError

    from zeta_one.contracts import RollingLimit
    with pytest.raises(ValidationError):
        RollingLimit(window_days=window_days, amount={'amount': 600000, 'currency': 'USD'})
