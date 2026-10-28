"""What turns a case and a configuration into a decision.

A backend owns everything about the engine: fresh data for each case, signing with the case's agent,
the evaluation's own setup ops (see eval/cases.py) and any follow-up steps. `ReplayBackend` runs the
five demo cases through the kernel's replay stand-ins, to test the runner and report. `RealBackend`
runs every case through the gateway on the real stages, each in its own sandbox: a fresh seed with
the case's setup, a fresh SQLite ledger, registry and authorization store, a one-off key, and the
seed's clock. With the live strong tier it calls a paid model, so the runner needs `--live` and a
budget; tests pass a stand-in tier.
"""

import dataclasses
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from eval import cases as hand_cases
from zeta_one.contracts import (
    Authorization,
    Case,
    Configuration,
    Decision,
    EvidenceRecord,
    InvalidProposal,
    Proposal,
    RiskInput,
    SetupOp,
    SignedRequest,
    TierOutput,
    TierResult,
)
from zeta_one.gateway import scenarios
from zeta_one.testing.replay import replay_engine, request_for


class Unsupported(Exception):
    """The backend cannot run this case; the report counts it as not run."""


@dataclass
class Outcome:
    decision: Decision
    record: EvidenceRecord | None = None
    # Decisions of every send, when the case repeats its request.
    decisions: list[Decision] = field(default_factory=list)
    model_calls: int | None = None
    # What every send of the case cost, when the backend measures it.
    cost_usd: float | None = None


class Backend(Protocol):
    name: str
    # True when a run can call a paid model: the runner then needs --live and a budget.
    paid: bool
    # True when the records' latency is the engine's, not a replay's wall-clock time.
    measures_latency: bool

    def run(self, case: Case, configuration: Configuration) -> Outcome: ...


class ReplayBackend:
    name = "replay"
    paid = False
    measures_latency = False

    def __init__(self) -> None:
        self._fixture_of = {case_id: fixture for fixture, (case_id, *_rest) in hand_cases.DEMO.items()}

    def run(self, case: Case, configuration: Configuration) -> Outcome:
        fixture = self._fixture_of.get(case.id)
        if fixture is None:
            raise Unsupported("the replay backend only knows the five demo cases")
        scenario = scenarios.load_fixture(fixture)
        engine = dataclasses.replace(replay_engine(scenario), configuration=configuration)
        record, _ = engine.evaluate(request_for(scenario))
        return Outcome(decision=record.decision, record=record, decisions=[record.decision])


class _FailingTier:
    """A model tier that errors on every call: the `fail_model` setup op."""

    def __init__(self, name: str = "strong"):
        self.name = name

    def assess(self, risk_input: RiskInput) -> TierOutput:
        return TierOutput(result=TierResult(tier=self.name, error="evaluation: fail_model"))


PATH = "/v1/actions/propose_payment"
ADMIN_TOKEN = "eval-admin-token"
STALE_SECONDS = 400  # outside the verifier's 300-second window


