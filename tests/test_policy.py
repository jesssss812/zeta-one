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


def _decide(risk, auth=None, amount=100, paid_before=True):
    return policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), auth or _auth(), risk, _proposal(amount),
                                            paid_before))


@pytest.mark.parametrize("risk, decision, reason", [
    (RiskEvidence(level="high", floor=Floor(level="high", flags=["bill_mismatch"])), "block",
     "risk:high_with_redirect_pattern"),
    (RiskEvidence(level="high", signals=[Signal(name="injection_detected", severity="high", source="strong")]),
     "block", "risk:high_with_redirect_pattern"),
    (RiskEvidence(level="low", tier_results=[TierResult(tier="strong", error="refusal")]), "challenge",
     "risk:model_unavailable"),
    (RiskEvidence(level="high"), "challenge", "risk:high"),
    (RiskEvidence(level="elevated"), "challenge", "risk:elevated"),
    (RiskEvidence(level="low"), "allow", "clean"),
])
def test_rows(risk, decision, reason):
    outcome = _decide(risk)
    assert (outcome.decision, outcome.reasons[0]) == (decision, reason)
    assert outcome.friction_rung == {"allow": 0, "challenge": 2, "block": 5}[decision]


@pytest.mark.parametrize("paid_before", [False, None])
def test_a_payee_never_paid_needs_approval_unless_the_grant_allows_new_payees(paid_before):
    outcome = _decide(RiskEvidence(level="low"), paid_before=paid_before)
    assert (outcome.decision, outcome.reasons) == ("challenge", ["authorization:new_counterparty_requires_approval"])
    assert _decide(RiskEvidence(level="low"), _auth(allow_new_counterparties=True), paid_before=paid_before).decision == "allow"


def test_a_young_payee_that_has_been_paid_is_not_an_authorization_question():
    risk = RiskEvidence(level="low", features={"counterparty_is_new": Feature(value=True)})
    assert _decide(risk).decision == "allow"


def test_approval_threshold_is_inclusive_and_currency_strict():
    auth = _auth(allow_new_counterparties=True, human_approval_above=Money(amount=1000, currency="USD"))
    assert _decide(RiskEvidence(level="low"), auth, amount=1000).decision == "allow"
    assert _decide(RiskEvidence(level="low"), auth, amount=1001).reasons == ["authorization:human_approval_threshold"]
    eur = Proposal(counterparty_id="cp", payment_method_id="pm", source_account_id="acct",
                   amount=Money(amount=10, currency="EUR"))
    outcome = policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), auth, RiskEvidence(level="low"), eur, True))
    assert outcome.reasons == ["authorization:human_approval_threshold"]


def test_a_tier0_failure_is_a_challenge_not_an_allow():
    risk = RiskEvidence(tiers_run=["tier0"], tier_results=[TierResult(tier="tier0", error="boom")])
    outcome = _decide(risk)
    assert (outcome.decision, outcome.reasons) == ("challenge", ["risk:tier0_unavailable"])


def test_the_repeat_limit_is_a_challenge():
    outcome = _decide(RiskEvidence(level="low", repeat_limit_reached=True))
    assert (outcome.decision, outcome.reasons) == ("challenge", ["risk:repeat_limit"])
