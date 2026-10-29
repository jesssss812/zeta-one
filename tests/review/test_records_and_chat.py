"""Every id the case review shows resolves to its record and source; the case chat answers from the
case only, on a local model or a keyed remote server, and is kept with the case."""

import json
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.review.test_case import RESEARCH, Stub, case_file, message
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture
from zeta_one.gateway.service import Gateway
from zeta_one.gateway.wiring import real_stages
from zeta_one.review import case as review
from zeta_one.review import chat
from zeta_one.review.chat import CaseChat
from zeta_one.rho.seed import SEED_NOW

TOKEN = "test-admin-token"
ADMIN = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def world():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    gateway = Gateway(stages=real_stages(connection), ledger=Ledger(connection), clock=lambda: SEED_NOW)
    return TestClient(create_app(gateway, TOKEN)), gateway


@pytest.mark.parametrize("record_id, system, production", [
    ("bill_0201", "Rho", "GET /ap/bills/{bill_id}"),
    ("cp_0012", "Rho", "GET /ap/counterparties/{counterparty_id}"),
    ("pm_0012_01", "Rho", "part of GET /ap/counterparties"),
    ("pmh_0042", "Rho", "not in Rho's confirmed API"),
    ("acct_seed_checking_01", "Rho", "GET /accounts/{account_id}"),
])
def test_seed_records_resolve_with_their_source(world, record_id, system, production):
    client, _ = world
    found = client.get(f"/v1/records/{record_id}", headers=ADMIN).json()
    assert found["id"] == record_id and system in found["source"]["system"]
    assert found["source"]["production"].startswith(production) and found["record"]


def test_ledger_records_resolve(world):
    client, gateway = world
    record = load_fixture("routine_bill_payment").decision_record.model_copy(update={"decision_id": "dec_x"})
    gateway.ledger.record(record, load_fixture("routine_bill_payment").proposal)
    payment = gateway.ledger.connection.execute("SELECT payment_id FROM payments").fetchone()[0]
    assert client.get("/v1/records/dec_x", headers=ADMIN).json()["source"]["collection"] == "decisions"
    assert client.get(f"/v1/records/{payment}", headers=ADMIN).json()["record"]["decision_id"] == "dec_x"


def test_unknown_records_and_no_token_are_refused(world):
    client, _ = world
    assert client.get("/v1/records/bill_nope", headers=ADMIN).status_code == 404
    assert client.get("/v1/records/whatever", headers=ADMIN).status_code == 404
    assert client.get("/v1/records/bill_0201").status_code == 401


def test_a_web_finding_must_be_a_web_address():
    with pytest.raises(Exception):
        review.Finding(claim="x", url="javascript:alert(1)")
    assert review.Finding(claim="x", url="https://vendor.example/a").url


# --- chat --------------------------------------------------------------------------------------


def _case(world):
    client, gateway = world
    fixture = load_fixture("routine_bill_payment")
    record = fixture.decision_record.model_copy(update={"decision_id": "dec_chat", "proposal": fixture.proposal,
                                                        "context": fixture.context})
    gateway.ledger.record(record, fixture.proposal)
    gateway.review_client = Stub(message(RESEARCH), message(case_file()))
    return client.post("/v1/cases", json={"decision_id": "dec_chat", "by": "cw"}, headers=ADMIN).json()


class Server:
    def __init__(self, answer=None, error=None, status=200, finish="stop"):
        self.answer, self.error, self.status, self.finish, self.calls = answer, error, status, finish, []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        if self.error:
            raise self.error
        return self.status, {"choices": [{"finish_reason": self.finish, "message": {"content": self.answer}}]}


def test_the_chat_answers_from_the_case_and_checks_what_it_cites(world):
    client, gateway = world
    case = _case(world)
    server = Server(answer="The payment dec_chat went to the usual method; see also bill_madeup.")
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    reply = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "Was the method new?", "by": "cw"},
                        headers=ADMIN).json()
    assert reply["cited"] == ["dec_chat"] and reply["not_in_case"] == ["bill_madeup"]
    url, headers, body = server.calls[0]
    assert url == "http://127.0.0.1:11434/v1/chat/completions" and headers == {}
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert reply["location"] == "local" and "address on this machine" in reply["note"]
    system, context, question = body["messages"][0], body["messages"][1], body["messages"][-1]
    assert "Never say whether the payment was fraud" in system["content"]
    assert "<gateway_facts>" in context["content"] and "untrusted_data boundary=" in context["content"]
    assert question == {"role": "user", "content": "Was the method new?"}
    history = client.get(f"/v1/cases/{case['case_id']}/chat", headers=ADMIN).json()
    assert [turn["question"] for turn in history] == ["Was the method new?"]


