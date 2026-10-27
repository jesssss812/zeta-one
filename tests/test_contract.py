"""The fixtures are the contract with the site: each must load, and replaying it through the real
merge and policy must reproduce its decision."""

from zeta_one.gateway import scenarios
from zeta_one.testing.replay import replay_engine, request_for

REQUIRED = {
    "schema_version", "decision_id", "created_at", "policy_version", "configuration", "decision",
    "reasons", "challenge", "friction_rung", "identity", "authorization", "risk", "execution",
}


def test_fixture_has_required_keys(fixture_raw):
    assert REQUIRED <= fixture_raw["decision_record"].keys()
    assert fixture_raw["decision_record"]["execution"]["simulated"] is True


def test_fixture_round_trips(scenario, fixture_raw):
    dumped = scenarios.dump(scenario)
    assert dumped["decision_record"]["decision"] == fixture_raw["decision_record"]["decision"]
    assert dumped["proposal"] == fixture_raw["proposal"]


def test_replay_reproduces_decision(scenario):
    record, proposal = replay_engine(scenario).evaluate(request_for(scenario))
    expected = scenario.decision_record
    assert record.decision == expected.decision == scenario.scenario.expected
    assert record.reasons == expected.reasons
    assert record.friction_rung == expected.friction_rung
    assert record.execution.status == expected.execution.status
    assert (record.challenge and record.challenge.type) == (expected.challenge and expected.challenge.type)
    assert record.risk.level == expected.risk.level
    assert record.risk.level_set_by == expected.risk.level_set_by
    assert record.risk.floor == expected.risk.floor
    assert record.risk.tiers_run == expected.risk.tiers_run
    assert record.risk.lowered is None
    if expected.identity.result == "verified":
        assert proposal == scenario.proposal


def test_a_case_names_its_setup_and_labels(scenario):
    from zeta_one.contracts import Case
    case = Case(id=f"demo:{scenario.scenario.name}", set="dev", category="A", proposal=scenario.proposal,
                truth="legitimate", expected=scenario.scenario.expected,
                setup=[{"op": "change_payment_method", "args": {"counterparty_id": "cp_0007", "days_ago": 3}}],
                provenance="synthetic:test")
    assert Case.model_validate_json(case.model_dump_json()) == case
