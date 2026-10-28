"""Registering and revoking agents and authorizations: admin only, never an agent (S6)."""

import base64
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import real_stages
from zeta_one.identity.signing import sign
from zeta_one.rho.seed import SEED_NOW

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}
AGENT, BUSINESS = "agent_new_01", "biz_seed_01"


@pytest.fixture
def setup():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    stages = real_stages(connection)
    gateway = Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: SEED_NOW)
    return TestClient(create_app(gateway, TOKEN)), stages


def _registration(key, agent_id=AGENT):
    raw = key.public_key().public_bytes_raw()
    return {"agent_id": agent_id, "business_id": BUSINESS, "owner": "Controller", "public_key": base64.b64encode(raw).decode()}


def _grant(agent_id=AGENT, version=1, authorization_id="auth_new"):
    snapshot = load_fixture("routine_bill_payment").decision_record.authorization.snapshot
    return {**snapshot, "agent_id": agent_id, "version": version, "authorization_id": authorization_id}


def _propose(client, key, agent_id=AGENT):
    body = load_fixture("routine_bill_payment").proposal.model_dump_json().encode()
    path = "/v1/actions/propose_payment"
    return client.post(path, content=body, headers=sign(key, agent_id, "POST", path, body, SEED_NOW)).json()


@pytest.mark.parametrize("method_path", ["/v1/agents", "/v1/agents/x/revoke", "/v1/authorizations",
                                         "/v1/authorizations/x/revoke"])
def test_every_admin_endpoint_refuses_no_token_and_agent_signed_requests(setup, method_path):
    client, _ = setup
    assert client.post(method_path, json={}).status_code == 401
    signed = {**ADMIN, "Zeta-Signature": "abc", "Zeta-Nonce": "n"}
    assert client.post(method_path, json={}, headers=signed).status_code == 403


def test_register_grant_pay_then_revoke(setup):
    client, stages = setup
    key = Ed25519PrivateKey.generate()
    response = client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    assert response.status_code == 201 and "public_key" not in response.json()
    assert _propose(client, key)["decision"] == "block"  # no authorization yet
    assert client.post("/v1/authorizations", json=_grant(), headers=ADMIN).status_code == 201
    assert _propose(client, key)["decision"] == "allow"
    assert client.post(f"/v1/agents/{AGENT}/revoke", headers=ADMIN).json()["status"] == "revoked"
    assert _propose(client, key)["decision"] == "block"


def test_revoking_an_authorization_blocks_the_agent(setup):
    client, _ = setup
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    client.post("/v1/authorizations", json=_grant(), headers=ADMIN)
    assert client.post("/v1/authorizations/auth_new/revoke", headers=ADMIN).json()["status"] == "revoked"
    assert _propose(client, key)["decision"] == "block"


def test_bad_registrations_and_grants_are_refused(setup):
    client, _ = setup
    key = Ed25519PrivateKey.generate()
    assert client.post("/v1/agents", json={**_registration(key), "public_key": "not base64!"}, headers=ADMIN).status_code == 400
    assert client.post("/v1/agents", json={**_registration(key), "public_key": base64.b64encode(b"short").decode()},
                       headers=ADMIN).status_code == 400
    assert client.post("/v1/agents", json={**_registration(key), "extra": 1}, headers=ADMIN).status_code == 400
    assert client.post("/v1/agents", json=_registration(key), headers=ADMIN).status_code == 201
    assert client.post("/v1/agents", json=_registration(key), headers=ADMIN).status_code == 409
    assert client.post("/v1/authorizations", json=_grant(agent_id="agent_nobody"), headers=ADMIN).status_code == 400
    assert client.post("/v1/authorizations", json=_grant(), headers=ADMIN).status_code == 201
    assert client.post("/v1/authorizations", json=_grant(), headers=ADMIN).status_code == 409  # version must increase
    assert client.post("/v1/agents/agent_nobody/revoke", headers=ADMIN).status_code == 404
    assert client.post("/v1/authorizations/auth_nobody/revoke", headers=ADMIN).status_code == 404


def test_admin_on_stand_in_stages_is_unavailable():
    from tests.gateway.fakes import FakeWorld

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    client = TestClient(create_app(Gateway(stages=FakeWorld().stages(), ledger=Ledger(connection)), TOKEN))
    assert client.post("/v1/agents", json={}, headers=ADMIN).status_code == 503


