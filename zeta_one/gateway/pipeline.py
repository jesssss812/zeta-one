"""One proposed action, from raw request to evidence record: identity, authorization, risk, policy.

The engine knows each stage only by its protocol in zeta_one.contracts; whoever builds the Engine
picks the implementations. Writing the simulated payment happens after this, not here.
"""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import ValidationError

from zeta_one.contracts import (
    AuthorizationChecker,
    AuthorizationEvidence,
    AuthorizationSource,
    Configuration,
    Context,
    ContextSource,
    EvidenceRecord,
    IdentityEvidence,
    IdentityVerifier,
    InvalidProposal,
    Price,
    Proposal,
    RiskEvidence,
    RiskTier,
    SignedRequest,
    Tier0,
    TierName,
)
from zeta_one.decide import evidence, policy
from zeta_one.risk import assess

LOG = logging.getLogger("zeta_one.decisions")


def _now() -> datetime:
    return datetime.now(UTC)


def new_decision_id() -> str:
    return f"dec_{uuid.uuid4().hex[:16]}"


@dataclass
class Engine:
    verify_identity: IdentityVerifier
    load_authorization: AuthorizationSource
    check_authorization: AuthorizationChecker
    load_context: ContextSource
    tier0: Tier0
    tiers: dict[TierName, RiskTier] = field(default_factory=dict)
    configuration: Configuration = field(default_factory=Configuration)
    prices: dict[str, Price] = field(default_factory=dict)
    clock: Callable[[], datetime] = _now
    new_id: Callable[[], str] = new_decision_id
    engine_version: str | None = None
    seed_version: str | None = None
    # Wraps the risk stage, e.g. to reuse an earlier result for a repeated proposal (decision 0010).
    # Called as assess_risk(engine, proposal, context, now, identity); defaults to run_tiers.
    assess_risk: Callable[["Engine", Proposal, Context, datetime, IdentityEvidence], RiskEvidence] | None = None

    def run_tiers(self, proposal: Proposal, context: Context, now: datetime, identity: IdentityEvidence) -> RiskEvidence:
        return assess.assess(proposal, context, now, self.tier0, self.tiers, self.configuration)

    def evaluate(self, request: SignedRequest) -> tuple[EvidenceRecord, Proposal | None]:
        """Decide one request. Raises InvalidProposal for a malformed body from a verified agent, or one
        naming records that don't exist or don't belong together; nothing is decided for it."""
        now = self.clock()
        latency: dict[str, int] = {}
        started = time.perf_counter()

        identity = self.verify_identity(request, now)
        latency["identity"] = _ms_since(started)
        proposal: Proposal | None = None
        context: Context | None = None
        authorization = AuthorizationEvidence.not_evaluated()
        authorization_doc = None
        risk = RiskEvidence.not_evaluated()

        if identity.result == "verified":
            proposal = _parse(request.body)
            # The context is loaded before authorization, so a proposal naming records that don't
            # exist is refused the same way whatever its amount: a 400 can't tell an agent whether
            # an amount was within its limits (security.md, S8).
            step = time.perf_counter()
            context_error = None
            try:
                context = self.load_context(proposal, identity.business_id, now)
            except InvalidProposal:
                raise
            except Exception as error:  # the data store failed: risk can't run, so the policy challenges
                context_error = f"context: {type(error).__name__}: {error}"
            context_ms = _ms_since(step)
            step = time.perf_counter()
            authorization_doc = self.load_authorization(identity.business_id, identity.claimed_agent_id)
            authorization = self.check_authorization(proposal, authorization_doc, identity, now)
            latency["authorization"] = _ms_since(step)

            if not authorization.violations:
                step = time.perf_counter()
                if context is None:
                    risk = assess.failed_tier0(context_error)
                else:
                    risk = (self.assess_risk or Engine.run_tiers)(self, proposal, context, now, identity)
                latency["risk"] = context_ms + _ms_since(step)
        else:
            # Kept for the reviewer if it parses; an unverified request is never acted on or given context.
            proposal = _parse_or_none(request.body)

        outcome = policy.decide(policy.PolicyInput(identity, authorization, authorization_doc, risk,
                                                   proposal if identity.result == "verified" else None,
                                                   context.payment_history.count > 0 if context else None))
        latency["total"] = _ms_since(started)
        record = evidence.build(
            decision_id=self.new_id(),
            created_at=now,
            configuration=self.configuration,
            identity=identity,
            authorization=authorization,
            authorization_doc=authorization_doc,
            risk=risk,
            outcome=outcome,
            latency_ms=latency,
            prices=self.prices,
            engine_version=self.engine_version,
            seed_version=self.seed_version,
            proposal=proposal,
            context=context,
        )
        LOG.info("%s", log_line(record))
        return record, proposal if identity.result == "verified" else None


def _parse(body: bytes) -> Proposal:
    try:
        return Proposal.model_validate_json(body)
    except ValidationError as error:
        raise InvalidProposal(str(error)) from error


def _parse_or_none(body: bytes) -> Proposal | None:
    try:
        return Proposal.model_validate_json(body)
    except ValidationError:
        return None


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def log_line(record: EvidenceRecord) -> str:
    """One line per decision for the console: what was decided, why, which tiers ran, time and spend.
    Ids and levels only, never request text or credentials. Each tier is named by its model, or
    `rules` for tier 0, so a run shows which models (Jev, Opus, an open-weight model) it reached."""
    tiers = []
    for result in record.risk.tier_results:
        part = result.model or ("rules" if result.tier == "tier0" else result.tier)
        part += f" {result.level}" if result.level else ""
        part += f" error:{result.error.split(':')[0]}" if result.error else ""
        if result.latency_ms is not None and result.tier != "tier0":
            part += f" {result.latency_ms / 1000:.1f}s"
        tiers.append(part)
    total = (record.latency_ms or {}).get("total")
    cost = record.cost.usd if record.cost else 0.0
    return (f"decision {record.decision_id}: {record.decision.upper()} ({', '.join(record.reasons)}) | "
            f"{' > '.join(tiers) or 'no risk tiers'} | {total if total is not None else '-'} ms | ${cost:.4f}")
