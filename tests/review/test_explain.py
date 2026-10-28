"""The reviewer's one-line reason, built from the evidence record, and the inbox that lists it."""

import base64
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import CONFIGURATIONS, real_stages
from zeta_one.identity.signing import sign
from zeta_one.review.explain import summary
from zeta_one.rho.seed import SEED_NOW

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}


def record(name):
    return load_fixture(name).decision_record.model_dump(mode="json", by_alias=True)


@pytest.mark.parametrize("name, action, headline", [
    ("routine_bill_payment", "Paid (simulated)", "Agent verified · within its $5,000.00 limit · nothing unusual about the payment"),
    ("over_per_payment_limit", "Blocked", "Agent verified · $7,200.00 is over its $5,000.00 limit"),
    ("unknown_agent", "Blocked", "Agent not verified: unknown agent"),
])
def test_each_question_is_answered_until_one_fails(name, action, headline):
    out = summary(record(name))
    assert (out["action"], out["headline"]) == (action, headline)


def test_a_bank_change_is_named_with_its_age_and_the_record_that_shows_it():
    out = summary(record("vendor_payment_method_changed"))
    risk = out["parts"][-1]
    assert out["action"] == "Confirm before paying" and not risk["ok"]
    assert "bank details changed 3 days ago" in risk["text"] and "pmh_0042" in risk["evidence"]
    assert [part["question"] for part in out["parts"]] == ["identity", "authorization", "risk"]


def test_injected_invoice_text_is_named_first():
    out = summary(record("invoice_redirect_instructions"))
    assert out["parts"][-1]["text"].startswith("the invoice text gives the agent instructions")
    assert len(out["parts"][-1]["evidence"]) == len(set(out["parts"][-1]["evidence"]))


def test_the_summary_carries_stage_timings_and_the_models_that_ran():
    out = summary(record("vendor_payment_method_changed"))
    assert set(out["stages"]) <= {"identity", "authorization", "risk"} and "total" not in out["stages"]
    assert out["models"] == [tier for tier in record("vendor_payment_method_changed")["risk"]["tiers_run"] if tier != "tier0"]


def test_the_inbox_lists_decisions_newest_first_with_their_reason_and_needs_the_token():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    configuration = CONFIGURATIONS["engineered"].model_copy(update={"tiers": ["tier0"], "escalation": "none"})
    gateway = Gateway(stages=real_stages(connection, configuration=configuration), ledger=Ledger(connection), clock=lambda: SEED_NOW)
    client = TestClient(create_app(gateway, TOKEN))
    routine = load_fixture("routine_bill_payment")
    identity = routine.decision_record.identity
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", headers=ADMIN, json={
        "agent_id": identity.claimed_agent_id, "business_id": identity.business_id, "owner": "owner",
        "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    client.post("/v1/authorizations", headers=ADMIN, json=routine.decision_record.authorization.snapshot)
    path, body = "/v1/actions/propose_payment", routine.proposal.model_dump_json().encode()
    decided = client.post(path, content=body, headers=sign(key, identity.claimed_agent_id, "POST", path, body, SEED_NOW)).json()

    assert client.get("/v1/inbox").status_code == 401
    rows = client.get("/v1/inbox", headers=ADMIN).json()
    assert [row["decision_id"] for row in rows] == [decided["decision_id"]]
    row = rows[0]
    assert (row["vendor"], row["decision"], row["case_ids"], row["outcome"]) == ("Cedar Ridge Cleaning Services", "allow", [], None)
    assert row["headline"].startswith("Agent verified")

    client.post(f"/v1/decisions/{decided['decision_id']}/outcomes", headers=ADMIN, json={
        "finding": "payee_fraud", "verification": "customer_report", "by": "AP controller", "note": None})
    outcome = client.get("/v1/inbox", headers=ADMIN).json()[0]["outcome"]
    assert outcome["finding"] == "payee_fraud" and outcome["verified"] is False


def test_a_confirmed_bank_change_says_so():
    raw = record("vendor_payment_method_changed")
    raw["risk"]["features"]["payment_method_change_confirmed"] = {"value": True, "evidence": ["adj_x"]}
    risk = summary(raw)["parts"][-1]
    assert "bank details changed 3 days ago, confirmed by a person" in risk["text"] and "adj_x" in risk["evidence"]
