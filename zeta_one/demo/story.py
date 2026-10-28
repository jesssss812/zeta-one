"""The feedback loop as a story told one step at a time, on the real stages, in a sandbox (decisions
0012, 0013).

1. A routine payment is allowed (simulated).
2. A customer reports it as fraud: recorded as a claim; nothing changes.
3. A reviewer verifies it with the bank: a verified finding; the payment method is blocked.
4. The agent pays the same account again ten days later: blocked, citing the finding.
5. A payment to a vendor whose bank details changed is held; the reviewer confirms by call-back.
6. That vendor's next payment: the confirmed change is a soft signal a model reviews, not a floor.
7. The stats: challenge approval rate, missed fraud, unneeded challenges.

Everything runs through the gateway's HTTP API with a signed demo agent, on an in-memory database,
a fresh seed and a one-off key, so nothing leaves the sandbox.
"""

import base64
import sqlite3
from datetime import timedelta
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from zeta_one.contracts import Proposal
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import CONFIGURATIONS, engine_version, real_stages
from zeta_one.identity.signing import sign
from zeta_one.rho.seed import SEED_NOW
from zeta_one.rho.snapshot import Store as SeedStore

PATH = "/v1/actions/propose_payment"
TITLES = ("A routine payment", "A customer reports fraud", "A reviewer verifies it", "The agent pays that account again",
          "A payment after a recent bank change", "The reviewer confirms the change", "That vendor's next payment",
          "What the business sees")


class Story:
    """One sandbox and its story. `next()` runs the next step and returns what it showed."""

    def __init__(self, token: str, live_models: bool = False, review_client: Any = None) -> None:
        self.token, self.live_models = token, live_models
        self._admin = {"Authorization": f"Bearer {token}"}
        routine = load_fixture("routine_bill_payment")
        identity = routine.decision_record.identity
        self._routine, self._agent = routine, identity.claimed_agent_id
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        configuration = CONFIGURATIONS["engineered"] if live_models else CONFIGURATIONS["engineered"].model_copy(
            update={"tiers": ["tier0"], "escalation": "none"})
        self._store = SeedStore()
        self._changed_vendor, self._changed_vendor_next = _vendor_with_recent_change(self._store)
        stages = real_stages(self._connection, self._store, configuration=configuration)
        self._clock = [SEED_NOW]
        self.gateway = Gateway(stages=stages, ledger=Ledger(self._connection), clock=lambda: self._clock[0],
                               version=engine_version())
        if review_client is not None:
            self.gateway.review_client = review_client
        self.app: FastAPI = create_app(self.gateway, token)
        self._client = TestClient(self.app)
        self._key = Ed25519PrivateKey.generate()
        self._client.post("/v1/agents", headers=self._admin, json={
            "agent_id": self._agent, "business_id": identity.business_id, "owner": identity.owner or "the business owner",
            "public_key": base64.b64encode(self._key.public_key().public_bytes_raw()).decode()})
        self._client.post("/v1/authorizations", headers=self._admin, json=routine.decision_record.authorization.snapshot)
        self._ids: dict[str, Any] = {}
        self.steps: list[dict[str, Any]] = []
        self._plan = [self._routine_payment, self._customer_report, self._verified, self._paid_again,
                      self._held, self._confirmed, self._next_payment, self._stats]

    @property
    def done(self) -> bool:
        return len(self.steps) == len(self._plan)

    @property
    def total(self) -> int:
        return len(self._plan)

    def next(self) -> dict[str, Any] | None:
        if self.done:
            return None
        self._plan[len(self.steps)]()
        return self.steps[-1]

    def run_all(self) -> list[dict[str, Any]]:
        while not self.done:
            self.next()
        return self.steps

    def close(self) -> None:
        self._connection.close()
        self._store.close()

    # --- The steps ----------------------------------------------------------------------------------

    def _routine_payment(self) -> None:
        paid = self._propose(self._routine.proposal)
        self._ids["paid"] = paid["decision_id"]
        self._step("A routine payment", "The agent pays a recurring invoice to a long-standing vendor.", paid)

    def _customer_report(self) -> None:
        self._clock[0] += timedelta(days=2)
        claim = self._outcome(self._ids["paid"], "payee_fraud", "customer_report", "The vendor says the payment never arrived.")
        self._step("A customer reports fraud", "Recorded as a claim: a report alone is not a fraud label.",
                   outcome=claim, adjustments=self._get("/v1/adjustments"))

    def _verified(self) -> None:
        self._clock[0] += timedelta(hours=3)
        verified = self._outcome(self._ids["paid"], "payee_fraud", "bank_confirmation",
                                 "The receiving bank confirmed the account is not the vendor's.")
        self._step("A reviewer verifies it", "A verified finding blocks the payment method it went to.",
                   outcome=verified, adjustments=self._get("/v1/adjustments"))

    def _paid_again(self) -> None:
        self._clock[0] += timedelta(days=8)
        again = self._propose(self._routine.proposal.model_copy(update={"bill_id": None, "source_document_ids": []}))
        self._step("The agent pays that account again", "Blocked: the decision cites the finding behind the block.", again)

    def _held(self) -> None:
        held = self._propose(self._changed_vendor)
        self._ids["challenge"] = held["_answer"]["challenge_id"]
        self._step("A payment after a recent bank change", "Held: a recent change is a floor no model may lower.", held)

    def _confirmed(self) -> None:
        resolved = self._client.post(f"/v1/challenges/{self._ids['challenge']}/resolve", headers=self._admin, json={
            "outcome": "approve", "by": "AP controller", "finding": "legitimate",
            "verification": "callback_known_number", "note": "Called the number on file; the vendor confirmed."}).json()
        self._step("The reviewer confirms the change", "Approved after a call-back; that change is now confirmed.",
                   resolution=resolved, adjustments=self._get("/v1/adjustments"))

    def _next_payment(self) -> None:
        self._clock[0] += timedelta(days=8)
        later = self._propose(self._changed_vendor_next)
        self._step("That vendor's next payment",
                   "The confirmed change is no longer a floor: a soft signal a model reviews"
                   + ("." if self.live_models else " (models are off in this run, so it is held for a person)."), later)

    def _stats(self) -> None:
        self._step("What the business sees", "Friction and missed fraud from real decisions.", stats=self._get("/v1/stats"))

    # --- Helpers ------------------------------------------------------------------------------------

    def _get(self, path: str) -> Any:
        return self._client.get(path, headers=self._admin).json()

    def _propose(self, proposal: Proposal) -> dict[str, Any]:
        body = proposal.model_dump_json().encode()
        answer = self._client.post(PATH, content=body, headers=sign(self._key, self._agent, "POST", PATH, body, self._clock[0])).json()
        return self._get(f"/v1/decisions/{answer['decision_id']}") | {"_answer": answer}

    def _outcome(self, decision_id: str, finding: str, verification: str, note: str) -> dict[str, Any]:
        return self._client.post(f"/v1/decisions/{decision_id}/outcomes", headers=self._admin, json={
            "finding": finding, "verification": verification, "by": "AP controller", "note": note}).json()

    def _step(self, title: str, what: str, record: dict[str, Any] | None = None, **extra: Any) -> None:
        entry = {"title": title, "what": what, "at": self._clock[0].isoformat(), **extra}
        if record:
            risk = record["risk"]
            entry["decision"] = {
                "decision_id": record["decision_id"], "decision": record["decision"], "reasons": record["reasons"],
                "floor": risk.get("floor"), "level": risk.get("level"), "tiers_run": risk.get("tiers_run"),
                "adjustments": risk.get("adjustments", []), "execution": record["execution"],
            }
        self.steps.append(entry)


