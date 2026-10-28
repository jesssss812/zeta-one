"""Run the feedback loop end to end on the real stages, in a sandbox, and record it (decisions 0012, 0013).

    .venv/bin/python scripts/demo_loop.py            # rules only: no model call
    .venv/bin/python scripts/demo_loop.py --live     # engineered: escalations call the strong tier (paid)

The story, on the synthetic seed, through the gateway's HTTP API with a signed demo agent:

1. A routine payment is allowed (simulated).
2. A customer reports it as fraud: recorded as a claim; nothing changes.
3. A reviewer verifies it with the bank: a verified finding; the payment method is blocked.
4. The agent pays the same account again ten days later: blocked, citing the finding.
5. A payment to a vendor whose bank details changed is held; the reviewer confirms by call-back.
6. That vendor's next payment: the confirmed change is a soft signal a model reviews, not a floor.
7. The stats: challenge approval rate, missed fraud, unneeded challenges.

Writes site/data/loop.json, marked recorded and simulated. Nothing leaves the sandbox: an in-memory
database, a fresh seed and a one-off key.
"""

import argparse
import base64
import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from zeta_one.contracts import POLICY_VERSION  # noqa: E402
from zeta_one.gateway.app import create_app  # noqa: E402
from zeta_one.gateway.ledger import Ledger  # noqa: E402
from zeta_one.gateway.scenarios import load_fixture  # noqa: E402
from zeta_one.gateway.service import Gateway  # noqa: E402
from zeta_one.gateway.wiring import CONFIGURATIONS, engine_version, real_stages  # noqa: E402
from zeta_one.identity.signing import sign  # noqa: E402
from zeta_one.rho.seed import SEED_NOW  # noqa: E402
from zeta_one.rho.snapshot import Store as SeedStore  # noqa: E402

OUT = ROOT / "site" / "data" / "loop.json"
TOKEN = "demo-loop-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}
PATH = "/v1/actions/propose_payment"


def run(live_models: bool = False) -> dict:
    routine = load_fixture("routine_bill_payment")
    identity = routine.decision_record.identity
    agent, business = identity.claimed_agent_id, identity.business_id
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    configuration = CONFIGURATIONS["engineered"] if live_models else CONFIGURATIONS["engineered"].model_copy(
        update={"tiers": ["tier0"], "escalation": "none"})
    store = SeedStore()
    changed_vendor, changed_vendor_next = _vendor_with_recent_change(store)
    stages = real_stages(connection, store, configuration=configuration)
    clock = [SEED_NOW]
    gateway = Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: clock[0], version=engine_version())
    client = TestClient(create_app(gateway, TOKEN))
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", headers=ADMIN, json={
        "agent_id": agent, "business_id": business, "owner": identity.owner or "the business owner",
        "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    client.post("/v1/authorizations", headers=ADMIN, json=routine.decision_record.authorization.snapshot)
    steps: list[dict] = []

    def propose(proposal) -> dict:
        body = proposal.model_dump_json().encode()
        answer = client.post(PATH, content=body, headers=sign(key, agent, "POST", PATH, body, clock[0])).json()
        return client.get(f"/v1/decisions/{answer['decision_id']}", headers=ADMIN).json() | {"_answer": answer}

    def step(title: str, what: str, record: dict | None = None, **extra) -> None:
        entry = {"title": title, "what": what, "at": clock[0].isoformat(), **extra}
        if record:
            risk = record["risk"]
            entry["decision"] = {
                "decision_id": record["decision_id"], "decision": record["decision"], "reasons": record["reasons"],
                "floor": risk.get("floor"), "level": risk.get("level"), "tiers_run": risk.get("tiers_run"),
                "adjustments": risk.get("adjustments", []), "execution": record["execution"],
            }
        steps.append(entry)

    def outcome(decision_id: str, finding: str, verification: str, note: str) -> dict:
        return client.post(f"/v1/decisions/{decision_id}/outcomes", headers=ADMIN, json={
            "finding": finding, "verification": verification, "by": "AP controller", "note": note}).json()

    paid = propose(routine.proposal)
    step("A routine payment", "The agent pays a recurring invoice to a long-standing vendor.", paid)

    clock[0] += timedelta(days=2)
    claim = outcome(paid["decision_id"], "payee_fraud", "customer_report",
                    "The vendor says the payment never arrived.")
    step("A customer reports fraud", "Recorded as a claim: a report alone is not a fraud label.",
         outcome=claim, adjustments=client.get("/v1/adjustments", headers=ADMIN).json())

    clock[0] += timedelta(hours=3)
    verified = outcome(paid["decision_id"], "payee_fraud", "bank_confirmation",
                       "The receiving bank confirmed the account is not the vendor's.")
    adjustments = client.get("/v1/adjustments", headers=ADMIN).json()
    step("A reviewer verifies it", "A verified finding blocks the payment method it went to.",
         outcome=verified, adjustments=adjustments)

    clock[0] += timedelta(days=8)
    again = propose(routine.proposal.model_copy(update={"bill_id": None, "source_document_ids": []}))
    step("The agent pays that account again", "Blocked: the decision cites the finding behind the block.", again)

    held_proposal = changed_vendor
    held = propose(held_proposal)
    step("A payment after a recent bank change", "Held: a recent change is a floor no model may lower.", held)
    resolved = client.post(f"/v1/challenges/{held['_answer']['challenge_id']}/resolve", headers=ADMIN, json={
        "outcome": "approve", "by": "AP controller", "finding": "legitimate",
        "verification": "callback_known_number", "note": "Called the number on file; the vendor confirmed."}).json()
    step("The reviewer confirms the change", "Approved after a call-back; that change is now confirmed.",
         resolution=resolved, adjustments=client.get("/v1/adjustments", headers=ADMIN).json())

    clock[0] += timedelta(days=8)
    later = propose(changed_vendor_next)
    step("That vendor's next payment",
         "The confirmed change is no longer a floor: a soft signal a model reviews"
         + ("." if live_models else " (models are off in this run, so it is held for a person)."), later)

    step("What the business sees", "Friction and missed fraud from real decisions.",
         stats=client.get("/v1/stats", headers=ADMIN).json())
    connection.close()
    store.close()
    return {
        "recorded": True, "simulated": True, "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine_version": engine_version(), "policy_version": POLICY_VERSION, "live_models": live_models,
        "note": "A recorded run of the feedback loop on the real engine and synthetic data. Payments are simulated."
                + ("" if live_models else " Models were off: escalations show where a model would review."),
        "steps": steps,
    }


def _vendor_with_recent_change(store) -> tuple:
    """A synthetic vendor paid monthly for a year whose bank details changed three days ago, with this
    month's and next month's clean bills: the recent change is the only floor. Built with the
    evaluation's own setup. Returns the two payments."""
    from eval import generate
    from zeta_one.contracts import Proposal, SetupOp
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="engineered configuration: calls the strong tier (paid)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    loop = run(live_models=args.live)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(loop, indent=2, sort_keys=True, default=str) + "\n")
    for number, entry in enumerate(loop["steps"], 1):
        decision = entry.get("decision")
        detail = f" -> {decision['decision']} {decision['reasons']}" if decision else ""
        print(f"{number}. {entry['title']}{detail}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
