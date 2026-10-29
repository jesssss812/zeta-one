"""Synthetic setup mutations on an isolated Store, with dates relative to SEED_NOW.

Operations and args (all optional defaults are synthetic):
- add_counterparty: counterparty_id (alias id), name, created_days_ago (alias
  days_ago, default 40), payment_method_id, business_id (default biz_seed_01).
- change_payment_method: counterparty_id, days_ago (default 0), new_method_id
  (optional; otherwise update the default method), bank_name, type (default ach),
  verified_with_vendor (stored provenance, never a trusted risk override).
- set_bill_text: bill_id, text (alias document_text).
- add_bill: bill_id (alias id), counterparty_id, amount (Money dict or integer
  minor units with currency, default USD), document_text (alias text), status
  (default awaiting_approval), business_id (default biz_seed_01), invoice_number.
- add_payments: counterparty_id, count (default 1), amount (Money dict or integer;
  alias median_amount), currency (default USD), days_ago (default 10),
  source_account_id (default acct_seed_checking_01), payment_method_id (the
  destination; default none recorded), bill_id (an existing unpaid bill of the
  counterparty, which this one payment pays; count must be 1). Creates settled
  outgoing transactions linked through paid bills, one per day counting backwards.

All changes are local simulated data. Unknown references or operations raise
ValueError. Repeated add operations require distinct entity IDs.
"""
from datetime import timedelta

from zeta_one.contracts import SetupOp
from zeta_one.rho.models import Money
from zeta_one.rho.seed import SEED_NOW

BUSINESS = 'biz_seed_01'
ACCOUNT = 'acct_seed_checking_01'


def _stamp(days=0):
    return (SEED_NOW - timedelta(days=days)).isoformat()


def _require(store, table, record_id):
    record = store.get(table, record_id)
    if record is None:
        raise ValueError(f'Unknown {table} record: {record_id}')
    return record


def _new(store, table, record):
    if store.get(table, record['id']) is not None:
        raise ValueError(f'Duplicate {table} id: {record["id"]}')
    store.put(table, record)


def _own(store, table, record_id, business_id):
    _require(store, 'businesses', business_id)
    store.put('ownership', {'id': f'{table}:{record_id}', 'business_id': business_id})


def _money(args):
    value = args.get('amount', args.get('median_amount', 10000))
    return Money.model_validate(value if isinstance(value, dict) else
                                {'amount': value, 'currency': args.get('currency', 'USD')}).model_dump()


