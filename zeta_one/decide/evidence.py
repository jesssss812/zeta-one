"""Assemble the evidence record for one decision."""

from datetime import datetime

from zeta_one.contracts import (
    POLICY_VERSION,
    Authorization,
    AuthorizationEvidence,
    Challenge,
    Configuration,
    Cost,
    EvidenceRecord,
    Execution,
    IdentityEvidence,
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
    )


def _cost(risk: RiskEvidence, prices: dict[str, tuple[float, float]]) -> Cost:
    """Cost from reported token usage at per-million-token (input, output) prices."""
    cost = Cost()
    for result in risk.tier_results:
        if not result.usage:
            continue
        cost.input_tokens += result.usage.input_tokens
        cost.output_tokens += result.usage.output_tokens
        if result.model in prices:
            input_price, output_price = prices[result.model]
            cost.usd += (result.usage.input_tokens * input_price + result.usage.output_tokens * output_price) / 1e6
            cost.prices_used[result.model] = {"input_per_mtok": input_price, "output_per_mtok": output_price}
    return cost
