"""Workspace recipes execute the real deterministic gateway, without model calls."""
from fastapi.testclient import TestClient
from zeta_one.demo.app import DemoServer
from zeta_one.demo.workspace import Workspace, export_state


def test_export_real_recipe_decisions():
    state = export_state()
    assert state["mode"] == "rules"
    assert {p["recipe_id"]: p["record"]["decision"] for p in state["payments"]} == {
        "routine": "allow", "quarterly": "challenge", "bank-change": "challenge",
        "invoice-redirection": "challenge", "over-limit": "block", "blocked-destination": "block"}
    for payment in state["payments"]:
        assert payment["record"]["execution"]["simulated"]
        assert payment["summary"]["models"] == []
        assert payment["record"]["latency_ms"]["total"] is not None


def test_outcome_repeat_resolve_and_reset():
    workspace = Workspace()
    try:
        assert workspace.state()["payments"] == []
        state = workspace.act("add", {"recipe_id": "routine"})
        payment = state["selected_id"]
        workspace.act("outcome", {"id": payment, "finding": "payee_fraud", "verification": "customer_report"})
        assert workspace.act("repeat", {"id": payment})["payments"][-1]["record"]["decision"] != "block"
        workspace.act("outcome", {"id": payment, "finding": "payee_fraud", "verification": "bank_confirmation"})
        assert workspace.act("repeat", {"id": payment})["payments"][-1]["record"]["decision"] == "block"
        state = workspace.act("add", {"recipe_id": "bank-change"})
        held = state["selected_id"]
        state = workspace.act("resolve", {"id": held, "outcome": "approve", "finding": "legitimate", "verification": "callback_known_number"})
        assert next(p for p in state["payments"] if p["id"] == held)["summary"]["status"] == "executed"
        state = workspace.act("assemble", {"id": held})
        case = next(p for p in state["payments"] if p["id"] == held)["case_file"]
        assert case["evidence"] and case["errors"] and case["case_file"] is None
        assert workspace.act("reset")["payments"] == []
    finally:
        workspace.close()


def test_workspace_http_and_legacy_demo():
    server = DemoServer()
    client = TestClient(server)
    try:
        assert client.get("/v1/workspace").json()["payments"] == []
        assert client.get("/workspace/config.json").json()["mode"] == "rules"
        assert client.get("/workspace/config.json").json()["explanation_url"] == "/about/"
        assert client.get("/about/").status_code == 200
        for path in ("/about/workspace", "/about/workspace/"):
            assert client.get(path, follow_redirects=False).headers["location"] == "/workspace/"
        assert client.get("/", follow_redirects=False).headers["location"] == "/workspace/"
        assert client.post("/v1/workspace/add", data='{}').status_code == 415
        assert client.post("/v1/workspace/add", json={"recipe_id": "missing"}).status_code == 400
        assert client.post("/v1/workspace/add", json={"recipe_id": "routine", "seed": 42}).status_code == 200
        assert client.post("/v1/workspace/add", json=[]).status_code == 400
        assert client.post("/v1/workspace/add", json={"recipe_id": "routine", "seed": True}).status_code == 400
        assert client.post("/v1/workspace/outcome", json={"id": "missing"}).status_code == 400
        assert client.post("/v1/workspace/assemble", content="{", headers={"Content-Type": "application/json"}).status_code == 400
        assert client.get("/demo").status_code == 200
        assert client.get("/v1/demo").json()["steps"] == []
    finally:
        server.workspace.close()
        server.story.close()
