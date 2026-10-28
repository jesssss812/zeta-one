"""Run the risk tiers for one proposal under a configuration.

Nothing here raises: a tier, tier 0 or the escalation rule that fails is recorded as an error on its
tier result, and the policy challenges the payment (decision 0010).
"""

from datetime import datetime

from zeta_one.contracts import (
    Configuration,
    Context,
    Proposal,
    RiskEvidence,
    RiskInput,
    RiskTier,
    Tier0,
    TierName,
    TierOutput,
    TierResult,
)
from zeta_one.risk import escalation


def assess(
    proposal: Proposal,
    context: Context,
    now: datetime,
    tier0: Tier0,
    tiers: dict[TierName, RiskTier],
    configuration: Configuration,
) -> RiskEvidence:
    try:
        first = tier0(proposal, context, now)
    except Exception as error:
        return failed_tier0(f"{type(error).__name__}: {error}")
    later: list[TierOutput] = []
    model_tiers = [name for name in configuration.tiers if name != "tier0"]
    try:
        escalate = bool(model_tiers) and escalation.should_escalate(configuration, first)
    except Exception as error:
        message = f"escalation: {type(error).__name__}: {error}"
        return escalation.merge(first, [TierOutput(result=TierResult(tier=name, error=message)) for name in model_tiers])
    if escalate:
        risk_input = RiskInput(proposal=proposal, context=context, features=first.features, tier0=first.result)
        # Model tiers run in order; after Jev (the cheap tier) the strong tier runs only on Jev's rule.
        for name in model_tiers:
            output = _run(tiers.get(name), name, risk_input)
            later.append(output)
            if name == "cheap" and not escalation.should_escalate_after_cheap(configuration, first, output):
                break
    return escalation.merge(first, later)


def _run(tier: RiskTier | None, name: TierName, risk_input: RiskInput) -> TierOutput:
    if tier is None:
        return TierOutput(result=TierResult(tier=name, error="tier not configured"))
    try:
        return tier.assess(risk_input)
    except Exception as error:  # a tier must not raise; if one does, it counts as a failure
        return TierOutput(result=TierResult(tier=name, error=f"{type(error).__name__}: {error}"))


def failed_tier0(error: str) -> RiskEvidence:
    """Risk evidence when tier 0 (or the context it reads) couldn't run: no level, one error."""
    return RiskEvidence(tiers_run=["tier0"], tier_results=[TierResult(tier="tier0", error=error)])
