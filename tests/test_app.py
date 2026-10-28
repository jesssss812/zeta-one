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
    return TestClient(create_app(Gateway(stages=real_stages(connection), ledger=Ledger(connection)), TOKEN))


def test_health_says_simulated(client):
    assert client.get("/v1/health").json()["simulated"] is True


def test_every_scenario_runs_and_its_decision_can_be_fetched(client):
    listed = [s["name"] for s in client.get("/v1/scenarios").json()]
    assert listed == ORDER
    for name in ORDER:
        body = client.post(f"/v1/scenarios/{name}/run", json={}).json()
        record = body["decision_record"]
        assert record["decision"] == body["scenario"]["expected"]
        assert record["execution"]["simulated"] is True
        assert client.get(f"/v1/decisions/{record['decision_id']}", headers=ADMIN).json() == record


def test_unknown_scenario_is_404(client):
    response = client.post("/v1/scenarios/nope/run", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_scenario"


def test_each_scenario_run_is_a_new_decision(client):
    first = client.post("/v1/scenarios/routine_bill_payment/run", json={}).json()["decision_record"]
    second = client.post("/v1/scenarios/routine_bill_payment/run", json={}).json()["decision_record"]
    assert first["decision_id"] != second["decision_id"]
    fixture = load_fixture("routine_bill_payment").decision_record
    assert fixture.decision_id not in (first["decision_id"], second["decision_id"])
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
    app = create_app(Gateway(stages=real_stages(connection), ledger=Ledger(connection)), TOKEN, eval_report=report)
    client = TestClient(app)
    assert client.get("/v1/eval/latest").json()["error"]["code"] == "no_report"
    report.write_text('{"sets": {}}')
    assert client.get("/v1/eval/latest").json() == {"sets": {}}


@pytest.mark.parametrize("name", ORDER)
def test_scenarios_run_on_the_real_stages(client, name):
    body = client.post(f"/v1/scenarios/{name}/run", json={}).json()
    record = body["decision_record"]
    fixture = load_fixture(name)
    assert record["decision"] == fixture.scenario.expected
    assert record["reasons"] == fixture.decision_record.reasons
    assert record["seed_version"]
    if "strong" in record["risk"]["tiers_run"]:
        assert body["illustrative"] is True and body["replayed_stages"] == ["strong"]
    else:
        assert body["illustrative"] is False and body["replayed_stages"] == []


def test_the_live_endpoint_decides_a_signed_demo_agent_request_on_the_real_stages(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    from zeta_one.gateway.wiring import register_demo_agents
    from zeta_one.identity.signing import sign
    from zeta_one.rho.seed import SEED_NOW

    key = Ed25519PrivateKey.generate()
    (tmp_path / "ap_assistant.pem").write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    stages = real_stages(connection)
    register_demo_agents(stages, tmp_path, SEED_NOW)
    client = TestClient(create_app(Gateway(stages=stages, ledger=Ledger(connection), clock=lambda: SEED_NOW), TOKEN))
    body = load_fixture("routine_bill_payment").proposal.model_dump_json().encode()
    path = "/v1/actions/propose_payment"
    headers = sign(key, "agent_ap_assistant_01", "POST", path, body, SEED_NOW)
    response = client.post(path, content=body, headers=headers)
    assert response.status_code == 200
    answer = response.json()
    assert set(answer) == {"decision", "decision_id", "challenge_id"} and answer["decision"] == "allow"
    record = client.get(f"/v1/decisions/{answer['decision_id']}", headers=ADMIN).json()
    assert record["identity"]["result"] == "verified" and record["execution"]["status"] == "executed"
    replayed = client.post(path, content=body, headers=headers).json()
    assert client.get(f"/v1/decisions/{replayed['decision_id']}", headers=ADMIN).json()["reasons"] == ["identity:replay"]


def test_a_scenario_run_needs_a_json_request_so_other_sites_cannot_trigger_it(client):
    response = client.post("/v1/scenarios/routine_bill_payment/run", content=b"", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    assert client.get("/v1/decisions", headers=ADMIN).json() == []


def test_a_scenario_record_says_it_is_a_sandbox_run(client):
    record = client.post("/v1/scenarios/routine_bill_payment/run", json={}).json()["decision_record"]
    assert record["sandbox"] == {"scenario": "routine_bill_payment"}
    assert client.get("/v1/decisions", headers=ADMIN).json()[0]["sandbox"] == {"scenario": "routine_bill_payment"}
