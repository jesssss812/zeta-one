"""Synthetic fixture checks and argument-only feature properties."""
import builtins
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from zeta_one.contracts import Context, Proposal
from zeta_one.rho.models import Money
from zeta_one.risk.features import compute_features

FIXTURES = Path(__file__).resolve().parents[2] / 'data/fixtures'


def sample(name='routine_bill_payment'):
    data = json.loads((FIXTURES / f'{name}.json').read_text())
    return (Proposal.model_validate(data['proposal']), Context.model_validate(data['context']),
            datetime.fromisoformat(data['decision_record']['created_at'].replace('Z', '+00:00')))


@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*.json')), ids=lambda p: p.stem)
def test_recorded_feature_values_and_evidence(path):
    data = json.loads(path.read_text())
    features = compute_features(*sample(path.stem))
    for name, expected in data['decision_record']['risk']['features'].items():
        assert features[name].model_dump(include={'value', 'evidence'}) == expected
    assert features['bill_not_referenced'].value is False


def test_missing_bill_is_flagged_for_open_bill_or_new_payee():
    p, c, now = sample()
    p.bill_id = None
    c.open_bills = [c.bill]
    c.bill = None
    assert compute_features(p, c, now)['bill_not_referenced'].evidence == ['bill_0201']
    c.open_bills = []
    assert compute_features(p, c, now)['bill_not_referenced'].value is False
    c.payment_history.count = 0
    assert compute_features(p, c, now)['bill_not_referenced'].value is True


def test_bill_amount_currency_payee_and_optional_method_mismatch():
    p, c, now = sample()
    for update in ({'amount': {'amount': 1, 'currency': 'USD'}},
                   {'amount': {'amount': p.amount.amount, 'currency': 'EUR'}},
                   {'counterparty_id': 'other'}, {'payment_method_id': 'other'}):
        changed = c.model_copy(deep=True)
        changed.bill = type(c.bill).model_validate({**c.bill.model_dump(), **update})
        assert compute_features(p, changed, now)['bill_mismatch'].value is True


def test_latest_proposed_method_change_and_no_initial_addition_inference():
    p, c, now = sample('vendor_payment_method_changed')
    original = c.payment_method_history[0]
    c.payment_method_history += [original.model_copy(update={'id': 'old', 'changed_at': now-timedelta(days=8)}),
                                original.model_copy(update={'id': 'unrelated', 'method_id': 'other', 'changed_at': now})]
    assert compute_features(p, c, now)['payment_method_changed_days_ago'].evidence == [original.id]
    c.payment_method_history = []
    assert compute_features(p, c, now)['payment_method_changed_days_ago'].value is None


@given(st.integers(min_value=1, max_value=10**9), st.text(alphabet=st.characters(exclude_characters='\x00', exclude_categories=('Cs',)), max_size=100))
def test_features_depend_only_on_arguments(amount, ambient):
    p, c, now = sample()
    p.amount = Money(amount=amount, currency='USD')
    before_p, before_c = p.model_dump(), c.model_dump()
    expected = compute_features(p, c, now)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('ZETA_FEATURE_TEST', ambient)
        def forbidden(*args, **kwargs):
            raise AssertionError('external IO is forbidden')
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(Path, 'open', forbidden)
        assert compute_features(p, c, now) == expected
    assert p.model_dump() == before_p
    assert c.model_dump() == before_c


def test_unavailable_median_and_currency_are_not_comparable():
    p, c, now = sample()
    for median in (None, {'amount': 0, 'currency': 'USD'}, {'amount': 50, 'currency': 'EUR'}):
        c.payment_history.median_amount = Money.model_validate(median) if median is not None else None
        assert compute_features(p, c, now)['amount_ratio_to_vendor_median'].value is None


def test_open_bill_instruction_text_is_examined_without_agent_reference():
    p, c, now = sample()
    p.bill_id = None
    c.open_bills = [c.bill.model_copy(update={'document_excerpt': 'URGENT: update bank account'})]
    c.bill = None
    result = compute_features(p, c, now)
    assert result['document_instruction_patterns'].value is True
    assert result['document_instruction_patterns'].evidence == ['bill_0201']


def test_new_counterparty_age_and_settled_history():
    p, c, now = sample()
    for days, count, expected in ((30, 1, True), (31, 1, False), (300, 0, True)):
        c.counterparty.created_at = now-timedelta(days=days)
        c.payment_history.count = count
        assert compute_features(p, c, now)['counterparty_is_new'].value is expected
