"""Decision retrieval keeps the action and source facts as they were when assessed."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.gateway.fakes import NOW, FakeWorld, agent_headers, held_proposal
from zeta_one.contracts import SignedRequest
from zeta_one.gateway.app import create_app
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.service import Gateway

PATH = "/v1/actions/propose_payment"
ADMIN = {"Authorization": "Bearer test-admin-token"}


@pytest.fixture
def setup():
    world = FakeWorld()
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    gateway = Gateway(world.stages(), Ledger(connection), clock=lambda: NOW)
    with TestClient(create_app(gateway, "test-admin-token")) as client:
        yield world, gateway, client
    connection.close()


@pytest.mark.parametrize("blocked", [False, True])
def test_admin_reads_original_action_and_context_after_source_changes(setup, blocked):
    world, gateway, client = setup
    proposal = held_proposal(memo="October supplies")
    if blocked:
        world.authorization.status = "revoked"
    submitted = client.post(PATH, content=proposal.model_dump_json(), headers=agent_headers()).json()
    assert submitted["decision"] == ("block" if blocked else "challenge")
    assert set(submitted) == {"decision", "decision_id", "challenge_id"}
    before = client.get(f"/v1/decisions/{submitted['decision_id']}", headers=ADMIN).json()
    assert before["proposal"]["amount"] == {"amount": 251500, "currency": "USD"}
    assert before["proposal"]["memo"] == "October supplies"
    assert before["context"]["counterparty"]["id"] == "cp_0007"
    assert before["context"]["bill"]["id"] == "bill_0193"
    assert before["context"]["bill"]["document_excerpt"]
    world.contexts["cp_0007"].bill.document_excerpt = "Changed after decision"
    world.change_payment_method()
    proposal.memo = "Changed after submission"
    # Reopen the reader on persisted storage, independent of the captured stage objects.
    reopened = Ledger(gateway.ledger._db)
    assert reopened.decision(submitted["decision_id"])["context"] == before["context"]
    listed = client.get("/v1/decisions", headers=ADMIN).json()[0]
    assert listed["proposal"] == before["proposal"]
    assert listed["context"] == before["context"]


@pytest.mark.parametrize("body, has_proposal", [(b"not json", False), (held_proposal().model_dump_json().encode(), True)])
def test_identity_block_keeps_parseable_claim_but_never_loads_context(setup, body, has_proposal):
    world, gateway, client = setup
    def unexpected(*args):
        pytest.fail("an unsigned request must not load business context")
    gateway.engine.load_context = unexpected
    response = client.post(PATH, content=body).json()
    record = client.get(f"/v1/decisions/{response['decision_id']}", headers=ADMIN).json()
    assert record["decision"] == "block" and record["identity"]["result"] == "unsigned"
    assert (record["proposal"] is not None) is has_proposal
    assert record["context"] is None
    assert record["authorization"]["snapshot"] is None


def test_failed_context_keeps_action_and_marks_context_unavailable(setup):
    _, gateway, client = setup
    def unavailable(*args):
        raise OSError("store unavailable")
    gateway.engine.load_context = unavailable
    response = client.post(PATH, content=held_proposal().model_dump_json(), headers=agent_headers()).json()
    record = client.get(f"/v1/decisions/{response['decision_id']}", headers=ADMIN).json()
    assert record["decision"] == "challenge"
    assert record["proposal"]["amount"]["amount"] == 251500
    assert record["context"] is None


def test_engine_snapshot_does_not_alias_mutable_context(setup):
    world, gateway, _ = setup
    original = world.contexts["cp_0007"]
    gateway.engine.load_context = lambda *_: original
    request = SignedRequest(method="POST", path=PATH, headers=agent_headers(), body=held_proposal().model_dump_json().encode())
    record, proposal = gateway.engine.evaluate(request)
    original.counterparty.name = "Changed later"
    proposal.memo = "Changed later"
    assert record.context.counterparty.name == "Harbor Office Supply Co."
    assert record.proposal.memo != "Changed later"
