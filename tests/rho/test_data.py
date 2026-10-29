import json
from pathlib import Path

import pytest

from zeta_one.contracts import Context, InvalidProposal, Money, Proposal, SetupOp
from zeta_one.rho.snapshot import Store
from zeta_one.rho.seed import SEED_NOW, make_seed
from zeta_one.rho.view import context_for
from zeta_one.rho.mutations import apply

FIXTURES = Path(__file__).resolve().parents[2] / 'data' / 'fixtures'


def routine():
    return Proposal.model_validate(json.loads((FIXTURES / 'routine_bill_payment.json').read_text())['proposal'])


@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*.json')), ids=lambda p: p.stem)
def test_fixture_context_parity(path):
    fixture = json.loads(path.read_text())
    expected = Context.model_validate(fixture['context'])
    actual = context_for(Store())(Proposal.model_validate(fixture['proposal']), expected.business.id, SEED_NOW)
    # The fixtures predate the bill's status and the bill each history payment settled.
    newer = {'open_bills': True, 'bill': {'status'}, 'payment_history': {'recent': {'__all__': {'bill_id'}}, 'duplicate_candidates': True},
             'bill_counterparty_payment_history': {'recent': {'__all__': {'bill_id'}}, 'duplicate_candidates': True}}
    assert actual.model_dump(exclude=newer) == expected.model_dump(exclude=newer)


@pytest.mark.parametrize('field,value', [('counterparty_id','missing'), ('payment_method_id','pm_0007_01'), ('source_account_id','missing'), ('bill_id','missing')])
def test_invalid_proposal(field, value):
    with pytest.raises(InvalidProposal):
        context_for(Store())(routine().model_copy(update={field:value}), 'biz_seed_01', SEED_NOW)


def test_business_isolation():
    with pytest.raises(InvalidProposal):
        context_for(Store())(routine(), 'another_business', SEED_NOW)


def test_open_bills_independent_of_agent_reference():
    store = Store()
    ctx = context_for(store)(routine().model_copy(update={'bill_id':None}), 'biz_seed_01', SEED_NOW)
    assert [b.id for b in ctx.open_bills] == ['bill_0201']
    assert ctx.bill is None


def test_seed_reproducible_and_hash_tracks_bytes(tmp_path):
    make_seed(tmp_path)
    first = Store(tmp_path)
    make_seed(tmp_path)
    assert first.seed_version == Store(tmp_path).seed_version == Store().seed_version
    p = tmp_path / 'provenance.json'
    p.write_text(p.read_text() + '\n')
    assert first.seed_version != Store(tmp_path).seed_version
    assert len(first.all('transactions')) == 150
    assert len(first.all('counterparties')) == 23
    assert len(first.all('accounts')) == 3


def test_mutations_are_local_and_change_context():
    store = Store()
    apply(store, SetupOp(op='change_payment_method', args={'counterparty_id':'cp_0012','days_ago':2}))
    ctx = context_for(store)(routine(), 'biz_seed_01', SEED_NOW)
    assert ctx.payment_method_history[0].changed_at == SEED_NOW.replace(day=25)
    assert context_for(Store())(routine(), 'biz_seed_01', SEED_NOW).payment_method_history == []
    apply(store, SetupOp(op='set_bill_text', args={'bill_id':'bill_0201','text':'Changed invoice text'}))
    assert context_for(store)(routine(), 'biz_seed_01', SEED_NOW).bill.document_excerpt == 'Changed invoice text'


