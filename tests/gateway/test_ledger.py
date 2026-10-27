from datetime import timedelta

from zeta_one.contracts import Money
from zeta_one.gateway.ledger import payment_method_state
from zeta_one.gateway.scenarios import load_fixture


def _with(scenario, decision_id, amount=None):
    record = scenario.decision_record.model_copy(update={"decision_id": decision_id})
    proposal = scenario.proposal
    if amount is not None:
        proposal = proposal.model_copy(update={"amount": Money(amount=amount, currency="USD")})
    return record, proposal


def test_held_payment_gets_a_challenge_and_keeps_the_state_it_was_decided_on(ledger, held_scenario):
    record, proposal = held_scenario.decision_record, held_scenario.proposal
    challenge_id = ledger.record(record, proposal, context=held_scenario.context)
    assert challenge_id
    held = ledger.held(challenge_id)
    assert held.status == "held"
    assert held.decision_id == record.decision_id
    assert held.authorization_id == "auth_0001" and held.authorization_version == 1
    assert held.payment_method_state == payment_method_state(held_scenario.context)
    assert ledger.decision(record.decision_id)["execution"] == {"status": "held", "simulated": True}


def test_allow_and_block_get_no_challenge(ledger, routine_scenario):
    assert ledger.record(routine_scenario.decision_record, routine_scenario.proposal) is None
    blocked = load_fixture("unknown_agent").decision_record
    assert ledger.record(blocked, None) is None
    assert ledger.decision(blocked.decision_id)["decision"] == "block"


def test_spend_counts_executed_and_held_only(ledger, held_scenario, routine_scenario):
    agent, since = "agent_ap_assistant_01", held_scenario.decision_record.created_at - timedelta(days=1)
    ledger.record(*_with(routine_scenario, "dec_a", 1000))
    ledger.record(*_with(held_scenario, "dec_b", 200))
    over = load_fixture("over_per_payment_limit")
    ledger.record(*_with(over, "dec_c", 720000))
    assert ledger.spend(agent, since, "USD") == 1200
    assert ledger.spend(agent, since, "EUR") == 0
    assert ledger.spend("someone_else", since, "USD") == 0
    assert ledger.spend(agent, since + timedelta(days=2), "USD") == 0


def test_spend_source_can_leave_out_one_payment(ledger, held_scenario):
    challenge_id = ledger.record(*_with(held_scenario, "dec_b", 200), context=held_scenario.context)
    held = ledger.held(challenge_id)
    since = held_scenario.decision_record.created_at - timedelta(days=1)
    assert ledger.spend_source()("agent_ap_assistant_01", since, "USD") == 200
    assert ledger.spend_source(exclude=held.payment_id)("agent_ap_assistant_01", since, "USD") == 0


def test_resolve_moves_a_held_payment_once(ledger, held_scenario):
    challenge_id = ledger.record(held_scenario.decision_record, held_scenario.proposal)
    held = ledger.held(challenge_id)
    now = held_scenario.decision_record.created_at + timedelta(minutes=5)
    review = {"by": "admin", "outcome": "approved"}
    assert ledger.resolve(held, "executed", review, now) is True
    assert ledger.resolve(held, "blocked", review, now) is False
    served = ledger.decision(held.decision_id)
    assert served["execution"]["status"] == "executed"
    assert served["review"] == review


def test_decisions_lists_newest_first(ledger, held_scenario, routine_scenario):
    ledger.record(*_with(routine_scenario, "dec_1"))
    ledger.record(*_with(routine_scenario, "dec_2"))
    assert [d["decision_id"] for d in ledger.decisions()] == ["dec_2", "dec_1"]
