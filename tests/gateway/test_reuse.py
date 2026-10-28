"""S3: the same proposal within 24 hours reuses the earlier risk result, so it can't be re-rolled."""

import sqlite3
from datetime import timedelta

import pytest

from tests.gateway.fakes import NOW, FakeWorld, agent_headers, held_proposal, routine_proposal
from zeta_one.contracts import Feature, Money, SignedRequest
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.reuse import MAX_FRESH_ASSESSMENTS, RiskReuse, fingerprint
from zeta_one.gateway.service import Gateway


class Clock:
    def __init__(self):
        self.now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def world() -> FakeWorld:
    return FakeWorld()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def gateway(world, clock) -> Gateway:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return Gateway(stages=world.stages(), ledger=Ledger(connection), reuse=RiskReuse(connection), clock=clock)


def send(gateway, proposal) -> dict:
    response = gateway.propose(
        SignedRequest(method="POST", path="/v1/actions/propose_payment", headers=agent_headers(), body=proposal.model_dump_json().encode())
    )
    return gateway.ledger.decision(response["decision_id"])


def test_same_adversarial_proposal_five_times_gets_one_model_call_and_one_decision(gateway, world, clock):
    records = []
    for _ in range(5):
        records.append(send(gateway, held_proposal()))
        clock.now += timedelta(minutes=1)
    assert world.strong_calls == 1
    assert {r["decision"] for r in records} == {"challenge"}
    first = records[0]
    assert first["risk"]["reused_from"] is None
    assert all(r["risk"]["reused_from"] == first["decision_id"] for r in records[1:])
    assert all(r["risk"]["level"] == first["risk"]["level"] for r in records)
    assert all(r["cost"]["input_tokens"] == 0 for r in records[1:])


def test_reuse_ends_after_24_hours(gateway, world, clock):
    send(gateway, held_proposal())
    clock.now += timedelta(hours=24, seconds=1)
    assert send(gateway, held_proposal())["risk"]["reused_from"] is None
    assert world.strong_calls == 2


def test_a_changed_payment_method_means_a_fresh_assessment(gateway, world):
    send(gateway, held_proposal())
    world.change_payment_method()
    assert send(gateway, held_proposal())["risk"]["reused_from"] is None
    assert world.strong_calls == 2


def test_a_different_amount_is_a_different_proposal(gateway, world):
    send(gateway, held_proposal())
    other = held_proposal(amount=Money(amount=251501, currency="USD"))
    assert send(gateway, other)["risk"]["reused_from"] is None


def test_identity_and_authorization_still_run_on_a_repeat(gateway, world):
    send(gateway, held_proposal())
    world.authorization = world.authorization.model_copy(update={"status": "revoked"})
    record = send(gateway, held_proposal())
    assert record["decision"] == "block" and record["reasons"] == ["authorization:status"]


def test_clean_results_are_reused_too(gateway):
    first = send(gateway, routine_proposal())
    assert send(gateway, routine_proposal())["risk"]["reused_from"] == first["decision_id"]


def test_fingerprint_covers_agent_and_bill():
    proposal = held_proposal()
    assert fingerprint("a", proposal) != fingerprint("b", proposal)
    assert fingerprint("a", proposal) != fingerprint("a", held_proposal(bill_id=None))
    assert fingerprint("a", proposal) == fingerprint("a", held_proposal(memo="different words"))


def test_tier_0_runs_again_on_reuse(gateway, world):
    send(gateway, held_proposal())
    send(gateway, held_proposal())
    assert world.tier0_calls == 2 and world.strong_calls == 1


def test_a_hard_flag_raised_since_means_a_fresh_assessment(gateway, world):
    """A bill for the payee opened after the first decision: tier 0 now flags it, so no reuse."""
    first = send(gateway, routine_proposal())
    world.extra_features = {"bill_not_referenced": Feature(value=True, evidence=["bill_new"])}
    second = send(gateway, routine_proposal())
    assert second["risk"]["reused_from"] is None
    assert second["risk"]["features"]["bill_not_referenced"]["value"] is True
    assert first["decision"] == "allow" and second["decision"] != "allow"


def test_concurrent_identical_proposals_get_one_model_call(gateway, world):
    from concurrent.futures import ThreadPoolExecutor

    world.delay = 0.05
    with ThreadPoolExecutor(max_workers=5) as pool:
        records = list(pool.map(lambda _: send(gateway, held_proposal()), range(5)))
    assert world.strong_calls == 1
    assert len({r["decision_id"] for r in records}) == 5
    assert sum(r["risk"]["reused_from"] is None for r in records) == 1


def test_varying_the_amount_stops_reaching_the_model_after_the_limit(gateway, world):
    records = [send(gateway, held_proposal(amount=Money(amount=251500 + cents, currency="USD")))
               for cents in range(MAX_FRESH_ASSESSMENTS + 2)]
    assert world.strong_calls == MAX_FRESH_ASSESSMENTS
    limited = records[MAX_FRESH_ASSESSMENTS:]
    assert all(r["risk"]["repeat_limit_reached"] for r in limited)
    assert all(r["decision"] == "challenge" and "risk:repeat_limit" in r["reasons"] for r in limited)
    assert all(r["risk"]["tiers_run"] == ["tier0"] for r in limited)


def test_the_repeat_limit_ends_with_the_window(gateway, world, clock):
    for cents in range(MAX_FRESH_ASSESSMENTS):
        send(gateway, held_proposal(amount=Money(amount=251500 + cents, currency="USD")))
    clock.now += timedelta(hours=24, seconds=1)
    record = send(gateway, held_proposal(amount=Money(amount=251599, currency="USD")))
    assert record["risk"]["repeat_limit_reached"] is False
    assert world.strong_calls == MAX_FRESH_ASSESSMENTS + 1


def test_an_older_risk_table_gains_the_payee_column():
    connection = sqlite3.connect(":memory:")
    connection.execute("""CREATE TABLE risk_results (decision_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
        configuration TEXT NOT NULL, created_at TEXT NOT NULL, payment_method_state TEXT NOT NULL, risk TEXT NOT NULL)""")
    RiskReuse(connection)
    assert "payee_key" in {row[1] for row in connection.execute("PRAGMA table_info(risk_results)")}


def test_clean_payments_that_never_reach_a_model_do_not_count_toward_the_limit(gateway, world):
    records = [send(gateway, routine_proposal(amount=Money(amount=185000 + cents, currency="USD")))
               for cents in range(MAX_FRESH_ASSESSMENTS + 2)]
    assert world.strong_calls == 0
    assert all(not r["risk"]["repeat_limit_reached"] for r in records)
    assert {r["decision"] for r in records} == {"allow"}
