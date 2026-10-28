"""The agent endpoint (S4), admin access (S6) and the recheck on resolve (S9), on fake stages."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.gateway.fakes import AGENT, NOW, FakeWorld, agent_headers, held_proposal, routine_proposal
from zeta_one.contracts import Money
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.service import Gateway

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}
PROPOSE = "/v1/actions/propose_payment"


@pytest.fixture
def world() -> FakeWorld:
    return FakeWorld()


@pytest.fixture
def gateway(world) -> Gateway:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return Gateway(stages=world.stages(), ledger=Ledger(connection), clock=lambda: NOW)


@pytest.fixture
def client(gateway) -> TestClient:
    return TestClient(create_app(gateway, TOKEN))


def propose(client, proposal, headers=None):
    return client.post(PROPOSE, content=proposal.model_dump_json(), headers=headers or agent_headers())


def hold(client) -> dict:
    body = propose(client, held_proposal()).json()
    assert body["decision"] == "challenge" and body["challenge_id"]
    return body


def resolve(client, challenge_id, outcome="approve", headers=ADMIN):
    return client.post(f"/v1/challenges/{challenge_id}/resolve", json={"outcome": outcome, "by": "owner"}, headers=headers)


# --- S4: the agent learns only the decision and its ids ---


@pytest.mark.parametrize("make", [held_proposal, routine_proposal])
def test_propose_returns_exactly_decision_and_ids(client, make):
    body = propose(client, make()).json()
    assert set(body) == {"decision", "decision_id", "challenge_id"}


def test_routine_payment_is_allowed_and_executed_simulated(client):
    body = propose(client, routine_proposal()).json()
    assert body["decision"] == "allow" and body["challenge_id"] is None
    record = client.get(f"/v1/decisions/{body['decision_id']}", headers=ADMIN).json()
    assert record["execution"] == {"status": "executed", "simulated": True}
    assert record["risk"]["tiers_run"] == ["tier0"]


def test_unsigned_request_is_blocked_and_recorded(client):
    body = client.post(PROPOSE, content=b"not even json").json()
    assert body["decision"] == "block"
    assert client.get(f"/v1/decisions/{body['decision_id']}", headers=ADMIN).json()["reasons"] == ["identity:unsigned"]


def test_malformed_body_from_a_verified_agent_is_400(client):
    response = client.post(PROPOSE, content=b'{"amount": "lots"}', headers=agent_headers())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_proposal"
    assert client.get("/v1/decisions", headers=ADMIN).json() == []


def test_unknown_counterparty_is_400(client):
    response = propose(client, held_proposal(counterparty_id="cp_nope"))
    assert response.status_code == 400


def test_an_unknown_counterparty_is_400_whatever_the_amount(client, gateway, world):
    """The 400 comes before authorization, so it can't reveal how much rolling budget is left."""
    world.set_rolling_limit(500000)
    for amount in (100000, 900000):
        bogus = held_proposal(counterparty_id="cp_nope", amount=Money(amount=amount, currency="USD"))
        assert propose(client, bogus).status_code == 400
    assert gateway.ledger.decisions(10) == []


def test_engine_not_ready_without_every_stage(world):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    stages = world.stages()
    stages.tier0 = None
    client = TestClient(create_app(Gateway(stages=stages, ledger=Ledger(connection)), TOKEN))
    response = propose(client, routine_proposal())
    assert response.status_code == 503 and "tier0" in response.json()["error"]["message"]


def test_rolling_limit_counts_earlier_payments(client, world):
    world.set_rolling_limit(300000)
    assert propose(client, routine_proposal()).json()["decision"] == "allow"
    assert propose(client, routine_proposal()).json()["decision"] == "block"


# --- S6: admin token, and no agent can approve ---


def test_agent_signed_resolve_of_its_own_challenge_is_refused_and_stays_held(client):
    held = hold(client)
    response = resolve(client, held["challenge_id"], headers={**ADMIN, **agent_headers()})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "agent_signed"
    assert client.get(f"/v1/decisions/{held['decision_id']}", headers=ADMIN).json()["execution"]["status"] == "held"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}])
def test_resolve_needs_the_admin_token(client, headers):
    held = hold(client)
    assert resolve(client, held["challenge_id"], headers=headers).status_code == 401


def test_admin_endpoints_are_off_without_a_token(gateway):
    client = TestClient(create_app(gateway, None))
    held = hold(client)
    assert resolve(client, held["challenge_id"]).status_code == 503


