"""Stand-in stages that replay a fixture's recorded stage results through the real merge and policy.

They let every module, the site and the evaluation run end to end before the real stages exist, and
they pin the contract: replaying a fixture must reproduce its decision. Each real stage replaces its
stand-in here one at a time.
"""

from datetime import datetime

from zeta_one.contracts import (
    Authorization,
    AuthorizationEvidence,
    Configuration,
    Context,
    IdentityEvidence,
    Proposal,
    RiskInput,
    ScenarioResult,
    SignedRequest,
    Tier0Output,
    TierName,
    TierOutput,
)
from zeta_one.gateway.pipeline import Engine


class _ReplayTier:
    def __init__(self, name: TierName, scenario: ScenarioResult):
        self.name = name
        self._scenario = scenario

    def assess(self, risk_input: RiskInput) -> TierOutput:
        risk = self._scenario.decision_record.risk
        result = next(r for r in risk.tier_results if r.tier == self.name)
        signals = [s for s in risk.signals if s.source == self.name]
        return TierOutput(result=result, signals=signals, rationale=risk.model_rationale)


def replay_engine(scenario: ScenarioResult) -> Engine:
    record = scenario.decision_record
    snapshot = record.authorization.snapshot

    def verify_identity(request: SignedRequest, now: datetime) -> IdentityEvidence:
        return record.identity

    def load_authorization(business_id: str, agent_id: str) -> Authorization | None:
        return Authorization.model_validate(snapshot) if snapshot else None

    def check_authorization(proposal, authorization, identity, now) -> AuthorizationEvidence:
        return record.authorization

    def load_context(proposal: Proposal, business_id: str, now: datetime) -> Context:
        return scenario.context

    def tier0(proposal: Proposal, context: Context, now: datetime) -> Tier0Output:
        risk = record.risk
        result = next(r for r in risk.tier_results if r.tier == "tier0")
        signals = [s for s in risk.signals if s.source == "tier0"]
        return Tier0Output(result=result, signals=signals, features=risk.features)

    recorded_tiers = {r.tier for r in record.risk.tier_results} - {"tier0"}
    return Engine(
        verify_identity=verify_identity,
        load_authorization=load_authorization,
        check_authorization=check_authorization,
        load_context=load_context,
        tier0=tier0,
        tiers={name: _ReplayTier(name, scenario) for name in recorded_tiers},
        configuration=Configuration(tiers=["tier0", "strong"], escalation="engineered"),
        clock=lambda: record.created_at,
        new_id=lambda: record.decision_id,
    )


def request_for(scenario: ScenarioResult) -> SignedRequest:
    identity = scenario.decision_record.identity
    return SignedRequest(
        method="POST",
        path="/v1/actions/propose_payment",
        headers={"Zeta-Agent-Id": identity.claimed_agent_id or ""},
        body=scenario.proposal.model_dump_json().encode(),
    )
