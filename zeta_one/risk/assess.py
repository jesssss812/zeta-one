"""Run the risk tiers for one proposal under a configuration."""

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
    first = tier0(proposal, context, now)
    later: list[TierOutput] = []
    model_tiers = [name for name in configuration.tiers if name != "tier0"]
    if model_tiers and escalation.should_escalate(configuration, first):
        risk_input = RiskInput(proposal=proposal, context=context, features=first.features, tier0=first.result)
        # One model tier in the first version; the Jev rule decides between cheap and strong later.
        for name in model_tiers:
            later.append(_run(tiers.get(name), name, risk_input))
    return escalation.merge(first, later)


def _run(tier: RiskTier | None, name: TierName, risk_input: RiskInput) -> TierOutput:
    if tier is None:
        return TierOutput(result=TierResult(tier=name, error="tier not configured"))
    try:
        return tier.assess(risk_input)
    except Exception as error:  # a tier must not raise; if one does, it counts as a failure
        return TierOutput(result=TierResult(tier=name, error=f"{type(error).__name__}: {error}"))
