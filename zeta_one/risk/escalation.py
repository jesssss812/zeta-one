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
    if days is not None and days <= RECENT_CHANGE_DAYS:
        raise_to("elevated", "payment_method_changed_days_ago")
    for flag in ("lookalike_counterparty", "duplicate_candidate"):
        if _true(features, flag):
            raise_to("elevated", flag)
    return Floor(level=level, flags=flags) if level else None


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
    if days is not None and days > RECENT_CHANGE_DAYS:
        found.append("payment_method_changed_days_ago")
    return found


def should_escalate(configuration: Configuration, tier0: Tier0Output) -> bool:
    """Whether the first model tier runs after tier 0."""
    if configuration.escalation == "none":
        return False
    if configuration.escalation == "always":
        return True
    if configuration.escalation == "engineered":
        return tier0.result.level in ("elevated", "high") or bool(soft_signals(tier0.features))
    raise NotImplementedError("the Jev escalation rule arrives with the Jev tier (extension 4)")


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
        model_rationale=succeeded[-1].rationale if succeeded else None,
    )