def test_revoking_a_superseded_version_is_404_not_a_false_success(setup):
    client, stages = setup
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    client.post("/v1/authorizations", json=_grant(authorization_id="auth_old"), headers=ADMIN)
    client.post("/v1/authorizations", json=_grant(version=2, authorization_id="auth_current"), headers=ADMIN)
    assert client.post("/v1/authorizations/auth_old/revoke", headers=ADMIN).status_code == 404
    assert stages.authorizations.load(BUSINESS, AGENT).status == "active"


def test_a_hold_whose_grant_expired_before_approval_is_blocked_on_the_real_checker():
    """S9 on the real stages: same authorization version, but it expired while the payment was held."""
    from datetime import timedelta

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    stages = real_stages(connection)
    clock = [SEED_NOW]
    gateway = Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: clock[0])
    client = TestClient(create_app(gateway, TOKEN))
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    grant = {**_grant(), "expires_at": (SEED_NOW + timedelta(hours=1)).isoformat()}
    assert client.post("/v1/authorizations", json=grant, headers=ADMIN).status_code == 201
    held = load_fixture("vendor_payment_method_changed").proposal.model_dump_json().encode()
    path = "/v1/actions/propose_payment"
    answer = client.post(path, content=held, headers=sign(key, AGENT, "POST", path, held, SEED_NOW)).json()
    assert answer["decision"] == "challenge"
    clock[0] = SEED_NOW + timedelta(hours=2)
    resolved = client.post(f"/v1/challenges/{answer['challenge_id']}/resolve", json={"outcome": "approve", "by": "owner"},
                           headers=ADMIN).json()
    assert resolved["status"] == "blocked"
    review = client.get(f"/v1/decisions/{answer['decision_id']}", headers=ADMIN).json()["review"]
    assert "authorization:expires_at" in review["changes"]


def test_a_rolling_limit_on_the_real_checker_counts_the_ledger(setup):
    """S8 on the real stages: the second payment that would pass the rolling cap is blocked."""
    client, _ = setup
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    limits = {"per_payment": {"amount": 500000, "currency": "USD"},
              "rolling": {"window_days": 7, "amount": {"amount": 300000, "currency": "USD"}}}
    client.post("/v1/authorizations", json={**_grant(), "limits": limits}, headers=ADMIN)
    assert _propose(client, key)["decision"] == "allow"   # $1,850
    second = _propose(client, key)                         # $3,700 > $3,000
    record = client.get(f"/v1/decisions/{second['decision_id']}", headers=ADMIN).json()
    assert second["decision"] == "block" and record["reasons"] == ["authorization:limits.rolling"]


def test_late_approval_counts_execution_in_the_current_rolling_window():
    from datetime import timedelta
    from tests.gateway.fakes import FakeWorld
    from zeta_one.gateway.reuse import RiskReuse

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    stages = real_stages(connection)
    world = FakeWorld()
    stages.tiers = {"strong": world._Strong(world)}
    clock = [SEED_NOW]
    gateway = Gateway(stages=stages, ledger=Ledger(connection), reuse=RiskReuse(connection), clock=lambda: clock[0])
    client = TestClient(create_app(gateway, TOKEN))
    key = Ed25519PrivateKey.generate()
    client.post("/v1/agents", json=_registration(key), headers=ADMIN)
    amount = load_fixture("vendor_payment_method_changed").proposal.amount.amount
    limits = {"rolling": {"window_days": 1, "amount": {"amount": amount, "currency": "USD"}}}
    grant = {**_grant(), "limits": limits, "expires_at": (SEED_NOW + timedelta(days=10)).isoformat()}
    assert client.post("/v1/authorizations", json=grant, headers=ADMIN).status_code == 201
    body = load_fixture("vendor_payment_method_changed").proposal.model_dump_json().encode()
    path = "/v1/actions/propose_payment"
    held = client.post(path, content=body, headers=sign(key, AGENT, "POST", path, body, clock[0])).json()
    assert held["decision"] == "challenge"
    clock[0] += timedelta(days=2)
    # An outstanding hold continues to reserve its amount even after the original window ages out.
    assert gateway.ledger.spend(AGENT, clock[0] - timedelta(days=1), "USD") == amount
    resolved = client.post(f"/v1/challenges/{held['challenge_id']}/resolve",
                           json={"outcome": "approve", "by": "owner"}, headers=ADMIN).json()
    assert resolved["status"] == "executed"
    assert gateway.ledger.spend(AGENT, clock[0] - timedelta(days=1), "USD") == amount
    second = client.post(path, content=body, headers=sign(key, AGENT, "POST", path, body, clock[0])).json()
    record = client.get(f"/v1/decisions/{second['decision_id']}", headers=ADMIN).json()
    assert second["decision"] == "block"
    assert record["reasons"] == ["authorization:limits.rolling"]