def test_add_counterparty_bill_and_payments():
    store = Store()
    apply(store, SetupOp(op='add_counterparty', args={'id':'cp_new','name':'New vendor','days_ago':40,'payment_method_id':'pm_new'}))
    apply(store, SetupOp(op='add_bill', args={'id':'bill_new','counterparty_id':'cp_new','amount':{'amount':100,'currency':'USD'},'text':'Invoice'}))
    apply(store, SetupOp(op='add_payments', args={'counterparty_id':'cp_new','count':3,'amount':{'amount':200,'currency':'USD'},'days_ago':10}))
    proposal = routine().model_copy(update={'counterparty_id':'cp_new','payment_method_id':'pm_new','bill_id':'bill_new'})
    ctx = context_for(store)(proposal, 'biz_seed_01', SEED_NOW)
    assert ctx.counterparty.name == 'New vendor'
    assert ctx.bill.document_excerpt == 'Invoice'
    assert ctx.payment_history.count == 3
    assert ctx.payment_history.median_amount.amount == 200
    assert [b.id for b in ctx.open_bills] == ['bill_new']
    apply(store, SetupOp(op='add_payments', args={'counterparty_id':'cp_new','count':2,'amount':{'amount':999,'currency':'EUR'}}))
    assert context_for(store)(proposal, 'biz_seed_01', SEED_NOW).payment_history.count == 3


def test_unknown_mutation_rejected():
    with pytest.raises(ValueError):
        apply(Store(), SetupOp(op='no_such_op'))


def test_evaluation_mutation_argument_shapes():
    store = Store()
    ops = [
        SetupOp(op='add_counterparty', args={'counterparty_id':'cp_eval', 'name':'Evaluation vendor',
                'created_days_ago':400, 'payment_method_id':'pm_eval'}),
        SetupOp(op='add_payments', args={'counterparty_id':'cp_eval', 'count':12,
                'median_amount':200000, 'currency':'USD'}),
        SetupOp(op='change_payment_method', args={'counterparty_id':'cp_eval', 'days_ago':3,
                'new_method_id':'pm_changed', 'verified_with_vendor':True}),
        SetupOp(op='add_bill', args={'bill_id':'bill_eval', 'counterparty_id':'cp_eval',
                'amount':200000, 'currency':'USD', 'document_text':'Synthetic invoice'})]
    for op in ops:
        apply(store, op)
    p = routine().model_copy(update={'counterparty_id':'cp_eval', 'payment_method_id':'pm_changed',
                                     'bill_id':'bill_eval'})
    ctx = context_for(store)(p, 'biz_seed_01', SEED_NOW)
    assert ctx.payment_history.count == 12
    assert ctx.payment_history.median_amount.amount == 200000
    assert ctx.bill.document_excerpt == 'Synthetic invoice'
    assert ctx.payment_method_history[0].method_id == 'pm_changed'
    assert (SEED_NOW - ctx.counterparty.created_at).days == 400


def test_history_excludes_unsettled_future_and_wrong_currency_records():
    store = Store()
    before = context_for(store)(routine(), 'biz_seed_01', SEED_NOW).payment_history
    apply(store, SetupOp(op='add_payments', args={'counterparty_id':'cp_0012', 'amount':1,
                                               'days_ago':-1}))
    apply(store, SetupOp(op='add_payments', args={'counterparty_id':'cp_0012', 'amount':1,
                                               'currency':'EUR'}))
    apply(store, SetupOp(op='add_payments', args={'counterparty_id':'cp_0012', 'amount':1}))
    transaction = store.all('transactions')[-1]
    transaction['status'] = 'pending'
    store.put('transactions', transaction)
    assert context_for(store)(routine(), 'biz_seed_01', SEED_NOW).payment_history == before


def test_context_can_be_read_from_gateway_worker_thread():
    from concurrent.futures import ThreadPoolExecutor
    store = Store()
    source = context_for(store)
    with ThreadPoolExecutor(max_workers=1) as worker:
        context = worker.submit(source, routine(), 'biz_seed_01', SEED_NOW).result()
    assert context.counterparty.id == 'cp_0012'


@pytest.mark.parametrize('days_ago, duplicate', [(4, True), (7, True), (8, False)])
def test_duplicate_window_includes_payments_beyond_the_three_item_summary(days_ago, duplicate):
    from zeta_one.risk.tier0 import Tier0
    from zeta_one.risk.assess import assess
    from zeta_one.contracts import Configuration

    store = Store()
    proposal = routine()
    for age, amount in [(days_ago, 185000), (1, 185001), (2, 185002), (3, 185003)]:
        apply(store, SetupOp(op='add_payments', args={'counterparty_id': proposal.counterparty_id,
                                                    'amount': amount, 'days_ago': age}))
    context = context_for(store)(proposal, 'biz_seed_01', SEED_NOW)
    assert len(context.payment_history.recent) == 3
    assert all(payment.amount.amount != 185000 for payment in context.payment_history.recent)
    risk = assess(proposal, context, SEED_NOW, Tier0(), {}, Configuration(tiers=['tier0']))
    assert risk.features['duplicate_candidate'].value is duplicate
    assert bool(risk.floor) is duplicate


