import json

import pytest

from eval import backends, cases, report, run, sets
from eval.backends import Outcome, Unsupported
from zeta_one.contracts import Case, Money, Proposal


class FakeBackend:
    """Answers from a table; unknown cases are not run."""

    name = "fake"
    paid = False
    measures_latency = True

    def __init__(self, answers: dict[str, str], decisions: dict[str, list[str]] | None = None):
        self.answers = answers
        self.decisions = decisions or {}

    def run(self, case, configuration):
        if case.id not in self.answers:
            raise Unsupported("not in the table")
        return Outcome(decision=self.answers[case.id], decisions=self.decisions.get(case.id, []))


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
    built = report.build(results=results, data=data)

    rules = built["metrics"]["rules"]["dev"]
    risk = rules["risk (A, D, E, F)"]
    assert (risk["accuracy"]["k"], risk["accuracy"]["n"], risk["undetectable"]) == (4, 4, 1)  # e2 is left out
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
    assert json.loads((data / "report.json").read_text())["backends"] == ["fake"]
    assert "Confusion matrix" in text and "Legit challenged" in text


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
    built = report.build(results=results)
    assert built["metrics"]["rules"]["dev"]["risk (A, D, E, F)"]["accuracy"]["n"] == 3
    assert built["backends"] == ["replay"]
    text = report.render(built)
    assert "Not a measurement of the real engine" in text and "not measured" in text


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


def test_a_case_whose_repeats_disagree_does_not_pass(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    answers = {"a1": "allow", "a2": "allow", "d1": "challenge", "e1": "block", "e2": "allow"}
    backend = FakeBackend(answers, decisions={"e1": ["block", "allow", "block"], "a1": ["allow", "allow"]})
    rows = {r["case_id"]: r for r in run.run_set("dev", "rules", backend, data=data, results=tmp_path / "r")}
    assert rows["e1"]["stable"] is False and rows["e1"]["correct"] is False and rows["e1"]["acceptable"] is False
    assert rows["a1"]["stable"] is True and rows["a1"]["correct"] is True


def test_a_case_that_raises_is_not_run_and_the_rest_are_written(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])

    class Broken(FakeBackend):
        def run(self, case, configuration):
            if case.id == "d1":
                raise RuntimeError("boom")
            return super().run(case, configuration)

    results = tmp_path / "r"
    rows = run.run_set("dev", "rules", Broken({"a1": "allow", "a2": "allow", "e1": "block", "e2": "allow"}),
                       data=data, results=results)
    assert next(r for r in rows if r["case_id"] == "d1")["not_run"] == "error: RuntimeError: boom"
    assert len(run.result_path("dev", "rules", results).read_text().splitlines()) == 5


