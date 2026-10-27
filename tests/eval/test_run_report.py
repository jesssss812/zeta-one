import json

import pytest

from eval import backends, cases, report, run, sets
from eval.backends import Outcome, Unsupported
from zeta_one.contracts import Case, Money, Proposal


class FakeBackend:
    """Answers from a table; unknown cases are not run."""

    name = "fake"

    def __init__(self, answers: dict[str, str]):
        self.answers = answers

    def run(self, case, configuration):
        if case.id not in self.answers:
            raise Unsupported("not in the table")
        return Outcome(decision=self.answers[case.id])


def _case(case_id, set_, category, truth, expected, detectable=True, also=()):
    return Case(
        id=case_id, set=set_, category=category, proposal=Proposal(
            counterparty_id="cp", payment_method_id="pm", source_account_id="acct", amount=Money(amount=1, currency="USD")),
        truth=truth, expected=expected, also_acceptable=list(also), detectable=detectable, provenance="test",
    )


@pytest.fixture
def data(tmp_path):
    group = [
        _case("a1", "dev", "A", "legitimate", "allow"),
        _case("a2", "dev", "A", "legitimate", "allow"),
        _case("d1", "dev", "D", "payee_fraud", "challenge"),
        _case("e1", "dev", "E", "manipulated_agent", "block", also=["challenge"]),
        _case("e2", "dev", "E", "payee_fraud", "allow", detectable=False),
    ]
    sets.write_jsonl(tmp_path / "dev" / "cases.jsonl", [c.model_dump(mode="json") for c in group])
    return tmp_path


def test_load_set_rejects_a_case_from_another_set(tmp_path):
    sets.write_jsonl(tmp_path / "dev" / "cases.jsonl", [_case("x", "test", "A", "legitimate", "allow").model_dump(mode="json")])
    with pytest.raises(ValueError):
        sets.load_set("dev", tmp_path)


def test_test_set_must_be_frozen_and_stays_frozen(tmp_path):
    sets.write_jsonl(tmp_path / "test" / "cases.jsonl", [_case("t1", "test", "A", "legitimate", "allow").model_dump(mode="json")])
    with pytest.raises(sets.FrozenSetChanged):
        sets.check_frozen("test", sets.load_set("test", tmp_path), tmp_path)
    sets.freeze("test", tmp_path)
    sets.check_frozen("test", sets.load_set("test", tmp_path), tmp_path)
    sets.write_jsonl(tmp_path / "test" / "cases.jsonl", [_case("t1", "test", "A", "legitimate", "block").model_dump(mode="json")])
    with pytest.raises(sets.FrozenSetChanged):
        sets.check_frozen("test", sets.load_set("test", tmp_path), tmp_path)


def test_baselines_and_not_run(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    rows = run.run_set("dev", "always_allow", FakeBackend({}), data=data, results=results)
    assert [r["decision"] for r in rows] == ["allow"] * 5
    assert [r["correct"] for r in rows] == [True, True, False, False, True]
    rows = run.run_set("dev", "rules", FakeBackend({"a1": "allow"}), data=data, results=results)
    assert [r["case_id"] for r in rows if r["not_run"]] == ["a2", "d1", "e1", "e2"]
    assert run.result_path("dev", "rules", results).exists()


def test_report_metrics_and_discordance(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    perfect = {"a1": "allow", "a2": "allow", "d1": "challenge", "e1": "block", "e2": "allow"}
    worse = {**perfect, "a2": "challenge", "e1": "allow"}
    run.run_set("dev", "rules", FakeBackend(perfect), data=data, results=results)
    run.run_set("dev", "engineered", FakeBackend(worse), data=data, results=results)
    built = report.build(results=results, data=data, backend="fake")

    rules = built["metrics"]["rules"]["dev"]
    assert rules["risk (A, D, E, F)"]["accuracy"]["k"] == 5
    engineered = built["metrics"]["engineered"]["dev"]
    assert engineered["A"]["legit_challenge_rate"]["k"] == 1
    assert engineered["E"]["detection"]["k"] == 0 and engineered["E"]["detection"]["n"] == 1  # e2 is undetectable
    assert built["undetectable"] == ["e2"]
    pair = built["discordant"]["rules vs engineered on dev"]
    assert pair["per_category"]["A"] == {"both": 1, "only_a": 1, "only_b": 0, "neither": 0}
    assert (pair["pooled_risk"]["only_a"], pair["pooled_risk"]["only_b"]) == (2, 0)
    assert pair["pooled_risk"]["p"] == pytest.approx(0.5)
    text = report.render(built)
    assert "rules vs engineered on dev" in text and "Limitations" in text and "`e2`" in text
    report.write(built, data)
    assert json.loads((data / "report.json").read_text())["backend"] == "fake"


def test_failure_stage_uses_owner_tags(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    run.run_set("dev", "rules", FakeBackend({"a1": "allow", "a2": "allow", "d1": "allow", "e1": "allow", "e2": "allow"}),
                data=data, results=results)
    (data / "error_tags.json").write_text(json.dumps({"d1": "feature"}))
    built = report.build(results=results, data=data)
    assert built["failures_by_stage"]["rules"]["dev"]["feature"] == 1


def test_end_to_end_on_the_replay_backend(tmp_path):
    results = tmp_path / "results"
    for config in run.CONFIGS:
        run.run_set("dev", config, backends.ReplayBackend(), workers=2, results=results)
    built = report.build(results=results, backend="replay")
    assert built["metrics"]["rules"]["dev"]["risk (A, D, E, F)"]["accuracy"]["n"] == 3
    assert "Plumbing run" in report.render(built)


def test_replay_backend_does_not_pretend_to_run_other_cases():
    other = next(c for c in cases.deterministic_cases() if c.id == "authz_expired")
    with pytest.raises(Unsupported):
        backends.ReplayBackend().run(other, run.CONFIGS["rules"])


def test_deterministic_cases_are_labelled_by_construction():
    group = cases.all_cases()
    assert len({c.id for c in group}) == len(group)
    assert all(c.provenance for c in group)
    assert {c.category for c in cases.deterministic_cases()} >= {"B", "C"}
    assert sum(c.set == "deterministic" for c in group) >= 20
