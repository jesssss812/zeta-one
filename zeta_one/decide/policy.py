"""The policy: identity, then authorization, then an ordered table of risk rows; first match wins.

A verified agent with no authorization document is blocked even if the checker reported nothing.

The table is data under contracts.POLICY_VERSION. A new rung is a new row (decision 0008). Rows that read
risk read the merged level, which no model can lower below the tier-0 floor (decision 0007).
"""

from collections.abc import Callable
from dataclasses import dataclass

from zeta_one.contracts import (
    LEVEL_ORDER,
    Authorization,
    AuthorizationEvidence,
    ChallengeType,
    Decision,
    IdentityEvidence,
    Proposal,
    RiskEvidence,
)

FRICTION_RUNG = {"allow": 0, ChallengeType.CONFIRM: 2, "block": 5}
REDIRECT_PATTERNS = ("bill_mismatch", "document_instruction_patterns", "injection_detected")


@dataclass(frozen=True)
class PolicyInput:
    identity: IdentityEvidence
    authorization: AuthorizationEvidence
    authorization_doc: Authorization | None
    risk: RiskEvidence
    proposal: Proposal | None


@dataclass(frozen=True)
class Outcome:
    decision: Decision
    reasons: list[str]
    challenge_type: ChallengeType | None
    friction_rung: int
    user_sees: str | None = None


@dataclass(frozen=True)
class Row:
    condition: Callable[[PolicyInput], bool]
    decision: Decision
    challenge_type: ChallengeType | None
    reason: str
    user_sees: str | None = None


def _level_at_least(level: str) -> Callable[[PolicyInput], bool]:
    return lambda p: p.risk.level is not None and LEVEL_ORDER[p.risk.level] >= LEVEL_ORDER[level]


def _redirect_pattern(p: PolicyInput) -> bool:
    return any(p.risk.has_signal(name) or (p.risk.floor and name in p.risk.floor.flags) for name in REDIRECT_PATTERNS)


def _new_counterparty_needs_approval(p: PolicyInput) -> bool:
    feature = p.risk.features.get("counterparty_is_new")
    allowed = p.authorization_doc.allow_new_counterparties if p.authorization_doc else False
    return bool(feature and feature.value is True) and not allowed


def _above_approval_threshold(p: PolicyInput) -> bool:
    threshold = p.authorization_doc.human_approval_above if p.authorization_doc else None
    if threshold is None or p.proposal is None:
        return False
    amount = p.proposal.amount
    return amount.currency != threshold.currency or amount.amount > threshold.amount


ROWS: list[Row] = [
    Row(lambda p: _level_at_least("high")(p) and _redirect_pattern(p), "block", None, "risk:high_with_redirect_pattern"),
    Row(lambda p: p.risk.tier0_failed(), "challenge", ChallengeType.CONFIRM, "risk:tier0_unavailable",
        "The risk check could not complete; confirm this payment before it is sent."),
    Row(lambda p: p.risk.model_failed(), "challenge", ChallengeType.CONFIRM, "risk:model_unavailable",
        "The risk check could not complete; confirm this payment before it is sent."),
    Row(lambda p: p.risk.repeat_limit_reached, "challenge", ChallengeType.CONFIRM, "risk:repeat_limit",
        "The agent has proposed several variations of this payment; confirm it before it is sent."),
    Row(_level_at_least("high"), "challenge", ChallengeType.CONFIRM, "risk:high",
        "This payment carries high risk; confirm it before it is sent."),
    Row(_new_counterparty_needs_approval, "challenge", ChallengeType.CONFIRM,
        "authorization:new_counterparty_requires_approval", "The agent wants to pay a new payee; approve or reject."),
    Row(_above_approval_threshold, "challenge", ChallengeType.CONFIRM, "authorization:human_approval_threshold",
        "This payment is above the amount that needs your approval."),
    Row(_level_at_least("elevated"), "challenge", ChallengeType.CONFIRM, "risk:elevated",
        "Something about this payment needs a second look; confirm before it is sent."),
    Row(lambda p: True, "allow", None, "clean"),
]


def decide(p: PolicyInput) -> Outcome:
    if p.identity.result != "verified":
        return Outcome("block", [f"identity:{p.identity.result}"], None, FRICTION_RUNG["block"])
    if p.authorization.violations:
        reasons = [f"authorization:{violation.field}" for violation in p.authorization.violations]
        return Outcome("block", reasons, None, FRICTION_RUNG["block"])
    if p.authorization_doc is None:
        # No grant at all blocks here too, whatever the checker returned: scope, expiry and
        # revocation can't rest on a checker remembering to report a missing grant.
        return Outcome("block", ["authorization:authorization"], None, FRICTION_RUNG["block"])
    for row in ROWS:
        if row.condition(p):
            reasons = [row.reason]
            if p.risk.lowered:
                reasons.append("risk:lowered_by_model")
            rung = FRICTION_RUNG[row.challenge_type] if row.challenge_type else FRICTION_RUNG[row.decision]
            return Outcome(row.decision, reasons, row.challenge_type, rung, row.user_sees)
    raise AssertionError("the last row always matches")

