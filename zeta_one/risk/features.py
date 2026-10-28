"""Pure deterministic risk features over the gateway's supplied evidence."""
from datetime import datetime, timedelta
import re

from zeta_one.contracts import Context, Feature, Proposal
from zeta_one.risk.escalation import RECENT_CHANGE_DAYS

NEW_COUNTERPARTY_DAYS = 30
# Frozen 2026-10-27 before evaluation test-set generation. Case-insensitive regexes.
INSTRUCTION_PATTERN_LEXICON = (
    r'\bupdate\s+(?:our\s+|the\s+)?bank',
    r'\bnew\s+(?:bank\s+)?account\b',
    r'\bbanking\s+has\s+changed\b',
    r'\bignore\b',
    r'\burgent(?:ly)?\b',
    r'\bimmediate(?:ly)?\b',
    r'\bautomated\s+(?:accounts\s+payable\s+)?systems?\b',
    r'\bdo\s+not\s+contact\b',
)


def counterparty_is_new(proposal: Proposal, context: Context, now: datetime) -> Feature:
    age = (now - context.counterparty.created_at).total_seconds() / 86400
    return Feature(value=age <= NEW_COUNTERPARTY_DAYS or context.payment_history.count == 0,
                   evidence=[context.counterparty.id])


def payment_method_changed_days_ago(proposal: Proposal, context: Context, now: datetime) -> Feature:
    changes = [change for change in context.payment_method_history
               if change.method_id == proposal.payment_method_id]
    if not changes:
        return Feature()
    latest = max(changes, key=lambda change: change.changed_at)
    return Feature(value=max(0, (now - latest.changed_at).days), evidence=[latest.id])


def amount_ratio_to_vendor_median(proposal: Proposal, context: Context, now: datetime) -> Feature:
    median = context.payment_history.median_amount
    if median is None or median.amount <= 0 or median.currency != proposal.amount.currency:
        return Feature()
    ratio = proposal.amount.amount / median.amount
    return Feature(value=round(ratio, 2), raw_value=ratio, evidence=[p.id for p in context.payment_history.recent])


def bill_mismatch(proposal: Proposal, context: Context, now: datetime) -> Feature:
    bill = context.bill if proposal.bill_id is not None else None
    if bill is None:
        return Feature(value=False)
    different_payee = proposal.counterparty_id != bill.counterparty_id
    method = getattr(bill, 'payment_method_id', None)
    mismatch = (proposal.bill_id != bill.id or proposal.amount != bill.amount or different_payee
                or (method is not None and method != proposal.payment_method_id))
    evidence = [bill.id]
    if different_payee:
        evidence += [proposal.counterparty_id, bill.counterparty_id]
    return Feature(value=mismatch, evidence=evidence)


def document_instruction_patterns(proposal: Proposal, context: Context, now: datetime) -> Feature:
    bills = {bill.id: bill for bill in context.open_bills}
    if context.bill is not None:
        bills[context.bill.id] = context.bill
    matched = [bill.id for bill in bills.values() if any(
        re.search(pattern, bill.document_excerpt or '', re.IGNORECASE)
        for pattern in INSTRUCTION_PATTERN_LEXICON)]
    return Feature(value=bool(matched), evidence=matched or list(bills))


def bill_not_referenced(proposal: Proposal, context: Context, now: datetime) -> Feature:
    if proposal.bill_id is not None:
        return Feature(value=False)
    new = counterparty_is_new(proposal, context, now)
    changed = payment_method_changed_days_ago(proposal, context, now)
    recent = changed.value is not None and changed.value <= RECENT_CHANGE_DAYS
    evidence = [bill.id for bill in context.open_bills]
    if new.value:
        evidence += new.evidence
    if recent:
        evidence += changed.evidence
    return Feature(value=bool(evidence), evidence=evidence)


DUPLICATE_DAYS = 7


def duplicate_candidate(proposal: Proposal, context: Context, now: datetime) -> Feature:
    """The named bill is already paid (Rho marks it paid, or a payment in Rho's history or the gateway's
    own simulated payments names it), or the same amount went to the payee within DUPLICATE_DAYS."""
    window = now - timedelta(days=DUPLICATE_DAYS)
    matched = []
    bill = context.bill if proposal.bill_id is not None else None
    if bill is not None and bill.status == 'paid':
        matched.append(bill.id)
    payments = {payment.id: payment for payment in [*context.payment_history.recent,
                *context.payment_history.duplicate_candidates, *context.gateway_payments]}
    for payment in payments.values():
        same_bill = proposal.bill_id is not None and getattr(payment, 'bill_id', None) == proposal.bill_id
        same_amount = payment.amount == proposal.amount and payment.posted_at >= window
        if same_bill or same_amount:
            matched.append(payment.id)
    return Feature(value=bool(matched), evidence=matched)


def payment_method_blocked(proposal: Proposal, context: Context, now: datetime) -> Feature:
    """The method was blocked after a verified fraud finding (decision 0013); evidence is the adjustment."""
    blocks = [a.adjustment_id for a in context.adjustments
              if a.kind == 'blocked_payment_method' and a.subject == proposal.payment_method_id]
    return Feature(value=bool(blocks), evidence=blocks)


def payment_method_change_confirmed(proposal: Proposal, context: Context, now: datetime) -> Feature:
    """The latest change to the method is the one a person verified (decision 0013). A newer change isn't."""
    changes = [change for change in context.payment_method_history if change.method_id == proposal.payment_method_id]
    if not changes:
        return Feature(value=False)
    latest = max(changes, key=lambda change: change.changed_at)
    confirmations = [a.adjustment_id for a in context.adjustments
                     if a.kind == 'confirmed_method_change' and a.subject == latest.id]
    return Feature(value=bool(confirmations), evidence=[latest.id, *confirmations] if confirmations else [])


FEATURE_FUNCTIONS = (counterparty_is_new, payment_method_changed_days_ago,
                     amount_ratio_to_vendor_median, bill_mismatch,
                     document_instruction_patterns, bill_not_referenced, duplicate_candidate,
                     payment_method_blocked, payment_method_change_confirmed)


def compute_features(proposal: Proposal, context: Context, now: datetime) -> dict[str, Feature]:
    return {function.__name__: function(proposal, context, now) for function in FEATURE_FUNCTIONS}