def test_rows_record_the_backend_and_the_run_time_set_hash(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    rows = run.run_set("dev", "rules", FakeBackend({}), data=data, results=tmp_path / "r")
    digest = sets.set_hash(sets.load_set("dev", data))
    assert {(r["backend"], r["set_hash"], r["measured_latency"]) for r in rows} == {("fake", digest, True)}


class PaidBackend(FakeBackend):
    name = "paid"
    paid = True


def test_a_paid_backend_needs_live_and_a_budget(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    with pytest.raises(run.BudgetRequired):
        run.run_set("dev", "engineered", PaidBackend({}), data=data, results=tmp_path / "r")
    with pytest.raises(run.BudgetRequired):
        run.run_set("dev", "engineered", PaidBackend({}), data=data, results=tmp_path / "r", live=True)
    run.run_set("dev", "engineered", PaidBackend({}), data=data, results=tmp_path / "r", live=True, max_usd=1.0)
    run.run_set("dev", "always_allow", PaidBackend({}), data=data, results=tmp_path / "r")  # baselines are free
    run.run_set("dev", "rules", PaidBackend({}), data=data, results=tmp_path / "r")  # no model in rules


def test_the_budget_stops_starting_cases(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    budget = run._Budget(1.5)
    assert not budget.exhausted()
    budget.add({"record": {"cost": {"usd": 1.0}}})
    assert not budget.exhausted()
    budget.add({"record": {"cost": {"usd": 1.0}}})
    assert budget.exhausted()


def test_an_always_allow_baseline_earns_nothing_from_undetectable_cases(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    run.run_set("dev", "always_allow", FakeBackend({}), data=data, results=results)
    e = report.build(results=results, data=data)["metrics"]["always_allow"]["dev"]["E"]
    assert (e["accuracy"]["k"], e["accuracy"]["n"]) == (0, 1)


def test_an_undefined_kappa_renders(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    run.run_set("dev", "rules", FakeBackend({}), data=data, results=results)
    from eval import stats
    (data / "agreement.json").write_text(json.dumps(stats.kappa_bootstrap(["block"] * 5, ["block"] * 5)))
    assert "undefined" in report.render(report.build(results=results, data=data))


def test_a_floor_allowed_through_is_blamed_on_merge_or_policy_before_the_model():
    row = {"category": "D", "decision": "allow", "expected": "challenge", "record": {
        "decision": "allow", "reasons": ["risk:model_unavailable"],
        "risk": {"floor": {"level": "elevated", "flags": ["x"]}, "tiers_run": ["tier0", "strong"]}}}
    assert report.failure_stage(row) == "merge_or_policy"


def test_the_report_marks_results_whose_set_changed(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    run.run_set("dev", "rules", FakeBackend({}), data=data, results=results)
    assert report.build(results=results, data=data)["stale_sets"] == []
    extra = _case("a3", "dev", "A", "legitimate", "allow")
    with (data / "dev" / "cases.jsonl").open("a") as f:
        f.write(json.dumps(extra.model_dump(mode="json")) + "\n")
    built = report.build(results=results, data=data)
    assert built["stale_sets"] == ["dev"] and "Stale results" in report.render(built)


def test_unstable_repeats_show_in_the_deterministic_section(tmp_path):
    rows = [{"case_id": "g", "set": "deterministic", "category": "E", "truth": "manipulated_agent",
             "detectable": True, "expected": "block", "decision": "block", "correct": False, "acceptable": False,
             "stable": False, "not_run": None}]
    assert report.cell(rows)["unstable"] == 1


def test_a_frozen_set_is_not_refrozen_without_force_and_a_note(tmp_path):
    sets.write_jsonl(tmp_path / "test" / "cases.jsonl", [_case("t1", "test", "A", "legitimate", "allow").model_dump(mode="json")])
    sets.freeze("test", tmp_path)
    with pytest.raises(sets.AlreadyFrozen):
        sets.freeze("test", tmp_path)
    with pytest.raises(sets.AlreadyFrozen):
        sets.freeze("test", tmp_path, force=True)
    sets.freeze("test", tmp_path, force=True, note="relabelled a typo in t1")
    log = [json.loads(line) for line in (tmp_path / "test" / sets.FREEZE_LOG).read_text().splitlines()]
    assert [entry["note"] for entry in log] == [None, "relabelled a typo in t1"]
    assert all(entry["frozen_at"] and entry["commit"] and entry["seed_version"] and entry["lexicon_sha256"]
               for entry in log)


def test_a_frozen_set_refuses_a_changed_lexicon(tmp_path, monkeypatch):
    from zeta_one.risk import features
    sets.write_jsonl(tmp_path / "test" / "cases.jsonl", [_case("t1", "test", "A", "legitimate", "allow").model_dump(mode="json")])
    sets.freeze("test", tmp_path)
    sets.check_frozen("test", sets.load_set("test", tmp_path), tmp_path)
    monkeypatch.setattr(features, "INSTRUCTION_PATTERN_LEXICON", (*features.INSTRUCTION_PATTERN_LEXICON, r"\\bwire\\b"))
    with pytest.raises(sets.FrozenSetChanged, match="lexicon"):
        sets.check_frozen("test", sets.load_set("test", tmp_path), tmp_path)


def test_freezing_the_hard_set_keeps_it_loadable(tmp_path):
    sets.write_jsonl(tmp_path / "hard" / "owner.jsonl", [_case("h1", "hard", "E", "payee_fraud", "block").model_dump(mode="json")])
    sets.freeze("hard", tmp_path)
    assert [c.id for c in sets.load_set("hard", tmp_path)] == ["h1"]


def test_the_report_shows_versions_and_says_when_dev_is_only_the_demo_cases(tmp_path):
    results = tmp_path / "results"
    run.run_set("dev", "rules", backends.ReplayBackend(), results=results)
    built = report.build(results=results)
    assert built["dev_is_demo_only"] is True and built["versions"]["policy_version"]
    text = report.render(built)
    assert "dev holds only the hand-built demo cases" in text and "Policy version" in text
    assert "## Not run\n\n- none" in text


@pytest.mark.parametrize("max_usd", [float("nan"), float("inf"), 0.0, -1.0])
def test_a_budget_must_be_a_positive_number(data, tmp_path, monkeypatch, max_usd):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    with pytest.raises(run.BudgetRequired):
        run.run_set("dev", "engineered", PaidBackend({}), data=data, results=tmp_path / "r", live=True, max_usd=max_usd)


def test_mcnemar_leaves_out_undetectable_cases_as_accuracy_does(data, tmp_path, monkeypatch):
    monkeypatch.setattr(cases, "demo_cases", lambda: [])
    results = tmp_path / "results"
    base = {"a1": "allow", "a2": "allow", "d1": "challenge", "e1": "block"}
    run.run_set("dev", "rules", FakeBackend({**base, "e2": "allow"}), data=data, results=results)
    run.run_set("dev", "engineered", FakeBackend({**base, "e2": "block"}), data=data, results=results)
    pair = report.build(results=results, data=data)["discordant"]["rules vs engineered on dev"]
    assert all(t["only_a"] == 0 and t["only_b"] == 0 for t in pair["per_category"].values())  # e2 differs but is excluded


def test_cost_per_action_counts_every_send(tmp_path):
    rows = [{"case_id": "r", "set": "dev", "category": "E", "truth": "manipulated_agent", "detectable": True,
             "expected": "block", "decision": "block", "correct": True, "acceptable": True, "not_run": None,
             "cost_usd": 0.05, "record": {"cost": {"usd": 0.0}, "risk": {}}}]
    assert report.cell(rows)["cost_per_action_usd"] == pytest.approx(0.05)


def _row(decision, truth, tiers, usd, detectable=True):
    return {"case_id": decision + truth, "set": "dev", "category": "D", "truth": truth, "detectable": detectable,
            "expected": "challenge", "decision": decision, "correct": True, "acceptable": True, "not_run": None,
            "cost_usd": usd, "record": {"cost": {"usd": usd}, "risk": {"tiers_run": tiers, "tier_results": []}}}


def test_cost_says_how_many_decisions_reached_a_model_and_what_a_caught_fraud_cost():
    rows = [_row("allow", "legitimate", ["tier0"], 0.0), _row("challenge", "payee_fraud", ["tier0", "strong"], 0.04),
            _row("block", "payee_fraud", ["tier0", "strong"], 0.06), _row("allow", "legitimate", ["tier0"], 0.0)]
    cost = report.cell(rows)["cost"]
    assert (cost["reached_a_model"]["k"], cost["reached_a_model"]["n"]) == (2, 4)
    assert cost["usd_per_1000_decisions"] == pytest.approx(25.0)
    assert cost["usd_per_fraud_caught"] == pytest.approx(0.05)


def test_cost_flags_unpriced_models_and_estimated_usage():
    row = _row("challenge", "payee_fraud", ["tier0", "open_weight"], 0.0)
    row["record"]["cost"]["unpriced_models"] = ["org/open-model"]
    row["record"]["risk"]["tier_results"] = [{"tier": "open_weight", "usage": {"estimated": True}}]
    cost = report.cell([row])["cost"]
    assert cost["unpriced_models"] == ["org/open-model"] and cost["estimated_usage"] is True
