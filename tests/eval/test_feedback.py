"""Verified outcomes become evaluation cases with their provenance; claims and sandbox runs don't."""

import sqlite3

from fastapi.testclient import TestClient

from eval import backends, feedback, run, sets
from tests.gateway.fakes import NOW, FakeWorld, held_proposal, routine_proposal
from tests.gateway.test_app import ADMIN, TOKEN, propose
from zeta_one.contracts import TierOutput, TierResult
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.service import Gateway


def _gateway():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    gateway = Gateway(stages=FakeWorld().stages(), ledger=Ledger(connection), clock=lambda: NOW)
    return connection, TestClient(create_app(gateway, TOKEN))


def _report(client, decision_id, finding, verification):
    body = {"finding": finding, "verification": verification, "by": "controller"}
    assert client.post(f"/v1/decisions/{decision_id}/outcomes", json=body, headers=ADMIN).status_code == 201


def test_only_verified_findings_become_cases_labelled_by_the_finding(tmp_path):
    connection, client = _gateway()
    fraud = propose(client, routine_proposal()).json()
    claim = propose(client, routine_proposal()).json()
    cleared = propose(client, held_proposal()).json()
    propose(client, routine_proposal())  # no outcome at all
    client.post("/v1/scenarios/routine_bill_payment/run", json={})  # sandbox run
    _report(client, fraud["decision_id"], "payee_fraud", "bank_confirmation")
    _report(client, claim["decision_id"], "payee_fraud", "customer_report")
    _report(client, cleared["decision_id"], "legitimate", "callback_known_number")

    cases = feedback.export(connection, data=tmp_path)
    by_id = {case.id: case for case in cases}
    assert set(by_id) == {f"feedback_{fraud['decision_id']}", f"feedback_{cleared['decision_id']}"}
    fraud_case = by_id[f"feedback_{fraud['decision_id']}"]
    assert (fraud_case.truth, fraud_case.expected, fraud_case.category) == ("payee_fraud", "block", "D")
    assert "bank_confirmation" in fraud_case.provenance and "allow" in fraud_case.provenance
    assert fraud_case.proposal == routine_proposal()
    assert [c.id for c in sets.load_set("feedback", tmp_path)] == [c.id for c in cases]


def test_feedback_cases_run_through_the_real_backend(tmp_path):
    connection, client = _gateway()
    allowed = propose(client, routine_proposal()).json()
    _report(client, allowed["decision_id"], "payee_fraud", "bank_confirmation")
    feedback.export(connection, data=tmp_path)

    class Echo:
        def __init__(self, name):
            self.name = name

        def assess(self, risk_input):
            return TierOutput(result=TierResult(tier=self.name, model="s", level=risk_input.tier0.level, confidence=0.99))

    rows = run.run_set("feedback", "engineered", backends.RealBackend(strong_tier=Echo("strong"), cheap_tier=Echo("cheap")),
                       data=tmp_path, results=tmp_path / "results")
    # The routine payment still looks routine on the seed, so the engine misses it: exactly what feedback is for.
    assert rows[0]["decision"] == "allow" and rows[0]["correct"] is False
