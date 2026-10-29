"""When the next risk tier runs, and how tier results combine into one level (decisions 0007, 0010).

`merge` is the only place a risk level is combined. Tier-0 hard flags set a floor no later tier can
lower; above the floor the latest tier that succeeded decides, and a lowering of soft signals is
recorded with the model tier that lowered it.
"""

from zeta_one.contracts import (
    LEVEL_ORDER,
    Configuration,
    Feature,
    Floor,
    Level,
    Lowered,
    RiskEvidence,
    Tier0Output,
    TierOutput,
    max_level,
)

RECENT_CHANGE_DAYS = 30
TYPICAL_AMOUNT_RATIO = (0.5, 2.0)


def _true(features: dict[str, Feature], name: str) -> bool:
    feature = features.get(name)
    return bool(feature and feature.value is True)


def _changed_days_ago(features: dict[str, Feature]) -> int | float | None:
    feature = features.get("payment_method_changed_days_ago")
    return feature.value if feature else None


def payee_new_or_changed(features: dict[str, Feature]) -> bool:
    days = _changed_days_ago(features)
    return _true(features, "counterparty_is_new") or (days is not None and days <= RECENT_CHANGE_DAYS)


def floor(features: dict[str, Feature]) -> Floor | None:
    """The level tier 0's hard flags guarantee, and the flags that set it."""
    level: Level | None = None
    flags: list[str] = []

    def raise_to(new: Level, flag: str) -> None:
        nonlocal level
        level = new if level is None else max_level(level, new)
        flags.append(flag)

    for flag in ("bill_mismatch", "bill_not_referenced"):
        if _true(features, flag):
            raise_to("high" if payee_new_or_changed(features) else "elevated", flag)
    if _true(features, "document_instruction_patterns"):
        raise_to("elevated", "document_instruction_patterns")
    days = _changed_days_ago(features)
    # A recent change is a floor unless a person verified that very change (decision 0013).
    if days is not None and days <= RECENT_CHANGE_DAYS and not _true(features, "payment_method_change_confirmed"):
        raise_to("elevated", "payment_method_changed_days_ago")
    for flag in ("lookalike_counterparty", "duplicate_candidate"):
        if _true(features, flag):
            raise_to("elevated", flag)
    if _true(features, "payment_method_blocked"):
        raise_to("high", "payment_method_blocked")
    return Floor(level=level, flags=flags) if level else None


ADJUSTMENT_FEATURES = ("payment_method_blocked", "payment_method_change_confirmed")


def adjustments_used(features: dict[str, Feature]) -> list[str]:
    """Ids of the risk adjustments that changed this assessment, from the features that read them."""
    return [ref for name in ADJUSTMENT_FEATURES if _true(features, name)
            for ref in features[name].evidence if ref.startswith("adj_")]


def soft_signals(features: dict[str, Feature]) -> list[str]:
    """Tier-0 findings that prompt a closer look but set no floor, so a model may clear them."""
    found = []
    if _true(features, "counterparty_is_new"):
        found.append("counterparty_is_new")
    ratio = features.get("amount_ratio_to_vendor_median")
    ratio_value = None
    if ratio:
        raw = getattr(ratio, "raw_value", None)
        ratio_value = raw if raw is not None else ratio.value
    if ratio_value is not None and not (TYPICAL_AMOUNT_RATIO[0] <= ratio_value <= TYPICAL_AMOUNT_RATIO[1]):
        found.append("amount_ratio_to_vendor_median")
    days = _changed_days_ago(features)
    confirmed = _true(features, "payment_method_change_confirmed")
    if days is not None and (days > RECENT_CHANGE_DAYS or confirmed):
        found.append("payment_method_changed_days_ago")
    return found


def should_escalate(configuration: Configuration, tier0: Tier0Output) -> bool:
    """Whether the first model tier runs after tier 0. Under the engineered rule it never runs on a
    high floor (decision 0017): no tier can lower a floor or go above high. Under the Jev rule Jev is
    the first tier, and it runs when tier 0 isn't clean; the rule after Jev skips the strong tier on a
    high floor (decision 0016)."""
    if configuration.escalation == "none":
        return False
    if configuration.escalation == "always":
        return True
    if configuration.escalation in ("engineered", "jev"):
        hard = floor(tier0.features)
        if configuration.escalation == "engineered" and hard and hard.level == "high":
            return False
        return tier0.result.level in ("elevated", "high") or bool(soft_signals(tier0.features))
    raise ValueError(f"unknown escalation rule {configuration.escalation!r}")


def should_escalate_after_cheap(configuration: Configuration, tier0: Tier0Output, cheap: TierOutput) -> bool:
    """Whether the strong tier runs after Jev (decisions 0007, 0016): Jev isn't confident enough in its
    level, or says elevated, or is more than one band from tier 0, or found something it isn't sure
    of, or a finding raised its level above its own answer. Never when tier 0's floor is already high:
    no tier can lower a floor or go above high, so the strong tier could not change the level. A Jev
    that failed escalates nothing: the policy challenges a failed model tier whatever comes after."""
    if configuration.escalation == "always":
        return True
    result = cheap.result
    if result.error or result.level is None:
        return False
    hard = floor(tier0.features)
    if hard and hard.level == "high":
        return False
    tier0_level = tier0.result.level or "low"
    unsure_findings = any(
        probability < configuration.jev_min_finding_confidence
        for name, probability in (getattr(result, "probabilities", None) or {}).items()
        if name != "risk_level" and name in _finding_names(result)
    )
    answered = getattr(result, "answered_level", None)
    return (
        (result.confidence is None or result.confidence < configuration.jev_min_confidence)
        or result.level == "elevated"
        or abs(LEVEL_ORDER[result.level] - LEVEL_ORDER[tier0_level]) > 1
        or unsure_findings
        or (answered is not None and answered != result.level)
    )


def _finding_names(result) -> set[str]:
    """The questions whose answer was a finding: the signals Jev raised, by the question they came from."""
    named = set(result.signals)
    if "proposal_mismatches_documents" in named:
        named.add("proposal_matches_documents")
    return named


def merge(tier0: Tier0Output, later: list[TierOutput]) -> RiskEvidence:
    """Combine tier results into the risk evidence. Failed tiers are recorded and don't set a level."""
    base: Level = tier0.result.level or "low"
    hard = floor(tier0.features)

    succeeded = [output for output in later if not output.result.error and output.result.level]
    level: Level = succeeded[-1].result.level if succeeded else base
    level_set_by = succeeded[-1].result.tier if succeeded else "tier0"
    if hard and LEVEL_ORDER[level] < LEVEL_ORDER[hard.level]:
        level, level_set_by = hard.level, "tier0"

    lowered = None
    if succeeded and LEVEL_ORDER[level] < LEVEL_ORDER[base]:
        # Only a model lowers; when the floor clamps it back up, tier 0 set the level but the
        # lowering is still the model's.
        lowered = Lowered(from_=base, to=level, by=succeeded[-1].result.tier, signals=soft_signals(tier0.features))

    return RiskEvidence(
        level=level,
        level_set_by=level_set_by,
        floor=hard,
        tiers_run=["tier0", *(output.result.tier for output in later)],
        features=tier0.features,
        tier_results=[tier0.result, *(output.result for output in later)],
        signals=[*tier0.signals, *(signal for output in succeeded for signal in output.signals)],
        lowered=lowered,
        adjustments=adjustments_used(tier0.features),
        model_rationale=succeeded[-1].rationale if succeeded else None,
    )