def test_earlier_turns_are_sent_as_history(world):
    client, gateway = world
    case = _case(world)
    server = Server(answer="ok")
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    for q in ("first?", "second?"):
        client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": q, "by": "cw"}, headers=ADMIN)
    roles = [m["role"] for m in server.calls[1][2]["messages"]]
    assert roles == ["system", "user", "user", "assistant", "user"]


@pytest.mark.parametrize("server, words", [
    (Server(error=httpx.ConnectError("refused")), "ollama serve"),
    (Server(status=404), "pulled"),
])
def test_an_unreachable_local_model_says_how_to_start_it(world, server, words):
    client, gateway = world
    case = _case(world)
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    response = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "hi", "by": "cw"}, headers=ADMIN)
    assert response.status_code == 503 and words in response.json()["error"]["message"]


@pytest.mark.parametrize("server, words", [
    (Server(answer="The payment dec_chat went to", finish="length"), "cut off (length)"),
    (Server(answer=None), "had no text"),
    (Server(answer="  "), "had no text"),
])
def test_a_cut_off_or_empty_answer_is_unavailable_and_not_kept(world, server, words):
    client, gateway = world
    case = _case(world)
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    response = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "hi", "by": "cw"}, headers=ADMIN)
    assert response.status_code == 503 and words in response.json()["error"]["message"]
    assert client.get(f"/v1/cases/{case['case_id']}/chat", headers=ADMIN).json() == []


REMOTE = "https://pod-8000.proxy.example.test/v1"


def test_a_remote_server_gets_the_key_and_the_reply_says_where_it_ran(world, monkeypatch):
    client, gateway = world
    case = _case(world)
    monkeypatch.setenv("CHAT_BASE_URL", REMOTE)
    monkeypatch.setenv("CHAT_MODEL", "qwen3.6-27b")
    monkeypatch.setenv("CHAT_API_KEY", "test-chat-key")
    server = Server(answer="The payment dec_chat went to the usual method; see also bill_madeup.")
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    reply = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "Was the method new?", "by": "cw"},
                        headers=ADMIN).json()
    url, headers, body = server.calls[0]
    assert url == REMOTE + "/chat/completions" and headers == {"Authorization": "Bearer test-chat-key"}
    assert body["model"] == "qwen3.6-27b" and body["chat_template_kwargs"] == {"enable_thinking": False}
    assert "Never say whether the payment was fraud" in body["messages"][0]["content"]
    assert reply["cited"] == ["dec_chat"] and reply["not_in_case"] == ["bill_madeup"]
    assert reply["location"] == "remote" and "remote server, not this machine" in reply["note"] and "test-chat-key" not in json.dumps(reply)
    history = client.get(f"/v1/cases/{case['case_id']}/chat", headers=ADMIN).json()
    assert [turn["question"] for turn in history] == ["Was the method new?"]


@pytest.mark.parametrize("server, words", [
    (Server(error=httpx.ConnectError("refused")), "isn't running"),
    (Server(status=401), "check CHAT_API_KEY"),
    (Server(error=httpx.ReadTimeout("slow")), "timed out"),
    (Server(error=httpx.RemoteProtocolError("closed mid-answer")), "failed (RemoteProtocolError)"),
    (Server(error=httpx.ProxyError("bad proxy")), "failed (ProxyError)"),
])
def test_a_failing_remote_server_says_what_failed_without_the_key(world, monkeypatch, server, words):
    client, gateway = world
    case = _case(world)
    monkeypatch.setenv("CHAT_BASE_URL", REMOTE)
    monkeypatch.setenv("CHAT_API_KEY", "test-chat-key")
    gateway.chat = CaseChat(gateway.ledger.connection, post=server)
    response = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "hi", "by": "cw"}, headers=ADMIN)
    message = response.json()["error"]["message"]
    assert response.status_code == 503 and words in message
    assert "ollama" not in message and "test-chat-key" not in message
    assert client.get(f"/v1/cases/{case['case_id']}/chat", headers=ADMIN).json() == []


