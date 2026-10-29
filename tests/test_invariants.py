"""AGENTS.md rule 7 as properties: whatever a model answers, it cannot lower a tier-0 floor, lift an
identity or authorization block, or turn its own failure into an allow."""


from hypothesis import given, strategies as st

from zeta_one.contracts import (
    LEVEL_ORDER,
    Authorization,
    AuthorizationEvidence,
    Configuration,
    Feature,
    IdentityEvidence,
    Proposal,
    Tier0Output,
    TierOutput,
    TierResult,
    Violation,
)
from zeta_one.decide import policy
from zeta_one.risk import escalation
from zeta_one.rho.models import Money

levels = st.sampled_from(["low", "elevated", "high"])
features = st.fixed_dictionaries({
    "counterparty_is_new": st.builds(Feature, value=st.booleans()),
    "payment_method_changed_days_ago": st.builds(Feature, value=st.none() | st.integers(0, 400)),
    "amount_ratio_to_vendor_median": st.builds(Feature, value=st.none() | st.floats(0, 20),
                                               raw_value=st.none() | st.floats(0, 20)),
    "bill_mismatch": st.builds(Feature, value=st.booleans()),
    "document_instruction_patterns": st.builds(Feature, value=st.booleans()),
    "bill_not_referenced": st.builds(Feature, value=st.booleans()),
    "lookalike_counterparty": st.builds(Feature, value=st.booleans()),
    "duplicate_candidate": st.builds(Feature, value=st.booleans()),
})
model_answers = st.lists(
    st.builds(lambda tier, level, error: TierOutput(result=TierResult(tier=tier, level=level, error=error)),
              st.sampled_from(["cheap", "strong"]), levels, st.none() | st.just("timeout")),
    max_size=2,
)
PROPOSAL = Proposal(counterparty_id="cp", payment_method_id="pm", source_account_id="acct",
                    amount=Money(amount=100, currency="USD"))
VERIFIED = IdentityEvidence(result="verified", claimed_agent_id="agent", business_id="biz")
GRANT = Authorization(authorization_id="a", version=1, policy_version="p", business_id="biz", agent_id="agent",
                      granted_by="owner", granted_at="2026-10-01T00:00:00Z")


def _tier0(level, feats) -> Tier0Output:
    return Tier0Output(result=TierResult(tier="tier0", level=level), features=feats)


@given(levels, features, model_answers)
def test_no_model_answer_lowers_the_floor(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    floor = escalation.floor(feats)
    if floor:
        assert LEVEL_ORDER[risk.level] >= LEVEL_ORDER[floor.level]


@given(levels, features, model_answers)
def test_every_lowering_is_recorded_and_flagged_in_reasons(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    lowered = LEVEL_ORDER[risk.level] < LEVEL_ORDER[tier0_level]
    assert (risk.lowered is not None) == lowered
    outcome = policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), GRANT, risk, PROPOSAL))
    assert ("risk:lowered_by_model" in outcome.reasons) == lowered


@given(levels, features, model_answers)
def test_a_failed_model_never_ends_in_allow(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    outcome = policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), GRANT, risk, PROPOSAL))
    if any(answer.result.error for answer in answers):
        assert outcome.decision != "allow"


@given(levels, features, model_answers, st.sampled_from(["unsigned", "unknown_agent", "revoked", "replay"]))
def test_identity_failure_blocks_whatever_risk_says(tier0_level, feats, answers, status):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    identity = IdentityEvidence(result=status)
    outcome = policy.decide(policy.PolicyInput(identity, AuthorizationEvidence(), None, risk, PROPOSAL))
    assert outcome.decision == "block" and outcome.reasons == [f"identity:{status}"]


