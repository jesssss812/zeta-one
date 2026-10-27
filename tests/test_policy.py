"""The policy table, row by row."""

from datetime import UTC, datetime

import pytest

from zeta_one.contracts import (
    Authorization,
    AuthorizationEvidence,
    Feature,
    Floor,
    IdentityEvidence,
    Proposal,
    RiskEvidence,
    Signal,
    TierResult,
)
from zeta_one.decide import policy
from zeta_one.rho.models import Money

VERIFIED = IdentityEvidence(result="verified", claimed_agent_id="agent", business_id="biz")


def _auth(**fields) -> Authorization:
    return Authorization(authorization_id="a", version=1, policy_version="p", business_id="biz", agent_id="agent",
                         granted_by="owner", granted_at=datetime(2026, 10, 1, tzinfo=UTC), **fields)


def _proposal(amount=100) -> Proposal:
    return Proposal(counterparty_id="cp", payment_method_id="pm", source_account_id="acct",
                    amount=Money(amount=amount, currency="USD"))


def _decide(risk, auth=None, amount=100):
    return policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), auth or _auth(), risk, _proposal(amount)))


@pytest.mark.parametrize("risk, decision, reason", [
    (RiskEvidence(level="high", floor=Floor(level="high", flags=["bill_mismatch"])), "block",
     "risk:high_with_redirect_pattern"),
    (RiskEvidence(level="high", signals=[Signal(name="injection_detected", severity="high", source="strong")]),
     "block", "risk:high_with_redirect_pattern"),
    (RiskEvidence(level="low", tier_results=[TierResult(tier="strong", error="refusal")]), "challenge",
     "risk:model_unavailable"),
    (RiskEvidence(level="high"), "challenge", "risk:high"),
    (RiskEvidence(level="low", features={"counterparty_is_new": Feature(value=True)}), "challenge",
     "authorization:new_counterparty_requires_approval"),
    (RiskEvidence(level="elevated"), "challenge", "risk:elevated"),
    (RiskEvidence(level="low"), "allow", "clean"),
])
def test_rows(risk, decision, reason):
    outcome = _decide(risk)
    assert (outcome.decision, outcome.reasons[0]) == (decision, reason)
    assert outcome.friction_rung == {"allow": 0, "challenge": 2, "block": 5}[decision]


def test_new_counterparty_allowed_by_authorization_passes():
    risk = RiskEvidence(level="low", features={"counterparty_is_new": Feature(value=True)})
    assert _decide(risk, _auth(allow_new_counterparties=True)).decision == "allow"


def test_approval_threshold_is_inclusive_and_currency_strict():
    auth = _auth(allow_new_counterparties=True, human_approval_above=Money(amount=1000, currency="USD"))
    assert _decide(RiskEvidence(level="low"), auth, amount=1000).decision == "allow"
    assert _decide(RiskEvidence(level="low"), auth, amount=1001).reasons == ["authorization:human_approval_threshold"]
    eur = Proposal(counterparty_id="cp", payment_method_id="pm", source_account_id="acct",
                   amount=Money(amount=10, currency="EUR"))
    outcome = policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), auth, RiskEvidence(level="low"), eur))
    assert outcome.reasons == ["authorization:human_approval_threshold"]
