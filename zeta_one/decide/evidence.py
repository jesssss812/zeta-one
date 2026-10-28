"""Assemble the evidence record for one decision."""

from datetime import datetime

from zeta_one.contracts import (
    POLICY_VERSION,
    Authorization,
    AuthorizationEvidence,
    Challenge,
    Configuration,
    Context,
    Cost,
    EvidenceRecord,
    Execution,
    IdentityEvidence,
    Proposal,
    RiskEvidence,
)
from zeta_one.decide.policy import Outcome

EXECUTION_STATUS = {"allow": "executed", "challenge": "held", "block": "blocked"}


def build(
    *,
    decision_id: str,
    created_at: datetime,
    configuration: Configuration,
    identity: IdentityEvidence,
    authorization: AuthorizationEvidence,
    authorization_doc: Authorization | None,
    risk: RiskEvidence,
    outcome: Outcome,
    latency_ms: dict[str, int] | None,
    prices: dict[str, tuple[float, float]] | None = None,
    engine_version: str | None = None,
    seed_version: str | None = None,
    proposal: Proposal | None = None,
    context: Context | None = None,
) -> EvidenceRecord:
    challenge = None
    if outcome.challenge_type:
        grantor = authorization_doc.granted_by if authorization_doc else "the business owner"
        challenge = Challenge(
            type=outcome.challenge_type,
            routed_to=f"authorization grantor ({grantor})",
            user_sees=outcome.user_sees or "One approve / reject prompt.",
        )
    return EvidenceRecord(
        decision_id=decision_id,
        created_at=created_at,
        policy_version=POLICY_VERSION,
        engine_version=engine_version,
        seed_version=seed_version,
        configuration=configuration,
        decision=outcome.decision,
        reasons=outcome.reasons,
        challenge=challenge,
        friction_rung=outcome.friction_rung,
        identity=identity,
        authorization=authorization,
        risk=risk,
        execution=Execution(status=EXECUTION_STATUS[outcome.decision]),
        cost=_cost(risk, prices or {}),
        latency_ms=latency_ms,
        # Copies, so later changes to the objects the stages hold can't rewrite the record.
        proposal=proposal.model_copy(deep=True) if proposal else None,
        context=context.model_copy(deep=True) if context else None,
    )


# Anthropic bills cache reads at a tenth of the input price and five-minute cache writes at 1.25x.
CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25


def _cost(risk: RiskEvidence, prices: dict[str, tuple[float, float]]) -> Cost:
    """Cost from reported token usage at per-million-token (input, output) prices, cache included."""
    cost = Cost()
    for result in risk.tier_results:
        if not result.usage:
            continue
        usage = result.usage
        cost.input_tokens += usage.input_tokens
        cost.output_tokens += usage.output_tokens
        cost.cache_read_input_tokens += usage.cache_read_input_tokens
        cost.cache_creation_input_tokens += usage.cache_creation_input_tokens
        if result.model not in prices:
            if result.model and result.model not in cost.unpriced_models:
                cost.unpriced_models.append(result.model)
            continue
        input_price, output_price = prices[result.model]
        input_equivalent = (
            usage.input_tokens
            + usage.cache_read_input_tokens * CACHE_READ_MULTIPLIER
            + usage.cache_creation_input_tokens * CACHE_WRITE_MULTIPLIER
        )
        cost.usd += (input_equivalent * input_price + usage.output_tokens * output_price) / 1e6
        cost.prices_used[result.model] = {
            "input_per_mtok": input_price,
            "output_per_mtok": output_price,
            "cache_read_multiplier": CACHE_READ_MULTIPLIER,
            "cache_write_multiplier": CACHE_WRITE_MULTIPLIER,
        }
    return cost
