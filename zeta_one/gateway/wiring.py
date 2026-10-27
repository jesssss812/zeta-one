"""Which implementation runs each stage of the Engine.

`real_stages()` names the real stages that exist. `build_engine` uses them and, for a demo scenario,
falls back stage by stage to the replay stand-ins of its fixture. The live agent endpoint has no
fixture to fall back to, so it runs only once every stage is real.
"""

import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from zeta_one.contracts import (
    AuthorizationChecker,
    AuthorizationSource,
    Configuration,
    Context,
    ContextSource,
    IdentityVerifier,
    Proposal,
    RiskTier,
    ScenarioResult,
    SpendSource,
    Tier0,
    TierName,
)
from zeta_one.gateway.pipeline import Engine
from zeta_one.risk import claude
from zeta_one.risk.claude import StrongTier
from zeta_one.testing.replay import replay_engine

ROOT = Path(__file__).resolve().parents[2]

# An agent's registry status ("active", "revoked") or None when unknown: what resolve rechecks.
AgentStatus = Callable[[str], str | None]
CheckerFactory = Callable[[SpendSource], AuthorizationChecker]


@dataclass
class Stages:
    verify_identity: IdentityVerifier | None = None
    load_authorization: AuthorizationSource | None = None
    make_checker: CheckerFactory | None = None
    load_context: ContextSource | None = None
    tier0: Tier0 | None = None
    tiers: dict[TierName, RiskTier] = field(default_factory=dict)
    agent_status: AgentStatus | None = None
    configuration: Configuration = field(default_factory=Configuration)
    prices: dict[str, tuple[float, float]] = field(default_factory=dict)
    seed_version: str | None = None

    def missing(self) -> list[str]:
        required = ["verify_identity", "load_authorization", "make_checker", "load_context", "tier0", "agent_status"]
        missing = [name for name in required if getattr(self, name) is None]
        missing += [f"tiers.{name}" for name in self.configuration.tiers if name != "tier0" and name not in self.tiers]
        return missing


def real_stages() -> Stages:
    """The real stages that have landed. Replay stands in for the rest in demo scenarios."""
    return Stages(tiers={"strong": StrongTier()}, prices=dict(claude.PRICES))


class StagesMissing(RuntimeError):
    pass


def engine_version() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() or None


def build_engine(
    stages: Stages,
    spend: SpendSource,
    *,
    replay: ScenarioResult | None = None,
    assess_risk: Callable | None = None,
    clock: Callable[[], datetime] | None = None,
    version: str | None = None,
) -> Engine:
    """An Engine on the given stages; with `replay`, each missing stage replays that fixture."""
    if replay is None and stages.missing():
        raise StagesMissing(", ".join(stages.missing()))
    fallback = replay_engine(replay) if replay else None
    timing = {"clock": fallback.clock, "new_id": fallback.new_id} if fallback else {}
    if clock:
        timing["clock"] = clock
    return Engine(
        verify_identity=stages.verify_identity or fallback.verify_identity,
        load_authorization=stages.load_authorization or fallback.load_authorization,
        check_authorization=stages.make_checker(spend) if stages.make_checker else fallback.check_authorization,
        load_context=stages.load_context or fallback.load_context,
        tier0=stages.tier0 or fallback.tier0,
        tiers={**(fallback.tiers if fallback else {}), **stages.tiers},
        configuration=stages.configuration,
        prices=stages.prices,
        engine_version=version,
        seed_version=stages.seed_version,
        assess_risk=assess_risk,
        **timing,
    )


class ContextCapture:
    """Wraps a ContextSource so the caller can keep the context a decision was made on."""

    def __init__(self, load_context: ContextSource):
        self._load_context = load_context
        self._seen: ContextVar[list[Context] | None] = ContextVar("seen", default=None)

    def __call__(self, proposal: Proposal, business_id: str, now: datetime) -> Context:
        context = self._load_context(proposal, business_id, now)
        seen = self._seen.get()
        if seen is not None:
            seen.append(context)
        return context

    @contextmanager
    def recording(self) -> Iterator[list[Context]]:
        seen: list[Context] = []
        token = self._seen.set(seen)
        try:
            yield seen
        finally:
            self._seen.reset(token)
