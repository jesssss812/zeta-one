"""Gateway-owned context lookup. Recent history means latest three payments within 90 days."""
from datetime import datetime, timedelta
from statistics import median

from zeta_one.contracts import (BillView, BusinessView, Context, CounterpartyView,
    InvalidProposal, PaymentHistory, PaymentMethodChange, PaymentMethodView, PaymentRecord)
from zeta_one.rho.models import Money

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

    def bill_view(bill):
        cp = store.get('counterparties', bill['counterparty']['id'])
        text = store.get('bill_text', bill['id'])
        return BillView(id=bill['id'], counterparty_id=cp['id'], counterparty_name=cp['legal_name'],
            amount=bill['amount'], invoice_number=bill['invoice_number'], invoice_date=bill['invoice_date'],
            due_date=bill['due_date'], memo=bill['memo'], document_excerpt=text['text'] if text else None,
            status=bill['status'])

    def history(cp_id, currency, business_id, now):
        transactions = {}
        for bill in store.all('bills'):
            if (bill['status'] != 'paid' or not bill['transaction'] or not bill['counterparty']
                or bill['counterparty']['id'] != cp_id or not owned('bills',bill['id'],business_id)):
                continue
            txn = store.get('transactions', bill['transaction']['id'])
            if (not txn or txn['status'] != 'settled' or not txn['posted_at']
                or txn['transaction_type'] not in METHOD_TYPES or txn['amount']['currency'] != currency
                or not owned('accounts',txn['account_id'],business_id)):
                continue
            posted = datetime.fromisoformat(txn['posted_at'].replace('Z','+00:00'))
            if posted <= now:
                transactions[txn['id']] = PaymentRecord(id=txn['id'], posted_at=posted,
                    amount=txn['amount'], method_type=METHOD_TYPES[txn['transaction_type']], bill_id=bill['id'])
        records = sorted(transactions.values(), key=lambda r:(r.posted_at,r.id), reverse=True)
        if not records:
            return PaymentHistory()
        return PaymentHistory(count=len(records), first_at=records[-1].posted_at, last_at=records[0].posted_at,
            median_amount=Money(amount=int(median(r.amount.amount for r in records)),currency=currency),
            recent=[r for r in records if r.posted_at >= now-timedelta(days=90)][:3])

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
        return Context(business=BusinessView(id=business_id,name=business['legal_name']),
            counterparty=counterparty(cp),
            payment_method_history=[PaymentMethodChange.model_validate({k: v for k, v in r.items() if k != 'counterparty_id'}) for r in store.all('method_history')
                if r['counterparty_id'] == cp['id'] and datetime.fromisoformat(r['changed_at'].replace('Z','+00:00')) <= now],
            bill=bill_view(bill) if bill else None,
            payment_history=history(cp['id'],proposal.amount.currency,business_id,now),
            bill_counterparty=counterparty(other) if other else None,
            bill_counterparty_payment_history=history(other['id'],proposal.amount.currency,business_id,now) if other else None,
            open_bills=[bill_view(b) for b in store.all('bills') if b['counterparty'] and b['counterparty']['id']==cp['id']
                and b['status'] not in ('paid','canceled','cancelled') and b['amount'] and owned('bills',b['id'],business_id)])
    return source