def _vendor_with_recent_change(store) -> tuple[Proposal, Proposal]:
    """A synthetic vendor paid monthly for a year whose bank details changed three days ago, with this
    month's and next month's clean bills: the recent change is the only floor. Built with the
    evaluation's own setup. Returns the two payments."""
    from eval import generate
    from zeta_one.contracts import SetupOp
    from zeta_one.rho import mutations

    row = {"id": "demo_loop_vendor", "vendor": "Copperline Freight", "dimensions": {
        "tenure": "established", "change_days": 3, "change_verified": "no", "amount_ratio": 1.0,
        "bill": "matches", "invoice": "clean", "rationale": "plain", "channel": "real_vendor"}}
    ops, proposal = generate.setup_for(row)
    for op in ops:
        if op["op"] == "add_bill":
            op["args"]["document_text"] = "Invoice CF-2026-1162. Freight services for October. Total $600.00, due Nov 20, 2026."
        mutations.apply(store, SetupOp(**op))
    vendor = proposal["counterparty_id"]
    mutations.apply(store, SetupOp(op="add_bill", args={
        "bill_id": "bill_demo_loop_next", "counterparty_id": vendor, "amount": proposal["amount"]["amount"],
        "currency": "USD", "document_text": "Invoice CF-2026-1209. Freight services for November. Total $600.00."}))
    october = Proposal.model_validate({**proposal, "memo": "October freight",
                                       "agent_rationale": "Matches the October freight invoice and the usual amount.",
                                       "source_document_ids": [proposal["bill_id"]]})
    november = october.model_copy(update={"bill_id": "bill_demo_loop_next", "source_document_ids": ["bill_demo_loop_next"],
                                          "memo": "November freight"})
    return october, november