def test_each_answer_keeps_the_model_and_where_it_ran(world, monkeypatch):
    client, gateway = world
    case = _case(world)
    gateway.chat = CaseChat(gateway.ledger.connection, post=Server(answer="first"))
    client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "here?", "by": "cw"}, headers=ADMIN)
    monkeypatch.setenv("CHAT_BASE_URL", REMOTE)
    monkeypatch.setenv("CHAT_MODEL", "qwen3.6-27b")
    gateway.chat = CaseChat(gateway.ledger.connection, post=Server(answer="second"))
    client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "there?", "by": "cw"}, headers=ADMIN)
    history = client.get(f"/v1/cases/{case['case_id']}/chat", headers=ADMIN).json()
    assert [(t["model"], t["location"]) for t in history] == [("qwen2.5:7b", "local"), ("qwen3.6-27b", "remote")]
    assert "address on this machine" in history[0]["note"] and "not this machine" in history[1]["note"]


def test_answers_kept_before_the_model_was_recorded_have_no_note():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE case_messages (message_id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,"
                       " at TEXT NOT NULL, by TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)")
    connection.execute("INSERT INTO case_messages (case_id, at, by, question, answer) VALUES ('c', 't', 'cw', 'q', 'a')")
    [turn] = CaseChat(connection, post=Server()).history("c")
    assert (turn["answer"], turn["model"], turn["location"], turn["note"]) == ("a", None, None, None)


@pytest.mark.parametrize("base_url, local", [
    ("http://127.0.0.1:11434/v1", True), ("http://127.0.0.2:8000/v1", True), ("http://localhost:11434/v1", True),
    ("http://[::1]:11434/v1", True), ("http://0.0.0.0:11434/v1", True), (REMOTE, False), ("http://10.0.0.5/v1", False),
])
def test_local_means_an_address_on_this_machine(monkeypatch, base_url, local):
    monkeypatch.setenv("CHAT_BASE_URL", base_url)
    assert CaseChat(sqlite3.connect(":memory:"), post=Server()).local is local


class Httpx:
    """Stands in for httpx.post, below the chat's own HTTP helper."""

    def __init__(self, response):
        self.response, self.calls = response, []

    def __call__(self, url, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.response


ANSWER = {"choices": [{"finish_reason": "stop", "message": {"content": "See dec_chat."}}]}


def _ask_through_httpx(world, monkeypatch, response):
    client, gateway = world
    case = _case(world)
    fake = Httpx(response)
    monkeypatch.setattr(chat.httpx, "post", fake)
    gateway.chat = CaseChat(gateway.ledger.connection)
    reply = client.post(f"/v1/cases/{case['case_id']}/chat", json={"question": "hi", "by": "cw"}, headers=ADMIN)
    return reply, fake.calls


def test_a_local_server_gets_no_key_and_the_longer_timeout(world, monkeypatch):
    reply, calls = _ask_through_httpx(world, monkeypatch, httpx.Response(200, json=ANSWER))
    assert reply.status_code == 200 and reply.json()["cited"] == ["dec_chat"]
    assert calls[0]["headers"] == {} and calls[0]["timeout"] == chat.LOCAL_TIMEOUT_SECONDS
    assert calls[0]["json"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_a_remote_server_gets_the_key_and_gives_up_sooner(world, monkeypatch):
    monkeypatch.setenv("CHAT_BASE_URL", REMOTE)
    monkeypatch.setenv("CHAT_API_KEY", "test-chat-key")
    reply, calls = _ask_through_httpx(world, monkeypatch, httpx.Response(200, json=ANSWER))
    assert reply.status_code == 200 and calls[0]["url"] == REMOTE + "/chat/completions"
    assert calls[0]["headers"] == {"Authorization": "Bearer test-chat-key"}
    assert calls[0]["timeout"] == chat.REMOTE_TIMEOUT_SECONDS < chat.LOCAL_TIMEOUT_SECONDS


@pytest.mark.parametrize("status, words", [(502, "HTTP 502"), (200, "had no text")])
def test_a_reply_that_is_not_json_is_unavailable(world, monkeypatch, status, words):
    reply, _ = _ask_through_httpx(world, monkeypatch, httpx.Response(status, text="<html>Bad gateway</html>"))
    assert reply.status_code == 503 and words in reply.json()["error"]["message"]


def test_the_chat_needs_the_token_and_a_known_case(world):
    client, _ = world
    assert client.post("/v1/cases/case_x/chat", json={"question": "q", "by": "b"}).status_code == 401
    assert client.post("/v1/cases/case_x/chat", json={"question": "q", "by": "b"}, headers=ADMIN).status_code == 404
    assert client.post("/v1/cases/case_x/chat", json={"question": "", "by": "b"}, headers=ADMIN).status_code == 400
