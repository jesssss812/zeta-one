"""The one-screen demo: steps, reset, the sandbox's review page, and no paid call unless started live."""

from fastapi.testclient import TestClient

from zeta_one.demo.app import DemoServer
from zeta_one.demo.story import TITLES

JSON = {"Content-Type": "application/json"}


def test_the_demo_steps_through_the_story_and_resets():
    server = DemoServer()
    client = TestClient(server)
    assert client.get("/demo").status_code == 200
    state = client.get("/v1/demo").json()
    assert state["titles"] == list(TITLES) and state["steps"] == [] and state["simulated"] and not state["live_models"]
    first = client.post("/v1/demo/next", headers=JSON, content="{}").json()["steps"][0]
    assert first["summary"]["headline"].startswith("Agent verified") and first["summary"]["decision"] == "allow"
    for _ in TITLES[1:]:
        state = client.post("/v1/demo/next", headers=JSON, content="{}").json()
    assert state["done"] and len(state["steps"]) == len(TITLES)
    assert client.post("/v1/demo/next", headers=JSON, content="{}").json()["steps"] == state["steps"]
    assert client.post("/v1/demo/reset", headers=JSON, content="{}").json()["steps"] == []


def test_the_root_opens_the_workspace():
    response = TestClient(DemoServer()).get("/", follow_redirects=False)
    assert response.status_code in (302, 307) and response.headers["location"] == "/workspace/"


def test_steps_need_a_json_request_so_another_site_cant_drive_them():
    client = TestClient(DemoServer())
    assert client.post("/v1/demo/next").status_code == 415
    assert client.post("/v1/demo/reset", content="x", headers={"Content-Type": "text/plain"}).status_code == 415


def test_the_review_page_and_inbox_serve_the_sandbox_with_the_demo_token_only():
    server = DemoServer()
    client = TestClient(server)
    client.post("/v1/demo/next", headers=JSON, content="{}")
    assert client.get("/review").status_code == 200
    assert client.get("/v1/inbox").status_code == 401
    rows = client.get("/v1/inbox", headers={"Authorization": f"Bearer {server.token}"}).json()
    assert [row["vendor"] for row in rows] == ["Cedar Ridge Cleaning Services"]


def test_with_models_off_a_case_shows_the_evidence_and_makes_no_model_call():
    server = DemoServer()
    client = TestClient(server)
    state = client.post("/v1/demo/next", headers=JSON, content="{}").json()
    decision_id = state["steps"][0]["decision"]["decision_id"]
    case = client.post("/v1/cases", headers={"Authorization": f"Bearer {server.token}"},
                       json={"decision_id": decision_id, "by": "demo"}).json()
    assert any("ModelsOff" in error for error in case["errors"]) and case["evidence"]["decision"]["decision_id"] == decision_id
