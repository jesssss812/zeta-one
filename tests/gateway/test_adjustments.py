"""Verified outcomes change risk through recorded, scoped adjustments (decision 0013), on the real stages."""

import base64
import sqlite3
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from zeta_one.contracts import Feature
from zeta_one.gateway.adjustments import CONFIRMATION_DAYS, Adjustments
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import real_stages
from zeta_one.identity.signing import sign
from zeta_one.risk import escalation
from zeta_one.rho.seed import SEED_NOW

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}
AGENT, BUSINESS = "agent_ap_assistant_01", "biz_seed_01"
PATH = "/v1/actions/propose_payment"


@pytest.fixture
def world():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    stages = real_stages(connection)
    clock = [SEED_NOW]
    gateway = Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: clock[0])
    client = TestClient(create_app(gateway, TOKEN))
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", headers=ADMIN, json={"agent_id": AGENT, "business_id": BUSINESS, "owner": "Controller",
                "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode()})
    grant = load_fixture("routine_bill_payment").decision_record.authorization.snapshot
    client.post("/v1/authorizations", headers=ADMIN, json=grant)
    stages.tiers = {}  # rules only: no model call in these tests
    stages.configuration = stages.configuration.model_copy(update={"tiers": ["tier0"], "escalation": "none"})
    gateway = Gateway(stages=stages, ledger=gateway.ledger, clock=lambda: clock[0])
    client = TestClient(create_app(gateway, TOKEN))
    return client, gateway, key, clock


def propose(world, proposal):
    client, _, key, clock = world
    body = proposal.model_dump_json().encode()
    answer = client.post(PATH, content=body, headers=sign(key, AGENT, "POST", PATH, body, clock[0])).json()
    return answer, client.get(f"/v1/decisions/{answer['decision_id']}", headers=ADMIN).json()


def report(client, decision_id, finding, verification="bank_confirmation"):
    body = {"finding": finding, "verification": verification, "by": "controller"}
    return client.post(f"/v1/decisions/{decision_id}/outcomes", json=body, headers=ADMIN)


def routine(**changes):
    return load_fixture("routine_bill_payment").proposal.model_copy(update=changes)


def test_verified_fraud_blocks_the_method_and_later_decisions_cite_it(world):
    client, gateway, _, clock = world
    first, _ = propose(world, routine())
    assert first["decision"] == "allow"
    report(client, first["decision_id"], "payee_fraud")
    [block] = gateway.adjustments.active(BUSINESS, clock[0])
    assert (block.kind, block.subject, block.expires_at) == ("blocked_payment_method", routine().payment_method_id, None)
    clock[0] += timedelta(days=10)  # past the duplicate window, so only the block can stop it
    second, record = propose(world, routine(bill_id=None, source_document_ids=[]))
    assert second["decision"] == "block"
    assert "payment_method_blocked" in record["risk"]["floor"]["flags"]
    assert record["risk"]["adjustments"] == [block.adjustment_id]


def test_a_customer_report_changes_nothing(world):
    client, gateway, _, clock = world
    first, _ = propose(world, routine())
    report(client, first["decision_id"], "payee_fraud", verification="customer_report")
    assert gateway.adjustments.all() == []


def test_revoking_a_block_is_recorded_and_lifts_it(world):
    client, gateway, _, clock = world
    first, _ = propose(world, routine())
    report(client, first["decision_id"], "payee_fraud")
    [block] = gateway.adjustments.active(BUSINESS, clock[0])
    response = client.post(f"/v1/adjustments/{block.adjustment_id}/revoke", headers=ADMIN,
                           json={"by": "controller", "reason": "the vendor's bank confirmed the account is theirs"})
    assert response.status_code == 201 and response.json()["kind"] == "revoke"
    assert gateway.adjustments.active(BUSINESS, clock[0]) == []
    assert [row.kind for row in gateway.adjustments.all()] == ["blocked_payment_method", "revoke"]  # history kept
    listed = client.get("/v1/adjustments", headers=ADMIN).json()
    assert [row["kind"] for row in listed] == ["blocked_payment_method", "revoke"]


