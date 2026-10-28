import sqlite3

import pytest
from fastapi.testclient import TestClient

from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import ORDER, load_fixture
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


def test_each_scenario_run_is_a_new_decision(client):
    first = client.post("/v1/scenarios/routine_bill_payment/run").json()["decision_record"]
    second = client.post("/v1/scenarios/routine_bill_payment/run").json()["decision_record"]
    assert first["decision_id"] != second["decision_id"]
    fixture = load_fixture("routine_bill_payment").decision_record
    assert fixture.decision_id not in (first["decision_id"], second["decision_id"])
    assert first["created_at"] != fixture.created_at.isoformat().replace("+00:00", "Z")
    assert len(client.get("/v1/decisions", headers=ADMIN).json()) == 2


def test_importing_the_app_module_opens_no_database_or_env():
    import subprocess
    import sys

    probe = (
        "import zeta_one.db as db, zeta_one.gateway.admin as admin\n"
        "db.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('db opened'))\n"
        "admin.admin_token = lambda *a, **k: (_ for _ in ()).throw(AssertionError('.env read'))\n"
        "import zeta_one.gateway.app as app_module\n"
        "assert app_module._app is None\n"
    )
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_the_latest_evaluation_report_is_served(tmp_path):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    report = tmp_path / "report.json"
    app = create_app(Gateway(stages=real_stages(), ledger=Ledger(connection)), TOKEN, eval_report=report)
    client = TestClient(app)
    assert client.get("/v1/eval/latest").json()["error"]["code"] == "no_report"
    report.write_text('{"sets": {}}')
    assert client.get("/v1/eval/latest").json() == {"sets": {}}
