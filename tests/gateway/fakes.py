"""Fake stages for gateway tests: just enough identity, authorization, context and risk to drive it.

Two counterparties, each with its fixture's context: cp_0007 (vendor_payment_method_changed), whose
recent method change makes tier 0 elevated, and cp_0012 (routine_bill_payment), which is clean.
"""

import time
from datetime import UTC, datetime, timedelta

from zeta_one.contracts import (
    Authorization,
    AuthorizationEvidence,
    Configuration,
    Context,
    Feature,
    IdentityEvidence,
    InvalidProposal,
    Money,
    PaymentMethodView,
    Proposal,
    RiskInput,
    RollingLimit,
    SignedRequest,
    Tier0Output,
    TierOutput,
    Violation,
)
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.wiring import Stages

NOW = datetime(2026, 10, 27, 22, 0, tzinfo=UTC)
AGENT = "agent_ap_assistant_01"
BUSINESS = "biz_seed_01"
HELD = load_fixture("vendor_payment_method_changed")
ROUTINE = load_fixture("routine_bill_payment")


def agent_headers(agent: str = AGENT, signature: str = "valid") -> dict[str, str]:
    return {"Zeta-Agent-Id": agent, "Zeta-Agent-Signature": signature}


class FakeWorld:
    def __init__(self):
        self.agents = {AGENT: "active"}
        self.authorization = Authorization.model_validate(HELD.decision_record.authorization.snapshot)
        self.contexts: dict[str, Context] = {
            scenario.context.counterparty.id: scenario.context.model_copy(deep=True) for scenario in (HELD, ROUTINE)
        }
        self.strong_calls = 0
        self.tier0_calls = 0
        self.delay = 0.0  # seconds each risk stage takes, to widen race windows in tests
        self.extra_features: dict[str, Feature] = {}

    # --- stages ---

    def verify_identity(self, request: SignedRequest, now: datetime) -> IdentityEvidence:
        headers = {name.lower(): value for name, value in request.headers.items()}
        agent = headers.get("zeta-agent-id")
        if agent is None:
            return IdentityEvidence(result="unsigned")
        status = self.agents.get(agent)
        if status is None:
            return IdentityEvidence(result="unknown_agent", claimed_agent_id=agent)
        if status != "active":
            return IdentityEvidence(result="revoked", claimed_agent_id=agent)
        if headers.get("zeta-agent-signature") != "valid":
            return IdentityEvidence(result="invalid_signature", claimed_agent_id=agent)
        return IdentityEvidence(result="verified", claimed_agent_id=agent, business_id=BUSINESS)

    def load_authorization(self, business_id: str, agent_id: str) -> Authorization | None:
        a = self.authorization
        return a if a and (a.business_id, a.agent_id) == (business_id, agent_id) else None

    def make_checker(self, spend):
        def check(proposal, authorization, identity, now) -> AuthorizationEvidence:
            if authorization is None:
                return AuthorizationEvidence(violations=[Violation(field="authorization", kind="scope")])
            violations = []
            if authorization.status != "active":
                violations.append(Violation(field="status", kind="scope", observed=authorization.status))
            if authorization.expires_at and now > authorization.expires_at:
                violations.append(Violation(field="expires_at", kind="scope"))
            cap = authorization.limits.per_payment
            if cap and proposal.amount.amount > cap.amount:
                violations.append(Violation(field="limits.per_payment", kind="limit"))
            rolling = authorization.limits.rolling
            if rolling:
                spent = spend(identity.claimed_agent_id, now - timedelta(days=rolling.window_days), "USD")
                if spent + proposal.amount.amount > rolling.amount.amount:
                    violations.append(Violation(field="limits.rolling", kind="limit", observed=spent))
            return AuthorizationEvidence(
                authorization_id=authorization.authorization_id,
                version=authorization.version,
                violations=violations,
                snapshot=authorization.model_dump(mode="json"),
            )

        return check

    def load_context(self, proposal: Proposal, business_id: str, now: datetime) -> Context:
        context = self.contexts.get(proposal.counterparty_id)
        if context is None:
            raise InvalidProposal(f"unknown counterparty {proposal.counterparty_id}")
        if proposal.payment_method_id not in {m.id for m in context.counterparty.payment_methods}:
            raise InvalidProposal("payment method not on counterparty")
        return context.model_copy(deep=True)

    def tier0(self, proposal: Proposal, context: Context, now: datetime) -> Tier0Output:
        self.tier0_calls += 1
        time.sleep(self.delay)
        source = HELD if context.payment_method_history else ROUTINE
        risk = source.decision_record.risk
        return Tier0Output(
            result=next(r for r in risk.tier_results if r.tier == "tier0"),
            signals=[s for s in risk.signals if s.source == "tier0"],
            features={**risk.features, **self.extra_features},
        )

    class _Strong:
        name = "strong"

        def __init__(self, world):
            self.world = world

        def assess(self, risk_input: RiskInput) -> TierOutput:
            self.world.strong_calls += 1
            time.sleep(self.world.delay)
            risk = HELD.decision_record.risk
            return TierOutput(
                result=next(r for r in risk.tier_results if r.tier == "strong"),
                signals=[s for s in risk.signals if s.source == "strong"],
            )

    def agent_status(self, agent_id: str) -> str | None:
        return self.agents.get(agent_id)

    # --- changes to the world ---

    def change_payment_method(self, counterparty_id: str = "cp_0007") -> None:
        counterparty = self.contexts[counterparty_id].counterparty
        counterparty.payment_methods.append(PaymentMethodView(id="pm_new", type="ach", is_default=False))

    def set_rolling_limit(self, amount: int, window_days: int = 30) -> None:
        rolling = RollingLimit(window_days=window_days, amount=Money(amount=amount, currency="USD"))
        limits = self.authorization.limits.model_copy(update={"rolling": rolling})
        self.authorization = self.authorization.model_copy(update={"limits": limits})

    def stages(self) -> Stages:
        return Stages(
            verify_identity=self.verify_identity,
            load_authorization=self.load_authorization,
            make_checker=self.make_checker,
            load_context=self.load_context,
            tier0=self.tier0,
            tiers={"strong": self._Strong(self)},
            agent_status=self.agent_status,
            configuration=Configuration(tiers=["tier0", "strong"], escalation="engineered"),
        )


def held_proposal(**changes) -> Proposal:
    return HELD.proposal.model_copy(update=changes)


def routine_proposal(**changes) -> Proposal:
    return ROUTINE.proposal.model_copy(update=changes)
