"""Ordered deterministic checks; every failed constraint contributes one violation."""
from datetime import timedelta
from zeta_one.contracts import AuthorizationChecker, AuthorizationEvidence, Violation


def _violation(field, kind, limit, observed):
    return Violation(field=field, kind=kind, limit=limit, observed=observed)

def check_status(p, a, i, now, spend):
    if a.status != 'active' or a.revoked_at is not None:
        return _violation('status', 'scope', 'active', a.status)

def check_business_id(p, a, i, now, spend):
    if a.business_id != i.business_id:
        return _violation('business_id', 'scope', a.business_id, i.business_id)

def check_agent_id(p, a, i, now, spend):
    if a.agent_id != i.claimed_agent_id:
        return _violation('agent_id', 'scope', a.agent_id, i.claimed_agent_id)

def check_actions(p, a, i, now, spend):
    if 'propose_payment' not in a.actions:
        return _violation('actions', 'scope', a.actions, 'propose_payment')

def check_counterparties(p, a, i, now, spend):
    scope = a.counterparties
    if ((scope.mode == 'allowlist' and p.counterparty_id not in scope.ids) or
        (scope.mode == 'denylist' and p.counterparty_id in scope.ids)):
        return _violation('counterparties', 'scope', scope.model_dump(), p.counterparty_id)

def check_expires_at(p, a, i, now, spend):
    if a.expires_at is not None and (a.expires_at.utcoffset() is None or now >= a.expires_at):
        return _violation('expires_at', 'limit', a.expires_at.isoformat(), now.isoformat())

def check_per_payment(p, a, i, now, spend):
    cap = a.limits.per_payment
    if cap and (p.amount.currency != cap.currency or p.amount.amount > cap.amount):
        return _violation('limits.per_payment', 'limit', cap.model_dump(), p.amount.model_dump())

def check_rolling(p, a, i, now, spend):
    rolling = a.limits.rolling
    if rolling is None:
        return None
    cap = rolling.amount
    if p.amount.currency != cap.currency:
        return _violation('limits.rolling', 'limit', cap.model_dump(), p.amount.model_dump())
    total = spend(a.agent_id, now - timedelta(days=rolling.window_days), cap.currency) + p.amount.amount
    if total > cap.amount:
        return _violation('limits.rolling', 'limit', cap.model_dump(), {'amount': total, 'currency': cap.currency})

CHECKS = (check_status, check_business_id, check_agent_id, check_actions, check_counterparties,
          check_expires_at, check_per_payment, check_rolling)

def checker(spend) -> AuthorizationChecker:
    def check(proposal, authorization, identity, now):
        if authorization is None:
            return AuthorizationEvidence(violations=[_violation('authorization', 'scope', 'active', None)])
        violations = [violation for function in CHECKS
                      if (violation := function(proposal, authorization, identity, now, spend)) is not None]
        return AuthorizationEvidence(authorization_id=authorization.authorization_id, version=authorization.version,
                                     snapshot=authorization.model_dump(mode='json'), violations=violations)
    return check