def apply(store, op: SetupOp):
    """Apply one operation to this store only; the committed seed stays unchanged."""
    a = op.args
    if op.op == 'add_counterparty':
        cp_id = a.get('counterparty_id', a.get('id'))
        if not cp_id:
            raise ValueError('counterparty_id is required')
        business = a.get('business_id', BUSINESS)
        _require(store, 'businesses', business)
        method_id = a.get('payment_method_id', f'pm_{cp_id}')
        stamp = _stamp(a.get('created_days_ago', a.get('days_ago', 40)))
        _new(store, 'counterparties', {'id': cp_id, 'legal_name': a.get('name', 'Synthetic vendor'),
             'status': 'active', 'is_business': True, 'created_at': stamp, 'updated_at': stamp,
             'payment_methods': [{'id': method_id, 'type': 'ach', 'is_default': True,
                                  'bank_name': 'Synthetic Community Bank'}]})
        _own(store, 'counterparties', cp_id, business)
        store.put('method_dates', {'id': method_id, 'added_at': stamp})
    elif op.op == 'change_payment_method':
        cp = _require(store, 'counterparties', a['counterparty_id'])
        method_id = a.get('new_method_id')
        if method_id is None:
            method_id = next((m['id'] for m in cp['payment_methods'] if m['is_default']), None)
        if not method_id:
            raise ValueError('new_method_id is required for a counterparty without a default method')
        stamp = _stamp(a.get('days_ago', 0))
        found = False
        for method in cp['payment_methods']:
            method['is_default'] = method['id'] == method_id
            if method['is_default']:
                found = True
                method['bank_name'] = a.get('bank_name', method.get('bank_name'))
        if not found:
            cp['payment_methods'].insert(0, {'id': method_id, 'type': a.get('type', 'ach'),
                'is_default': True, 'bank_name': a.get('bank_name', 'Synthetic Updated Bank')})
            store.put('method_dates', {'id': method_id, 'added_at': stamp})
        cp['updated_at'] = stamp
        store.put('counterparties', cp)
        index = len(store.all('method_history'))
        history_id = f'pmh_setup_{index:05}'
        while store.get('method_history', history_id):
            index += 1
            history_id = f'pmh_setup_{index:05}'
        store.put('method_history', {'id': history_id, 'counterparty_id': cp['id'],
            'method_id': method_id, 'change': 'added_as_default' if not found else 'updated',
            'changed_at': stamp, 'changed_by': 'synthetic_setup',
            'summary': 'Simulated payment-method change',
            'verified_with_vendor': a.get('verified_with_vendor', False)})
    elif op.op == 'set_bill_text':
        _require(store, 'bills', a['bill_id'])
        store.put('bill_text', {'id': a['bill_id'], 'text': a.get('text', a.get('document_text', ''))})
    elif op.op == 'add_bill':
        cp = _require(store, 'counterparties', a['counterparty_id'])
        owner = _require(store, 'ownership', f'counterparties:{cp["id"]}')['business_id']
        business = a.get('business_id', owner)
        if business != owner:
            raise ValueError('Bill counterparty is outside business')
        bill_id = a.get('bill_id', a.get('id'))
        if not bill_id:
            raise ValueError('bill_id is required')
        _new(store, 'bills', {'id': bill_id, 'status': a.get('status', 'awaiting_approval'),
            'amount': _money(a), 'counterparty': {'id': cp['id']}, 'transaction': None,
            'invoice_number': a.get('invoice_number'), 'memo': 'Synthetic bill',
            'created_at': _stamp(), 'updated_at': _stamp()})
        _own(store, 'bills', bill_id, business)
        store.put('bill_text', {'id': bill_id, 'text': a.get('document_text', a.get('text', 'Synthetic invoice.'))})
    elif op.op == 'add_payments':
        cp = _require(store, 'counterparties', a['counterparty_id'])
        owner = _require(store, 'ownership', f'counterparties:{cp["id"]}')['business_id']
        account = a.get('source_account_id', ACCOUNT)
        _require(store, 'accounts', account)
        if _require(store, 'ownership', f'accounts:{account}')['business_id'] != owner:
            raise ValueError('Payment source account is outside business')
        count = a.get('count', 1)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError('count must be a nonnegative integer')
        method_id = a.get('payment_method_id')
        if method_id is not None and not any(m['id'] == method_id for m in cp['payment_methods']):
            raise ValueError(f'Payment method {method_id} is not on counterparty')
        paid = a.get('bill_id')
        if paid is not None:
            bill = _require(store, 'bills', paid)
            if bill['counterparty']['id'] != cp['id'] or bill['status'] == 'paid' or count != 1:
                raise ValueError('bill_id must be an unpaid bill of the counterparty, paid by one payment')
        amount = _money(a) if paid is None or 'amount' in a or 'median_amount' in a else bill['amount']
        for n in range(count):
            index = len(store.all('transactions'))
            transaction_id = f'txn_setup_{index:05}'
            while store.get('transactions', transaction_id):
                index += 1
                transaction_id = f'txn_setup_{index:05}'
            stamp = _stamp(a.get('days_ago', 10) + n)
            store.put('transactions', {'id': transaction_id, 'account_id': account,
                'transaction_type': 'ach_debit', 'status': 'settled', 'amount': amount,
                'counterparty_name': cp['legal_name'], 'posted_at': stamp, 'initiated_at': stamp})
            if method_id is not None:
                store.put('payment_destinations', {'id': transaction_id, 'payment_method_id': method_id})
            if paid is not None:
                store.put('bills', {**bill, 'status': 'paid', 'transaction': {'id': transaction_id},
                                    'created_at': min(bill['created_at'], stamp), 'updated_at': stamp})
                continue
            bill_id = f'paid_{transaction_id}'
            store.put('bills', {'id': bill_id, 'status': 'paid', 'amount': amount,
                'counterparty': {'id': cp['id']}, 'transaction': {'id': transaction_id},
                'created_at': stamp, 'updated_at': stamp})
            _own(store, 'bills', bill_id, owner)
    else:
        raise ValueError(f'Unknown setup operation: {op.op}')
