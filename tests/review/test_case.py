"""The case-review assistant (decision 0015) against a stubbed Anthropic client: code gathers, the web
call sees only public facts, the case file has no verdict, and nothing changes a decision."""

import json

import pytest
from anthropic.types import Message
from fastapi.testclient import TestClient

from tests.gateway.fakes import agent_headers, routine_proposal
from tests.gateway.test_app import ADMIN, client, gateway, propose, world  # noqa: F401  (fixtures)
from zeta_one.review import case as review

MODEL = review.MODEL


def message(text, stop="end_turn"):
    return Message.model_validate({
        "id": "msg", "type": "message", "role": "assistant", "model": MODEL, "stop_sequence": None,
        "content": [{"type": "text", "text": text}] if text is not None else [], "stop_reason": stop,
        "usage": {"input_tokens": 1000, "output_tokens": 200}})


RESEARCH = json.dumps({"official_domain": "vendor.example", "findings": [{"claim": "The vendor's site lists a different phone number.",
                                     "url": "https://vendor.example/contact"}], "summary": "Found the vendor."})


def case_file(**overrides):
    body = {"summary": "A routine payment was later disputed.", "timeline": [{"at": "2026-10-27", "event": "Paid"}],
            "verified_facts": [], "inferences": [], "contradictions": [], "open_questions": ["Who holds the account?"],
            "missing_evidence": [], "next_steps": ["Call the vendor on the number on file."]}
    body.update(overrides)
    return json.dumps(body)


class Stub:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def open_case(client, gateway, stub, decision_id):
    gateway.review_client = stub
    return client.post("/v1/cases", json={"decision_id": decision_id, "by": "case worker"}, headers=ADMIN)


def test_a_case_gathers_evidence_researches_public_facts_and_writes_a_file(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    stub = Stub(message(RESEARCH), message(case_file()))
    response = open_case(client, gateway, stub, allowed["decision_id"])
    assert response.status_code == 201
    case = response.json()
    assert case["errors"] == [] and case["case_file"]["summary"]
    assert case["evidence"]["decision"]["decision_id"] == allowed["decision_id"]
    assert [p["payment_id"] for p in case["evidence"]["payments_to_method"]]
    research_call, assembly_call = stub.calls
    sent = json.loads(research_call["messages"][0]["content"])
    assert set(sent) == {"vendor_names", "domains_on_invoice", "phones_on_invoice"}
    research_text = json.dumps(research_call)
    for private in (str(routine_proposal().amount.amount), routine_proposal().payment_method_id,
                    routine_proposal().counterparty_id, allowed["decision_id"], "biz_"):
        assert private not in research_text
    assert research_call["tools"] == [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]
    assert "tools" not in assembly_call
    assert client.get(f"/v1/cases/{case['case_id']}", headers=ADMIN).json()["case_id"] == case["case_id"]
    assert [c["case_id"] for c in client.get(f"/v1/decisions/{allowed['decision_id']}/cases", headers=ADMIN).json()] == [case["case_id"]]


def test_the_case_file_schema_has_no_verdict():
    fields = set(review.CaseFile.model_fields)
    assert not fields & {"verdict", "decision", "is_fraud", "recommended_decision", "recommendation"}


def test_web_findings_and_invoice_text_reach_the_assembly_only_as_untrusted_text(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    stub = Stub(message(RESEARCH), message(case_file()))
    open_case(client, gateway, stub, allowed["decision_id"])
    text = stub.calls[1]["messages"][0]["content"]
    facts, _, untrusted = text.partition("</gateway_facts>")
    assert "vendor.example" not in facts and "vendor.example" in untrusted
    assert 'field="web_findings"' in untrusted


def test_a_paused_research_turn_is_resumed(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    stub = Stub(message(None, stop="pause_turn"), message(RESEARCH), message(case_file()))
    case = open_case(client, gateway, stub, allowed["decision_id"]).json()
    assert case["research"]["findings"] and len(stub.calls) == 3


def test_a_verified_fact_without_a_known_source_becomes_an_inference(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    facts = [{"statement": "Paid before.", "sources": [allowed["decision_id"]]},
             {"statement": "The vendor was hacked.", "sources": ["https://made-up.example"]}]
    stub = Stub(message(RESEARCH), message(case_file(verified_facts=facts)))
    file = open_case(client, gateway, stub, allowed["decision_id"]).json()["case_file"]
    assert [f["statement"] for f in file["verified_facts"]] == ["Paid before."]
    assert file["inferences"][-1]["statement"] == "The vendor was hacked."


def test_research_failure_is_recorded_and_the_case_is_still_built(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    stub = Stub(TimeoutError("slow"), message(case_file()))
    case = open_case(client, gateway, stub, allowed["decision_id"]).json()
    assert case["errors"] == ["research: TimeoutError"] and case["case_file"] and case["research"] is None


@pytest.mark.parametrize("assembly", [message("not json"), message(case_file(), stop="max_tokens"), RuntimeError("down")])
def test_assembly_failure_keeps_the_evidence(client, gateway, assembly):
    allowed = propose(client, routine_proposal()).json()
    case = open_case(client, gateway, Stub(message(RESEARCH), assembly), allowed["decision_id"]).json()
    assert case["case_file"] is None and case["errors"][-1].startswith("assembly:") and case["evidence"]


def test_a_case_changes_no_decision_payment_or_risk(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    before = client.get(f"/v1/decisions/{allowed['decision_id']}", headers=ADMIN).json()
    open_case(client, gateway, Stub(message(RESEARCH), message(case_file())), allowed["decision_id"])
    assert client.get(f"/v1/decisions/{allowed['decision_id']}", headers=ADMIN).json() == before
    assert gateway.adjustments.all() == []


def test_only_a_person_with_the_admin_token_opens_or_reads_a_case(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    body = {"decision_id": allowed["decision_id"], "by": "x"}
    assert client.post("/v1/cases", json=body).status_code == 401
    assert client.post("/v1/cases", json=body, headers={**ADMIN, **agent_headers()}).status_code == 403
    assert client.get("/v1/cases/case_x").status_code == 401
    gateway.review_client = Stub()
    assert client.post("/v1/cases", json={"decision_id": "dec_nope", "by": "x"}, headers=ADMIN).status_code == 404


def test_the_review_page_holds_no_data_and_renders_text_as_text(client):
    page = client.get("/review")
    assert page.status_code == 200 and "Case review" in page.text
    assert "innerHTML" not in page.text and "textContent" in page.text


def test_research_reports_the_vendors_own_domain_and_refuses_a_malformed_one(client, gateway):
    allowed = propose(client, routine_proposal()).json()
    case = open_case(client, gateway, Stub(message(RESEARCH), message(case_file())), allowed["decision_id"]).json()
    assert case["research"]["official_domain"] == "vendor.example"
    bad = json.dumps({"official_domain": "javascript:alert(1)", "findings": [], "summary": "x"})
    case = open_case(client, gateway, Stub(message(bad), message(case_file())), allowed["decision_id"]).json()
    assert case["research"] is None and case["errors"] == ["research: invalid output"]