@given(levels, features, model_answers)
def test_authorization_violation_blocks_whatever_risk_says(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    violation = Violation(field="limits.per_payment", kind="limit")
    authorization = AuthorizationEvidence(violations=[violation])
    outcome = policy.decide(policy.PolicyInput(VERIFIED, authorization, None, risk, PROPOSAL))
    assert outcome.decision == "block" and outcome.reasons == ["authorization:limits.per_payment"]


@given(levels, features, model_answers)
def test_no_authorization_document_blocks_whatever_risk_says(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    outcome = policy.decide(policy.PolicyInput(VERIFIED, AuthorizationEvidence(), None, risk, PROPOSAL))
    assert outcome.decision == "block" and outcome.reasons == ["authorization:authorization"]


@given(levels, features, model_answers)
def test_a_lowering_names_the_model_and_its_soft_signals(tier0_level, feats, answers):
    risk = escalation.merge(_tier0(tier0_level, feats), answers)
    if risk.lowered:
        assert risk.lowered.by in ("cheap", "strong")
        assert risk.lowered.signals == escalation.soft_signals(feats)


def test_a_lowering_the_floor_clamped_is_still_the_models():
    feats = {"payment_method_changed_days_ago": Feature(value=3, evidence=["pmc_1"])}
    strong = TierOutput(result=TierResult(tier="strong", level="low"))
    risk = escalation.merge(_tier0("high", feats), [strong])
    assert (risk.level, risk.level_set_by) == ("elevated", "tier0")
    assert (risk.lowered.from_, risk.lowered.to, risk.lowered.by) == ("high", "elevated", "strong")


def test_an_unrounded_ratio_missing_falls_back_to_the_rounded_one():
    feats = {"amount_ratio_to_vendor_median": Feature(value=9.0, raw_value=None)}
    assert escalation.soft_signals(feats) == ["amount_ratio_to_vendor_median"]


def test_a_method_change_through_day_30_sets_the_floor_and_day_31_does_not():
    at_30 = {"payment_method_changed_days_ago": Feature(value=escalation.RECENT_CHANGE_DAYS)}
    at_31 = {"payment_method_changed_days_ago": Feature(value=escalation.RECENT_CHANGE_DAYS + 1)}
    assert escalation.floor(at_30).level == "elevated"
    assert escalation.floor(at_31) is None
    assert escalation.soft_signals(at_31) == ["payment_method_changed_days_ago"]


def test_clean_tier0_does_not_escalate_and_soft_signal_does():
    clean = {"counterparty_is_new": Feature(value=False), "amount_ratio_to_vendor_median": Feature(value=1.0)}
    soft = {**clean, "amount_ratio_to_vendor_median": Feature(value=5.0)}
    config = Configuration()
    assert not escalation.should_escalate(config, _tier0("low", clean))
    assert escalation.should_escalate(config, _tier0("low", soft))


def test_ratio_rounding_does_not_hide_soft_signal_at_threshold():
    for displayed, raw in ((2.0, 2.004), (0.5, 0.496)):
        feats = {"amount_ratio_to_vendor_median": Feature(value=displayed, raw_value=raw)}
        assert escalation.should_escalate(Configuration(), _tier0("low", feats))
        lowered = escalation.merge(_tier0("elevated", feats), [
            TierOutput(result=TierResult(tier="strong", level="low"))
        ])
        assert lowered.lowered.signals == ["amount_ratio_to_vendor_median"]


def test_a_high_floor_runs_no_model_under_engineered_but_still_runs_jev_and_always():
    """No tier can lower a high floor or go above high (decision 0017)."""
    high = {"bill_mismatch": Feature(value=True), "counterparty_is_new": Feature(value=True)}
    assert escalation.floor(high).level == "high"
    tier0 = _tier0("high", high)
    assert not escalation.should_escalate(Configuration(escalation="engineered"), tier0)
    assert escalation.should_escalate(Configuration(tiers=["tier0", "cheap", "strong"], escalation="jev"), tier0)
    assert escalation.should_escalate(Configuration(escalation="always"), tier0)
    elevated = {"bill_mismatch": Feature(value=True)}
    assert escalation.should_escalate(Configuration(escalation="engineered"), _tier0("elevated", elevated))
