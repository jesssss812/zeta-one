"""Deterministic risk banding; the escalation module alone owns the enforced floor."""
from datetime import datetime

from zeta_one.contracts import Context, Proposal, Signal, Tier0Output, TierResult
from zeta_one.risk.features import compute_features


class Tier0:
    def __call__(self, proposal: Proposal, context: Context, now: datetime) -> Tier0Output:
        features = compute_features(proposal, context, now)
        changed = features['payment_method_changed_days_ago'].value
        new_or_changed = features['counterparty_is_new'].value or (changed is not None and changed <= 30)
        signals = []
        for name in ('bill_mismatch', 'bill_not_referenced', 'document_instruction_patterns',
                     'duplicate_candidate', 'counterparty_is_new', 'payment_method_changed_days_ago',
                     'amount_ratio_to_vendor_median'):
            feature = features[name]
            severity = 'elevated'
            active = feature.value is True
            if name in ('bill_mismatch', 'bill_not_referenced') and new_or_changed:
                severity = 'high'
            if name == 'payment_method_changed_days_ago':
                active = changed is not None
            if name == 'amount_ratio_to_vendor_median':
                raw = getattr(feature, 'raw_value', None)
                ratio = raw if raw is not None else feature.value
                active = ratio is not None and not (0.5 <= ratio <= 2.0)
            if active:
                signals.append(Signal(name='payment_method_changed' if name == 'payment_method_changed_days_ago' else name,
                                      severity=severity, evidence=feature.evidence, source='tier0'))
        level = 'high' if any(s.severity == 'high' for s in signals) else 'elevated' if signals else 'low'
        return Tier0Output(features=features, signals=signals,
                           result=TierResult(tier='tier0', level=level, signals=[s.name for s in signals]))