def _vendor(store, **details):
    apply(store, SetupOp(op='add_counterparty', args={'counterparty_id': 'cp_dest', 'name': 'Destination vendor',
          'created_days_ago': 400, 'payment_method_id': 'pm_old', **details}))
    return routine().model_copy(update={'counterparty_id': 'cp_dest', 'payment_method_id': 'pm_old', 'bill_id': None})


def test_payments_record_their_destination_and_count_since_the_latest_change():
    store = Store()
    proposal = _vendor(store)
    for days in (130, 100):
        apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'amount': 500,
              'days_ago': days, 'payment_method_id': 'pm_old'}))
    apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'amount': 500, 'days_ago': 70}))
    apply(store, SetupOp(op='change_payment_method', args={'counterparty_id': 'cp_dest', 'days_ago': 50,
          'new_method_id': 'pm_new', 'account_ending': '9088'}))
    for days in (40, 10):
        apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'amount': 500,
              'days_ago': days, 'payment_method_id': 'pm_new'}))
    history = context_for(store)(proposal.model_copy(update={'payment_method_id': 'pm_new'}),
                                 'biz_seed_01', SEED_NOW).payment_history
    assert history.count == 5
    assert [r.payment_method_id for r in history.recent] == ['pm_new', 'pm_new', None]
    uses = {u.payment_method_id: (u.count, u.since_latest_change) for u in history.by_method}
    assert uses == {'pm_new': (2, 2), 'pm_old': (2, 2)}  # the unlinked payment is in neither


def test_a_payment_can_pay_a_named_bill_once():
    store = Store()
    proposal = _vendor(store)
    apply(store, SetupOp(op='add_bill', args={'bill_id': 'bill_named', 'counterparty_id': 'cp_dest', 'amount': 2100}))
    apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'bill_id': 'bill_named',
          'days_ago': 45, 'payment_method_id': 'pm_old'}))
    named = proposal.model_copy(update={'bill_id': 'bill_named', 'amount': Money(amount=2100, currency='USD')})
    ctx = context_for(store)(named, 'biz_seed_01', SEED_NOW)
    assert ctx.bill.status == 'paid' and ctx.open_bills == []
    assert (SEED_NOW - ctx.bill.paid_by.posted_at).days == 45
    assert ctx.bill.paid_by.amount.amount == 2100 and ctx.bill.paid_by.payment_method_id == 'pm_old'
    with pytest.raises(ValueError):
        apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'bill_id': 'bill_named'}))
    with pytest.raises(ValueError):
        apply(store, SetupOp(op='add_payments', args={'counterparty_id': 'cp_dest', 'payment_method_id': 'pm_other'}))


def test_method_details_and_email_reach_the_context():
    store = Store()
    proposal = _vendor(store, email='ap@vendor.example', account_ending='4821', beneficiary_name='Vendor Ltd')
    apply(store, SetupOp(op='change_payment_method', args={'counterparty_id': 'cp_dest', 'new_method_id': 'pm_new',
          'beneficiary_name': 'Vendor Settlement Partners'}))
    cp = context_for(store)(proposal, 'biz_seed_01', SEED_NOW).counterparty
    assert cp.email == 'ap@vendor.example'
    assert {m.id: (m.account_ending, m.beneficiary_name) for m in cp.payment_methods} == {
        'pm_old': ('4821', 'Vendor Ltd'), 'pm_new': (None, 'Vendor Settlement Partners')}
    assert all(m.added_at is not None for m in cp.payment_methods)
    with pytest.raises(ValueError):
        apply(store, SetupOp(op='change_payment_method', args={'counterparty_id': 'cp_dest', 'account_ending': '48-21'}))