def test_a_verified_bank_change_stops_being_a_floor_but_still_escalates(world):
    client, gateway, _, clock = world
    held = load_fixture("vendor_payment_method_changed").proposal
    answer, record = propose(world, held)
    assert answer["decision"] == "challenge" and "payment_method_changed_days_ago" in record["risk"]["floor"]["flags"]
    resolve = {"outcome": "approve", "by": "controller", "finding": "legitimate", "verification": "callback_known_number"}
    client.post(f"/v1/challenges/{answer['challenge_id']}/resolve", json=resolve, headers=ADMIN)
    [confirmed] = gateway.adjustments.active(BUSINESS, clock[0])
    assert confirmed.kind == "confirmed_method_change"
    assert confirmed.expires_at == clock[0] + timedelta(days=CONFIRMATION_DAYS)

    context = gateway.engine.load_context(held, BUSINESS, clock[0])
    output = gateway.engine.tier0(held, context, clock[0])
    floor = escalation.floor(output.features)
    assert floor is None or "payment_method_changed_days_ago" not in floor.flags
    assert "payment_method_changed_days_ago" in escalation.soft_signals(output.features)  # a model still looks
    assert escalation.adjustments_used(output.features) == [confirmed.adjustment_id]


def test_a_confirmation_expires():
    adjustments = Adjustments(sqlite3.connect(":memory:"))
    from zeta_one.contracts import RiskAdjustment
    adjustments.append(RiskAdjustment(adjustment_id="adj_x", business_id=BUSINESS, kind="confirmed_method_change",
                                      subject="pmc_1", by="c", at=SEED_NOW,
                                      expires_at=SEED_NOW + timedelta(days=CONFIRMATION_DAYS)))
    assert adjustments.active(BUSINESS, SEED_NOW + timedelta(days=CONFIRMATION_DAYS - 1))
    assert adjustments.active(BUSINESS, SEED_NOW + timedelta(days=CONFIRMATION_DAYS)) == []


def test_an_adjustment_never_reaches_another_business(world):
    client, gateway, _, clock = world
    first, _ = propose(world, routine())
    report(client, first["decision_id"], "payee_fraud")
    assert gateway.adjustments.active("biz_other", clock[0]) == []


@pytest.mark.parametrize("hard_flag", ["bill_mismatch", "document_instruction_patterns", "duplicate_candidate"])
def test_a_confirmed_change_never_lowers_another_hard_flag(hard_flag):
    features = {"payment_method_changed_days_ago": Feature(value=3), "payment_method_change_confirmed": Feature(value=True),
                hard_flag: Feature(value=True)}
    floor = escalation.floor(features)
    assert floor is not None and hard_flag in floor.flags and "payment_method_changed_days_ago" not in floor.flags


def test_a_newer_change_than_the_confirmed_one_floors_again(world):
    from zeta_one.contracts import PaymentMethodChange, RiskAdjustment
    from zeta_one.risk.features import payment_method_change_confirmed

    proposal = load_fixture("vendor_payment_method_changed").proposal
    context = load_fixture("vendor_payment_method_changed").context
    old = context.payment_method_history[-1]
    context.adjustments = [RiskAdjustment(adjustment_id="adj_c", business_id=BUSINESS, kind="confirmed_method_change",
                                          subject=old.id, by="c", at=SEED_NOW)]
    assert payment_method_change_confirmed(proposal, context, SEED_NOW).value is True
    context.payment_method_history.append(PaymentMethodChange(id="pmc_newer", method_id=proposal.payment_method_id,
                                                              change="updated", changed_at=SEED_NOW))
    assert payment_method_change_confirmed(proposal, context, SEED_NOW).value is False


def test_only_a_person_with_the_admin_token_sees_or_revokes_adjustments(world):
    client = world[0]
    assert client.get("/v1/adjustments").status_code == 401
    assert client.post("/v1/adjustments/adj_x/revoke", json={"by": "x", "reason": "y"}).status_code == 401
    assert client.post("/v1/adjustments/adj_missing/revoke", json={"by": "x", "reason": "y"}, headers=ADMIN).status_code == 404