class RealBackend:
    name = "real"
    measures_latency = True

    def __init__(self, strong_tier: Any = None, cheap_tier: Any = None, open_weight_tier: Any = None):
        """`strong_tier`, `cheap_tier` and `open_weight_tier` stand in for the live strong tier, Jev and
        the open-weight model; None uses the live one, which is paid."""
        from zeta_one.gateway.wiring import engine_version

        self._strong, self._cheap, self._open_weight = strong_tier, cheap_tier, open_weight_tier
        self.paid = strong_tier is None or cheap_tier is None or open_weight_tier is None
        self._version = engine_version()

    def paid_for(self, configuration: Configuration) -> bool:
        """Whether a run under this configuration can call a live, paid model tier."""
        live = {"strong": self._strong is None, "cheap": self._cheap is None,
                "open_weight": self._open_weight is None}
        return any(live.get(tier, False) for tier in configuration.tiers)

    def run(self, case: Case, configuration: Configuration) -> Outcome:
        from zeta_one.gateway.app import create_app
        from zeta_one.gateway.ledger import Ledger
        from zeta_one.gateway.reuse import RiskReuse
        from zeta_one.gateway.service import Gateway
        from zeta_one.gateway.wiring import real_stages
        from zeta_one.identity.signing import sign
        from zeta_one.risk.claude import StrongTier
        from zeta_one.risk.jev import JevTier
        from zeta_one.risk.open_weight import OpenWeightTier
        from zeta_one.rho import mutations
        from zeta_one.rho.seed import SEED_NOW
        from zeta_one.rho.snapshot import Store as SeedStore

        name, _, fault = case.agent.removeprefix("builtin:").partition("+")
        if name != "ap_assistant":
            raise Unsupported(f"no built-in agent {name!r}")
        ops = {op.op: op for op in case.setup}
        _check_setup(case, ops, fault, configuration)
        follow_up = next((op.op for op in case.setup if op.op.startswith(hand_cases.FOLLOW_UP_PREFIX)), None)
        identity = scenarios.load_fixture("routine_bill_payment").decision_record
        agent_id, business_id = identity.identity.claimed_agent_id, identity.identity.business_id

        connection = sqlite3.connect(":memory:", check_same_thread=False)
        connection.row_factory = sqlite3.Row
        with SeedStore() as store:
            for op in case.setup:
                if op.op not in hand_cases.EVAL_OPS and not op.op.startswith(hand_cases.FOLLOW_UP_PREFIX):
                    mutations.apply(store, op)
            stages = real_stages(connection, store)
            stages.configuration = configuration
            failing = "fail_model" in ops
            stages.tiers = {
                "strong": _FailingTier("strong") if failing else (self._strong or StrongTier()),
                "cheap": _FailingTier("cheap") if failing else (self._cheap or JevTier()),
                "open_weight": _FailingTier("open_weight") if failing else (self._open_weight or OpenWeightTier()),
            }
            key = Ed25519PrivateKey.generate()
            if fault != "unknown":
                stages.registry.register(agent_id, business_id, identity.identity.owner or "owner", key.public_key(), SEED_NOW)
            if "revoke_agent" in ops:
                stages.registry.revoke(agent_id, SEED_NOW)
            if "no_authorization" not in ops:
                self._grant(stages, identity.authorization.snapshot, ops.get("grant_authorization"), SEED_NOW)
            ledger = Ledger(connection)
            if "add_spend" in ops:
                _add_spend(connection, agent_id, business_id, ops["add_spend"], SEED_NOW)
            gateway = Gateway(stages=stages, ledger=ledger, reuse=RiskReuse(connection), clock=lambda: SEED_NOW,
                              version=self._version)
            if "confirm_method_change" in ops:
                confirmation = hand_cases.confirmed_change(store, case.proposal, business_id,
                                                           SEED_NOW - timedelta(minutes=1))
                if confirmation is None:
                    raise Unsupported("confirm_method_change needs a change to the proposal's payment method")
                gateway.adjustments.append(confirmation)

            body = case.proposal.model_dump_json().encode()
            times = int(ops["repeat"].args.get("times", 1)) if "repeat" in ops else 1
            first_headers = None
            answers = []
            for send in range(times):
                if fault == "replay" and first_headers is not None:
                    headers = first_headers
                else:
                    headers = self._headers(fault, key, agent_id, body, SEED_NOW, sign)
                first_headers = first_headers or headers
                try:
                    answers.append(gateway.propose(SignedRequest(method="POST", path=PATH, headers=headers, body=body)))
                except InvalidProposal as error:
                    raise Unsupported(f"malformed proposal: {error}") from error
            # A replay case is judged on its second send; every other repeat must agree.
            judged = answers[-1]
            record = EvidenceRecord.model_validate(ledger.decision(judged["decision_id"]))
            decisions = [] if fault == "replay" else [answer["decision"] for answer in answers]
            decision = judged["decision"]
            if follow_up:
                decision = self._follow_up(follow_up, gateway, stages, judged, key, agent_id, create_app, sign, SEED_NOW)
            sent = [EvidenceRecord.model_validate(ledger.decision(answer["decision_id"])) for answer in answers]
            model_calls = sum(1 for each in sent for result in each.risk.tier_results
                              if result.tier != "tier0" and result.usage is not None)
            cost_usd = sum(each.cost.usd for each in sent if each.cost)
        connection.close()
        return Outcome(decision=decision, record=record, decisions=decisions, model_calls=model_calls,
                       cost_usd=cost_usd)

    @staticmethod
    def _grant(stages, snapshot: dict, override: SetupOp | None, now) -> None:
        document = dict(snapshot)
        args = dict(override.args) if override else {}
        if "expires_in_days" in args:
            document["expires_at"] = (now + timedelta(days=args.pop("expires_in_days"))).isoformat()
        revoke = args.pop("status", None) == "revoked"
        document.update(args)
        authorization = Authorization.model_validate(document)
        stages.authorizations.grant(authorization)
        if revoke:
            stages.authorizations.revoke(authorization.authorization_id, now)

    @staticmethod
    def _headers(fault: str, key, agent_id: str, body: bytes, now, sign) -> dict[str, str]:
        if fault == "unsigned":
            return {}
        if fault == "bad_signature":
            return sign(key, agent_id, "POST", PATH, body + b" ", now)
        if fault == "stale_timestamp":
            return sign(key, agent_id, "POST", PATH, body, now - timedelta(seconds=STALE_SECONDS))
        return sign(key, agent_id, "POST", PATH, body, now)

    @staticmethod
    def _follow_up(op: str, gateway, stages, answer: dict, key, agent_id: str, create_app, sign, now) -> Decision:
        """Block when the payment did not execute after the follow-up, allow when it did."""
        challenge = answer.get("challenge_id")
        if challenge is None:
            raise Unsupported(f"{op} needs a held payment, but the decision was {answer['decision']}")
        if op == "after:agent_resolves_own_challenge":
            # The agent even holds the admin token here: the refusal must come from its signature.
            client = TestClient(create_app(gateway, ADMIN_TOKEN))
            path = f"/v1/challenges/{challenge}/resolve"
            content = json.dumps({"outcome": "approve", "by": agent_id}).encode()
            headers = {**sign(key, agent_id, "POST", path, content, now), "Authorization": f"Bearer {ADMIN_TOKEN}"}
            response = client.post(path, content=content, headers=headers)
            if response.status_code != 403:
                raise RuntimeError(f"self-approval answered {response.status_code}, not 403 agent_signed")
        elif op == "after:revoke_then_approve":
            held = gateway.ledger.held(challenge)
            stages.authorizations.revoke(held.authorization_id, now)
            gateway.resolve(challenge, "approve", "evaluation admin")
        else:
            raise Unsupported(f"unknown follow-up {op}")
        status = gateway.ledger.held(challenge).status
        return "allow" if status == "executed" else "block"


