"""The admin token's sources, and every branch of the recheck before a held payment executes (S6, S9)."""

import dataclasses
import sqlite3

import pytest

from tests.gateway.fakes import AGENT, NOW, FakeWorld, agent_headers, held_proposal
from zeta_one.contracts import IdentityEvidence, InvalidProposal, SignedRequest
from zeta_one.gateway import admin
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.recheck import recheck
from zeta_one.gateway.service import Gateway

# --- admin_token -----------------------------------------------------------------------------------


@pytest.fixture
def no_env_token(monkeypatch):
    monkeypatch.delenv(admin.TOKEN_NAME, raising=False)


def test_the_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(f"{admin.TOKEN_NAME}=from-file\n")
    monkeypatch.setenv(admin.TOKEN_NAME, "from-environment")
    assert admin.admin_token(env) == "from-environment"


@pytest.mark.parametrize("line, token", [
    ("ZETA_ADMIN_TOKEN=plain", "plain"),
    ("ZETA_ADMIN_TOKEN = spaced ", "spaced"),
    ("ZETA_ADMIN_TOKEN=\"double\"", "double"),
    ("ZETA_ADMIN_TOKEN='single'", "single"),
    ("ZETA_ADMIN_TOKEN=", None),
    ("OTHER=value", None),
])
def test_the_env_file_is_parsed(tmp_path, no_env_token, line, token):
    env = tmp_path / ".env"
    env.write_text(f"# comment\n{line}\n")
    assert admin.admin_token(env) == token


def test_no_env_file_means_no_token(tmp_path, no_env_token):
    assert admin.admin_token(tmp_path / "missing.env") is None


def test_without_a_token_admin_actions_are_disabled():
    with pytest.raises(admin.AdminRefused) as refused:
        admin.require_admin({"authorization": "Bearer anything"}, None)
    assert refused.value.status == 503


@pytest.mark.parametrize("header", ["Bearer wrong", "Basic right", "right", ""])
def test_a_wrong_or_malformed_token_is_refused(header):
    with pytest.raises(admin.AdminRefused) as refused:
        admin.require_admin({"authorization": header}, "right")
    assert refused.value.status == 401


# --- recheck ---------------------------------------------------------------------------------------


@pytest.fixture
def world() -> FakeWorld:
    return FakeWorld()


@pytest.fixture
def held(world):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    gateway = Gateway(stages=world.stages(), ledger=Ledger(connection), clock=lambda: NOW)
    body = held_proposal().model_dump_json().encode()
    response = gateway.propose(SignedRequest(method="POST", path="/v1/actions/propose_payment",
                                             headers=agent_headers(), body=body))
    payment = gateway.ledger.held(response["challenge_id"])
    identity = IdentityEvidence.model_validate(gateway.ledger.decision(payment.decision_id)["identity"])
    return gateway, payment, identity


def _recheck(held, stages=None):
    gateway, payment, identity = held
    return recheck(payment, identity, stages or gateway.stages, gateway.ledger, NOW)


def test_nothing_changed_means_no_changes(held):
    assert _recheck(held) == []


def test_a_revoked_agent_is_a_change(held, world):
    world.agents[AGENT] = "revoked"
    assert _recheck(held) == ["agent:revoked"]


def test_an_unknown_agent_status_is_unverifiable(held):
    stages = dataclasses.replace(held[0].stages, agent_status=None)
    assert "agent:unverifiable" in _recheck(held, stages)


def test_a_missing_authorization_stage_is_unverifiable(held):
    stages = dataclasses.replace(held[0].stages, load_authorization=None)
    assert "authorization:unverifiable" in _recheck(held, stages)


def test_a_new_authorization_version_is_a_change(held, world):
    world.authorization = world.authorization.model_copy(update={"version": world.authorization.version + 1})
    assert "authorization:version" in _recheck(held)


def test_a_changed_payment_method_is_named(held, world):
    world.change_payment_method()
    assert _recheck(held) == ["payment_method:changed"]


def test_a_held_payment_with_no_recorded_method_state_is_unverifiable(held):
    gateway, payment, identity = held
    stripped = dataclasses.replace(payment, payment_method_state=None)
    assert recheck(stripped, identity, gateway.stages, gateway.ledger, NOW) == ["payment_method:unverifiable"]


def test_a_payee_that_no_longer_resolves_is_invalid(held):
    def gone(*args):
        raise InvalidProposal("unknown counterparty")

    stages = dataclasses.replace(held[0].stages, load_context=gone)
    assert _recheck(held, stages) == ["payment_method:invalid"]