# --- S9: approve reruns the deterministic checks ---


def test_approve_with_nothing_changed_executes(client):
    held = hold(client)
    body = resolve(client, held["challenge_id"]).json()
    assert body["status"] == "executed" and body["reasons"] == []
    record = client.get(f"/v1/decisions/{held['decision_id']}", headers=ADMIN).json()
    assert record["execution"] == {"status": "executed", "simulated": True}
    assert record["review"]["outcome"] == "approved" and record["review"]["provenance"] == "admin_token"


def test_reject_blocks(client):
    held = hold(client)
    assert resolve(client, held["challenge_id"], "reject").json()["status"] == "blocked"


def test_revoking_the_authorization_while_held_blocks_on_approve(client, world):
    held = hold(client)
    world.authorization = world.authorization.model_copy(update={"status": "revoked", "version": 2})
    body = resolve(client, held["challenge_id"]).json()
    assert body == {**body, "status": "blocked", "reasons": ["resolve:state_changed"]}
    review = client.get(f"/v1/decisions/{held['decision_id']}", headers=ADMIN).json()["review"]
    assert "authorization:version" in review["changes"] and "authorization:status" in review["changes"]


def test_revoking_the_agent_while_held_blocks_on_approve(client, world):
    held = hold(client)
    world.agents[AGENT] = "revoked"
    assert resolve(client, held["challenge_id"]).json()["status"] == "blocked"


def test_changing_the_payment_method_while_held_blocks_on_approve(client, world):
    held = hold(client)
    world.change_payment_method()
    body = resolve(client, held["challenge_id"]).json()
    assert body["status"] == "blocked"


def test_held_payment_is_not_counted_against_its_own_rolling_limit(client, world):
    amount = held_proposal().amount.amount
    world.set_rolling_limit(amount)
    held = hold(client)
    assert resolve(client, held["challenge_id"]).json()["status"] == "executed"


def test_resolving_twice_is_409_and_unknown_is_404(client):
    held = hold(client)
    resolve(client, held["challenge_id"])
    assert resolve(client, held["challenge_id"]).status_code == 409
    assert resolve(client, "chl_nope").status_code == 404


def test_bad_resolution_body_is_400(client):
    held = hold(client)
    response = client.post(f"/v1/challenges/{held['challenge_id']}/resolve", json={"outcome": "maybe"}, headers=ADMIN)
    assert response.status_code == 400


def test_concurrent_proposals_cannot_both_fit_under_the_rolling_limit(gateway, world):
    from concurrent.futures import ThreadPoolExecutor

    from zeta_one.contracts import SignedRequest

    world.set_rolling_limit(300000)
    world.delay = 0.05
    body = routine_proposal().model_dump_json().encode()

    def send(_):
        request = SignedRequest(method="POST", path=PROPOSE, headers=agent_headers(), body=body)
        return gateway.propose(request)["decision"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = sorted(pool.map(send, range(2)))
    assert decisions == ["allow", "block"]


@pytest.mark.parametrize("path", ["/v1/decisions", "/v1/decisions/{id}"])
def test_reading_records_needs_the_admin_token_and_refuses_agents(client, path):
    """An agent gets only the decision and its ids (S4); it can't read back the record's signals."""
    body = propose(client, held_proposal()).json()
    url = path.format(id=body["decision_id"])
    assert client.get(url).status_code == 401
    assert client.get(url, headers=agent_headers()).status_code == 403
    assert client.get(url, headers={**ADMIN, **agent_headers()}).status_code == 403
    assert client.get(url, headers=ADMIN).status_code == 200


@pytest.mark.parametrize("method, path, status", [
    ("get", "/nope", 404),
    ("get", "/v1/decisions?limit=abc", 422),
    ("put", "/v1/health", 405),
])
def test_framework_errors_have_the_api_error_shape(client, method, path, status):
    response = getattr(client, method)(path, headers=ADMIN)
    assert response.status_code == status
    assert set(response.json()["error"]) == {"code", "message"}


def test_an_unexpected_crash_is_a_500_in_the_api_error_shape(gateway):
    def broken(request):
        raise RuntimeError("secret detail")

    gateway.propose = broken
    client = TestClient(create_app(gateway, TOKEN), raise_server_exceptions=False)
    response = propose(client, routine_proposal())
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "RuntimeError"}}
