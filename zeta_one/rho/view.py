"""Gateway-owned context lookup, with a three-payment summary and a complete duplicate window."""
from datetime import datetime, timedelta
from statistics import median

from zeta_one.contracts import (BillView, BusinessView, Context, CounterpartyView,
    InvalidProposal, MethodUse, PaymentHistory, PaymentMethodChange, PaymentMethodView, PaymentRecord)
from zeta_one.rho.models import Money
from zeta_one.risk.features import DUPLICATE_DAYS

METHOD_TYPES = {'ach_debit':'ach', 'wire_out':'wire', 'check_payment':'check',
                'international_wire_out':'international_wire'}


def context_for(store):
    def owned(table, record_id, business_id):
        owner = store.get('ownership', f'{table}:{record_id}')
        return owner is not None and owner['business_id'] == business_id

    def counterparty(cp):
        methods = []
        for method in cp['payment_methods']:
            date = store.get('method_dates', method['id']) if method['id'] else None
            methods.append(PaymentMethodView(**method, added_at=date['added_at'] if date else None))
        return CounterpartyView(id=cp['id'], name=cp['legal_name'], status=cp['status'],
                                created_at=cp['created_at'], payment_methods=methods)

    def settled(bill, business_id, now, currency=None):
        """The settled payment a paid bill is linked to, or None."""
        if bill['status'] != 'paid' or not bill['transaction'] or not owned('bills', bill['id'], business_id):
            return None
        txn = store.get('transactions', bill['transaction']['id'])
        if (not txn or txn['status'] != 'settled' or not txn['posted_at']
            or txn['transaction_type'] not in METHOD_TYPES or (currency and txn['amount']['currency'] != currency)
            or not owned('accounts',txn['account_id'],business_id)):
            return None
        posted = datetime.fromisoformat(txn['posted_at'].replace('Z','+00:00'))
        if posted > now:
            return None
        destination = store.get('payment_destinations', txn['id'])
        return PaymentRecord(id=txn['id'], posted_at=posted, amount=txn['amount'],
            method_type=METHOD_TYPES[txn['transaction_type']], bill_id=bill['id'],
            payment_method_id=destination['payment_method_id'] if destination else None)

    def bill_view(bill, business_id, now):
        cp = store.get('counterparties', bill['counterparty']['id'])
        text = store.get('bill_text', bill['id'])
        return BillView(id=bill['id'], counterparty_id=cp['id'], counterparty_name=cp['legal_name'],
            amount=bill['amount'], invoice_number=bill['invoice_number'], invoice_date=bill['invoice_date'],
            due_date=bill['due_date'], memo=bill['memo'], document_excerpt=text['text'] if text else None,
            status=bill['status'], paid_by=settled(bill, business_id, now))

    def history(cp_id, currency, business_id, now, changes):
        transactions = {}
        for bill in store.all('bills'):
            if not bill['counterparty'] or bill['counterparty']['id'] != cp_id:
                continue
            record = settled(bill, business_id, now, currency)
            if record:
                transactions[record.id] = record
        records = sorted(transactions.values(), key=lambda r:(r.posted_at,r.id), reverse=True)
        if not records:
            return PaymentHistory()
        latest_change = {}
        for change in changes:
            if change.method_id not in latest_change or change.changed_at > latest_change[change.method_id]:
                latest_change[change.method_id] = change.changed_at
        by_method = []
        for method_id in sorted({r.payment_method_id for r in records if r.payment_method_id}):
            used = [r for r in records if r.payment_method_id == method_id]
            since = latest_change.get(method_id)
            by_method.append(MethodUse(payment_method_id=method_id, count=len(used), first_at=used[-1].posted_at,
                last_at=used[0].posted_at, since_latest_change=sum(1 for r in used if since is None or r.posted_at > since)))
        return PaymentHistory(count=len(records), first_at=records[-1].posted_at, last_at=records[0].posted_at,
            median_amount=Money(amount=int(median(r.amount.amount for r in records)),currency=currency),
            recent=[r for r in records if r.posted_at >= now-timedelta(days=90)][:3],
            duplicate_candidates=[r for r in records if r.posted_at >= now-timedelta(days=DUPLICATE_DAYS)],
            by_method=by_method)

    def changes_of(cp_id, now):
        return [PaymentMethodChange.model_validate({k: v for k, v in r.items() if k != 'counterparty_id'})
                for r in store.all('method_history')
                if r['counterparty_id'] == cp_id and datetime.fromisoformat(r['changed_at'].replace('Z','+00:00')) <= now]

    def source(proposal, business_id, now):
        business = store.get('businesses', business_id)
        cp = store.get('counterparties', proposal.counterparty_id)
        if not business or not cp or not owned('counterparties',proposal.counterparty_id,business_id):
            raise InvalidProposal('Unknown counterparty for business')
        if not any(m['id'] == proposal.payment_method_id for m in cp['payment_methods']):
            raise InvalidProposal('Payment method is not on counterparty')
        if not owned('accounts',proposal.source_account_id,business_id) or not store.get('accounts',proposal.source_account_id):
            raise InvalidProposal('Source account is outside business')
        bill = store.get('bills',proposal.bill_id) if proposal.bill_id else None
        if proposal.bill_id and (not bill or not owned('bills',proposal.bill_id,business_id)):
            raise InvalidProposal('Unknown bill for business')
        if bill and (not bill['counterparty'] or not bill['amount']):
            raise InvalidProposal('Bill lacks payee or amount')
        other = store.get('counterparties',bill['counterparty']['id']) if bill and bill['counterparty']['id'] != cp['id'] else None
        changes = changes_of(cp['id'], now)
        return Context(business=BusinessView(id=business_id,name=business['legal_name']),
            counterparty=counterparty(cp),
            payment_method_history=changes,
            bill=bill_view(bill, business_id, now) if bill else None,
            payment_history=history(cp['id'],proposal.amount.currency,business_id,now,changes),
            bill_counterparty=counterparty(other) if other else None,
            bill_counterparty_payment_history=history(other['id'],proposal.amount.currency,business_id,now,
                                                      changes_of(other['id'], now)) if other else None,
            open_bills=[bill_view(b, business_id, now) for b in store.all('bills') if b['counterparty'] and b['counterparty']['id']==cp['id']
                and b['status'] not in ('paid','canceled','cancelled') and b['amount'] and owned('bills',b['id'],business_id)])
    return source
