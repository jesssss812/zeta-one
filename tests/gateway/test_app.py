"""The agent endpoint on fake stages: a minimal response (S4), decisions recorded in the ledger."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.gateway.fakes import NOW, FakeWorld, agent_headers, held_proposal, routine_proposal
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.service import Gateway

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
    return TestClient(create_app(gateway))


def propose(client, proposal, headers=None):
    return client.post(PROPOSE, content=proposal.model_dump_json(), headers=headers or agent_headers())


# --- S4: the agent learns only the decision and its ids ---


@pytest.mark.parametrize("make", [held_proposal, routine_proposal])
def test_propose_returns_exactly_decision_and_ids(client, make):
    body = propose(client, make()).json()
    assert set(body) == {"decision", "decision_id", "challenge_id"}


def test_routine_payment_is_allowed_and_executed_simulated(client):
    body = propose(client, routine_proposal()).json()
    assert body["decision"] == "allow" and body["challenge_id"] is None
    record = client.get(f"/v1/decisions/{body['decision_id']}").json()
    assert record["execution"] == {"status": "executed", "simulated": True}
    assert record["risk"]["tiers_run"] == ["tier0"]


def test_unsigned_request_is_blocked_and_recorded(client):
    body = client.post(PROPOSE, content=b"not even json").json()
    assert body["decision"] == "block"
    assert client.get(f"/v1/decisions/{body['decision_id']}").json()["reasons"] == ["identity:unsigned"]


def test_malformed_body_from_a_verified_agent_is_400(client):
    response = client.post(PROPOSE, content=b'{"amount": "lots"}', headers=agent_headers())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_proposal"
    assert client.get("/v1/decisions").json() == []


def test_unknown_counterparty_is_400(client):
    response = propose(client, held_proposal(counterparty_id="cp_nope"))
    assert response.status_code == 400


def test_engine_not_ready_without_every_stage(world):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    stages = world.stages()
    stages.tier0 = None
    client = TestClient(create_app(Gateway(stages=stages, ledger=Ledger(connection))))
    response = propose(client, routine_proposal())
    assert response.status_code == 503 and "tier0" in response.json()["error"]["message"]


def test_rolling_limit_counts_earlier_payments(client, world):
    world.set_rolling_limit(300000)
    assert propose(client, routine_proposal()).json()["decision"] == "allow"
    assert propose(client, routine_proposal()).json()["decision"] == "block"