def _check_setup(case: Case, ops: dict[str, SetupOp], fault: str, configuration: Configuration) -> None:
    """Refuse a case the backend can't run faithfully, rather than run something else and score it."""
    evaluation_ops = [op.op for op in case.setup if op.op in hand_cases.EVAL_OPS]
    repeated = sorted({name for name in evaluation_ops if evaluation_ops.count(name) > 1})
    if repeated:
        raise Unsupported(f"setup repeats {repeated}; each evaluation op may appear once")
    if fault == "replay" and "repeat" not in ops:
        raise Unsupported("a +replay agent needs a repeat op, so a second send is judged")
    models = any(tier != "tier0" for tier in configuration.tiers) and configuration.escalation != "none"
    if not models and ("fail_model" in ops or ("repeat" in ops and fault != "replay")):
        raise Unsupported("this guardrail needs a configuration that runs a model")


def _add_spend(connection, agent_id: str, business_id: str, op: SetupOp, now) -> None:
    """An executed payment by the agent, to an unrelated payee, for the rolling limit."""
    from zeta_one.contracts import Money

    amount = Money(amount=int(op.args["amount"]), currency=op.args.get("currency", "USD"))
    at = (now - timedelta(days=float(op.args.get("days_ago", 1)))).isoformat()
    decision_id, payment_id = f"dec_spend_{uuid.uuid4().hex[:8]}", f"pay_spend_{uuid.uuid4().hex[:8]}"
    proposal = Proposal(counterparty_id="cp_eval_prior_payee", payment_method_id="pm_prior", source_account_id="acct",
                        amount=amount)
    with connection:
        connection.execute("INSERT INTO decisions (decision_id, created_at, record) VALUES (?, ?, ?)",
                           (decision_id, at, json.dumps({"note": "evaluation setup: an earlier payment"})))
        connection.execute(
            """INSERT INTO payments (payment_id, decision_id, agent_id, business_id, proposal, amount, currency,
               status, created_at, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'executed', ?, ?)""",
            (payment_id, decision_id, agent_id, business_id, proposal.model_dump_json(), amount.amount,
             amount.currency, at, at))


def get_backend(name: str) -> Backend:
    if name == "replay":
        return ReplayBackend()
    if name == "real":
        return RealBackend()
    raise ValueError(f"unknown backend {name!r}; choose from: replay, real")
