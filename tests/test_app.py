import sqlite3

import pytest
from fastapi.testclient import TestClient

from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import ORDER
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import real_stages

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client() -> TestClient:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return TestClient(create_app(Gateway(stages=real_stages(), ledger=Ledger(connection)), TOKEN))


def test_health_says_simulated(client):
    assert client.get("/v1/health").json()["simulated"] is True


def test_every_scenario_runs_and_its_decision_can_be_fetched(client):
    listed = [s["name"] for s in client.get("/v1/scenarios").json()]
    assert listed == ORDER
    for name in ORDER:
        body = client.post(f"/v1/scenarios/{name}/run").json()
        record = body["decision_record"]
        assert record["decision"] == body["scenario"]["expected"]
        assert record["execution"]["simulated"] is True
        assert client.get(f"/v1/decisions/{record['decision_id']}", headers=ADMIN).json() == record


def test_unknown_scenario_is_404(client):
    response = client.post("/v1/scenarios/nope/run")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_scenario"
