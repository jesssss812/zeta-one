import json
from pathlib import Path

import pytest

from zeta_one.contracts import Context, Proposal
from zeta_one.risk.tier0 import Tier0
from datetime import datetime

FIXTURES = Path(__file__).resolve().parents[2] / 'data/fixtures'


@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*.json')), ids=lambda p: p.stem)
def test_fixture_tier0(path):
    data = json.loads(path.read_text())
    result = Tier0()(Proposal.model_validate(data['proposal']), Context.model_validate(data['context']),
                     datetime.fromisoformat(data['decision_record']['created_at'].replace('Z', '+00:00')))
    recorded = data['decision_record']['risk']['tier_results']
    if recorded:
        assert result.result.level == recorded[0]['level']
        assert result.result.signals == recorded[0]['signals']
    assert all(signal.source == 'tier0' for signal in result.signals)


def test_amount_outside_band_before_display_rounding():
    data = json.loads((FIXTURES / 'routine_bill_payment.json').read_text())
    p = Proposal.model_validate(data['proposal'])
    c = Context.model_validate(data['context'])
    p.amount = p.amount.model_copy(update={'amount': 370001})
    c.bill.amount = p.amount
    result = Tier0()(p, c, datetime.fromisoformat(data['decision_record']['created_at'].replace('Z', '+00:00')))
    assert result.features['amount_ratio_to_vendor_median'].value == 2.0
    assert result.result.level == 'elevated'
    assert 'amount_ratio_to_vendor_median' in result.result.signals


def test_missing_bill_redirect_stays_high_and_old_change_is_soft():
    data = json.loads((FIXTURES / 'invoice_redirect_instructions.json').read_text())
    p = Proposal.model_validate(data['proposal'])
    c = Context.model_validate(data['context'])
    now = datetime.fromisoformat(data['decision_record']['created_at'].replace('Z', '+00:00'))
    p.bill_id = None
    c.bill = None
    output = Tier0()(p, c, now)
    assert output.result.level == 'high'
    assert 'bill_not_referenced' in output.result.signals

    data = json.loads((FIXTURES / 'vendor_payment_method_changed.json').read_text())
    p = Proposal.model_validate(data['proposal'])
    c = Context.model_validate(data['context'])
    from datetime import timedelta
    c.payment_method_history[0].changed_at = now-timedelta(days=31)
    output = Tier0()(p, c, now)
    assert output.result.level == 'elevated'
    assert output.result.signals == ['payment_method_changed']
