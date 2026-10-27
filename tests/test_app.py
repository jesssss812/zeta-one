from fastapi.testclient import TestClient

from zeta_one.gateway.app import app
from zeta_one.gateway.scenarios import ORDER

client = TestClient(app)


def test_health_says_simulated():
    assert client.get("/v1/health").json()["simulated"] is True


def test_every_scenario_runs_and_its_decision_can_be_fetched():
    listed = [s["name"] for s in client.get("/v1/scenarios").json()]
    assert listed == ORDER
    for name in ORDER:
        body = client.post(f"/v1/scenarios/{name}/run").json()
        record = body["decision_record"]
        assert record["decision"] == body["scenario"]["expected"]
        assert record["execution"]["simulated"] is True
        assert client.get(f"/v1/decisions/{record['decision_id']}").json() == record


def test_unknown_scenario_is_404():
    response = client.post("/v1/scenarios/nope/run")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_scenario"
