"""Which implementation runs each stage of the Engine.

`real_stages(connection)` builds every real stage: the agent registry and authorization store on the
gateway's SQLite connection, the synthetic Rho seed as the context source, tier 0 and the strong
tier. `build_engine` uses them and, given a fixture as `replay`, falls back stage by stage to that
fixture's replay stand-ins; demo scenarios use that to replay the model's recorded answer instead of
calling it. `register_demo_agents` registers the built-in demo agent from its local key in
`data/keys/` (made by `scripts/keygen.py`) and grants it the demo authorization.
"""

import sqlite3
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from zeta_one.authorization.check import checker
from zeta_one.authorization.store import Store as AuthorizationStore
from zeta_one.gateway.pipeline import Engine
from zeta_one.identity.registry import Registry
from zeta_one.identity.signing import verifier
from zeta_one.rho.snapshot import Store as SeedStore
from zeta_one.rho.view import context_for
from zeta_one.risk import claude
from zeta_one.risk import jev
from zeta_one.risk.claude import StrongTier
from zeta_one.risk.jev import JevTier
from zeta_one.risk import open_weight
from zeta_one.risk.open_weight import OpenWeightTier
from zeta_one.risk.tier0 import Tier0 as RealTier0
from zeta_one.testing.replay import replay_engine

ROOT = Path(__file__).resolve().parents[2]
KEYS = ROOT / "data" / "keys"
# Built-in demo agents: key file name -> the fixture whose identity and authorization they take.
DEMO_AGENTS = {"ap_assistant": "routine_bill_payment"}
# The live gateway's risk configurations, chosen by ZETA_RISK_CONFIGURATION (decisions 0007, 0009).
CONFIGURATIONS = {
    "engineered": Configuration(tiers=["tier0", "strong"], escalation="engineered"),
    "jev": Configuration(tiers=["tier0", "cheap", "strong"], escalation="jev"),
    # The comparison arm: an open-weight model in the strong tier's place (decision 0009).
    "open_weight": Configuration(tiers=["tier0", "open_weight"], escalation="engineered"),
}
CONFIGURATION_NAME = "ZETA_RISK_CONFIGURATION"

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
    # Where admin endpoints register agents and grant authorizations; None when the stages are stand-ins.
    registry: Registry | None = None
    authorizations: AuthorizationStore | None = None

    def missing(self) -> list[str]:
        required = ["verify_identity", "load_authorization", "make_checker", "load_context", "tier0", "agent_status"]
        missing = [name for name in required if getattr(self, name) is None]
        missing += [f"tiers.{name}" for name in self.configuration.tiers if name != "tier0" and name not in self.tiers]
        return missing


def configuration_from_env() -> Configuration:
    """The configuration ZETA_RISK_CONFIGURATION names: `engineered` (the default) or `jev`."""
    import os

    name = os.environ.get(CONFIGURATION_NAME, "engineered")
    if name not in CONFIGURATIONS:
        raise ValueError(f"{CONFIGURATION_NAME} must be one of {sorted(CONFIGURATIONS)}, not {name!r}")
    return CONFIGURATIONS[name]


def real_stages(connection: sqlite3.Connection, store: SeedStore | None = None,
                configuration: Configuration | None = None) -> Stages:
    """Every real stage, on the gateway's connection and a seed store (a fresh one by default)."""
    store = store or SeedStore()
    registry, authorizations = Registry(connection), AuthorizationStore(connection)

    def agent_status(agent_id: str) -> str | None:
        agent = registry.get(agent_id)
        return agent.status if agent else None

    return Stages(
        verify_identity=verifier(registry),
        load_authorization=authorizations.loader(),
        make_checker=checker,
        load_context=context_for(store),
        tier0=RealTier0(),
        tiers={"cheap": JevTier(), "strong": StrongTier(), "open_weight": OpenWeightTier()},
        agent_status=agent_status,
        configuration=configuration or CONFIGURATIONS["engineered"],
        prices={**claude.PRICES, **jev.PRICES, **open_weight.prices()},
        seed_version=store.seed_version,
        registry=registry,
        authorizations=authorizations,
    )


def register_demo_agents(stages: Stages, keys: Path = KEYS, now: datetime | None = None) -> list[str]:
    """Register each demo agent whose key exists and that isn't registered yet, and grant it the demo
    authorization. Returns the agent ids it registered; never prints or logs key material."""
    from zeta_one.gateway.scenarios import load_fixture

    registered = []
    now = now or datetime.now(UTC)
    for name, fixture in DEMO_AGENTS.items():
        path = keys / f"{name}.pem"
        if not path.exists() or stages.registry is None or stages.authorizations is None:
            continue
        record = load_fixture(fixture).decision_record
        agent_id, business_id = record.identity.claimed_agent_id, record.identity.business_id
        if stages.registry.get(agent_id) is not None:
            continue
        key = load_pem_private_key(path.read_bytes(), password=None)
        stages.registry.register(agent_id, business_id, record.identity.owner or "the business owner",
                                 key.public_key(), now)
        if stages.authorizations.load(business_id, agent_id) is None:
            from zeta_one.contracts import Authorization

            stages.authorizations.grant(Authorization.model_validate(record.authorization.snapshot))
        registered.append(agent_id)
    return registered


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
