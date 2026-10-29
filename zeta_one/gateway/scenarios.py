"""The five demo scenarios, each run in its own sandbox on the real stages.

A run gets a fresh copy of the seed, a fresh registry with a one-off key for the scenario's agent
(none for the unknown-agent scenario), the scenario's authorization, and a request signed at the
seed's clock, `SEED_NOW`. Identity, authorization, context and tier 0 are real. A model tier the
scenario escalates to replays the answer recorded in its fixture, so a demo button never calls a
paid model; such a result is marked `illustrative` and names the replayed stages.
"""

import dataclasses
import json
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from zeta_one.contracts import Authorization, EvidenceRecord, ScenarioResult, SignedRequest
from zeta_one.gateway.pipeline import new_decision_id
from zeta_one.identity.signing import sign
from zeta_one.rho.seed import SEED_NOW
from zeta_one.rho.snapshot import Store as SeedStore

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
ORDER = [
    "vendor_payment_method_changed",
    "routine_bill_payment",
    "over_per_payment_limit",
    "unknown_agent",
    "invoice_redirect_instructions",
]
PATH = "/v1/actions/propose_payment"
# Bills cancelled in a scenario's sandbox, so its context matches its fixture. The redirect
# scenario's invoice is an open bill of the vendor the bank-change scenario pays, and its injected
# text would otherwise flag that scenario too.
CANCELLED_IN_SANDBOX = {"vendor_payment_method_changed": ("bill_0194",)}


def load_fixture(name: str) -> ScenarioResult:
    return ScenarioResult.model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


def list_scenarios() -> list[dict]:
    return [load_fixture(name).scenario.model_dump() for name in ORDER]


def run(name: str, live_models: bool = False) -> ScenarioResult:
    """Run one scenario in its sandbox. With `live_models`, a model tier it escalates to is called for
    real (paid, needs its key) instead of replaying the fixture's recorded answer."""
    from zeta_one.gateway.wiring import build_engine, real_stages

    if name not in ORDER:
        raise KeyError(name)
    scenario = load_fixture(name)
    identity = scenario.decision_record.identity
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    key = Ed25519PrivateKey.generate()
    with SeedStore() as store:
        for bill_id in CANCELLED_IN_SANDBOX.get(name, ()):
            store.put("bills", {**store.get("bills", bill_id), "status": "canceled"})
        stages = real_stages(connection, store)
        if identity.result != "unknown_agent":
            stages.registry.register(identity.claimed_agent_id, identity.business_id,
                                     identity.owner or "the business owner", key.public_key(), SEED_NOW)
        if scenario.decision_record.authorization.snapshot:
            stages.authorizations.grant(Authorization.model_validate(scenario.decision_record.authorization.snapshot))
        replayed = [] if live_models else sorted(stages.tiers)
        if not live_models:
            stages.tiers = {}  # model tiers replay the fixture's recorded answer
        engine = build_engine(stages, lambda *_: 0, replay=scenario, clock=lambda: SEED_NOW)
        engine = dataclasses.replace(engine, new_id=new_decision_id)
        body = scenario.proposal.model_dump_json().encode()
        request = SignedRequest(method="POST", path=PATH, body=body,
                                headers=sign(key, identity.claimed_agent_id, "POST", PATH, body, SEED_NOW))
        record, _ = engine.evaluate(request)
    connection.close()
    ran_models = [name for name in replayed if name in record.risk.tiers_run]
    # The record says it came from a sandboxed demo run, so no one reads it as a real agent's decision.
    record = EvidenceRecord.model_validate({**record.model_dump(by_alias=True), "sandbox": {"scenario": name}})
    return scenario.model_copy(update={"decision_record": record, "illustrative": bool(ran_models),
                                       "replayed_stages": ran_models})


def dump(record: EvidenceRecord | ScenarioResult) -> dict:
    """The JSON shape served to the site, with aliases applied (`risk.lowered.from`)."""
    return record.model_dump(mode="json", by_alias=True)
