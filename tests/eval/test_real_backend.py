"""Every hand-written case through the gateway on the real stages, with a stand-in strong tier."""

import pytest

from eval import backends, cases, run
from zeta_one.contracts import TierOutput, TierResult
from zeta_one.rho.models import Money


class EchoStrong:
    """Agrees with tier 0, so the result is tier 0's and no paid model runs."""

    name = "strong"

    def __init__(self):
        self.calls = 0

    def assess(self, risk_input):
        self.calls += 1
        return TierOutput(result=TierResult(tier="strong", model="stand-in", level=risk_input.tier0.level))


class EchoCheap:
    """A stand-in Jev that agrees with tier 0, confidently."""

    name = "cheap"

    def assess(self, risk_input):
        return TierOutput(result=TierResult(tier="cheap", model="stand-in", level=risk_input.tier0.level,
                                            confidence=0.99, probabilities={"risk_level": 0.99}))


@pytest.fixture(scope="module")
def backend():
    return backends.RealBackend(strong_tier=EchoStrong(), cheap_tier=EchoCheap(), open_weight_tier=EchoOpenWeight())


class EchoOpenWeight(EchoStrong):
    name = "open_weight"

    def assess(self, risk_input):
        self.calls += 1
        return TierOutput(result=TierResult(tier="open_weight", model="stand-in", level=risk_input.tier0.level))


@pytest.mark.parametrize("case", cases.all_cases(), ids=lambda c: c.id)
@pytest.mark.parametrize("config", ["rules", "engineered", "jev", "open_weight"])
def test_every_hand_written_case_passes_on_the_real_stages(backend, case, config):
    needs_model = any(op.op == "fail_model" for op in case.setup) or (
        any(op.op == "repeat" for op in case.setup) and not case.agent.endswith("+replay"))
    if needs_model and config == "rules":
        with pytest.raises(backends.Unsupported, match="runs a model"):
            backend.run(case, run.CONFIGS[config])
        return
    outcome = backend.run(case, run.CONFIGS[config])
    if case.expected_reason:
        assert case.expected_reason in outcome.record.reasons
    assert outcome.decision == case.expected or outcome.decision in case.also_acceptable, outcome.record.reasons
    assert len(set(outcome.decisions)) <= 1


class LoweringStrong:
    """Answers low to everything: the floors and deterministic checks must still hold."""

    name = "strong"

    def assess(self, risk_input):
        return TierOutput(result=TierResult(tier="strong", model="stand-in", level="low"))


@pytest.mark.parametrize("case", [c for c in cases.all_cases() if c.expected != "allow"], ids=lambda c: c.id)
def test_a_model_that_clears_everything_lets_no_blocked_or_challenged_case_through(case):
    outcome = backends.RealBackend(strong_tier=LoweringStrong()).run(case, run.CONFIGS["engineered"])
    assert outcome.decision != "allow", outcome.record.reasons


def test_a_live_tier_makes_a_configuration_that_uses_it_paid():
    live = backends.get_backend("real")
    assert live.paid_for(run.CONFIGS["engineered"]) and live.paid_for(run.CONFIGS["jev"])
    stand_in_strong = backends.RealBackend(strong_tier=EchoStrong())
    assert not stand_in_strong.paid_for(run.CONFIGS["engineered"])
    assert stand_in_strong.paid_for(run.CONFIGS["jev"])  # Jev is still live
    both = backends.RealBackend(strong_tier=EchoStrong(), cheap_tier=EchoCheap())
    assert not both.paid_for(run.CONFIGS["jev"]) and not live.paid_for(run.CONFIGS["rules"])
    assert live.paid_for(run.CONFIGS["open_weight"]) and both.paid_for(run.CONFIGS["open_weight"])


def test_the_runner_refuses_the_live_backend_without_a_budget(tmp_path):
    with pytest.raises(run.BudgetRequired):
        run.run_set("deterministic", "engineered", backends.get_backend("real"), results=tmp_path)


def test_a_repeated_adversarial_proposal_reaches_the_model_once():
    strong = EchoStrong()
    case = next(c for c in cases.all_cases() if c.id == "guardrail_repeat_not_rerolled")
    # `strong` runs the model on every case: under `engineered` this case's high floor skips it.
    outcome = backends.RealBackend(strong_tier=strong).run(case, run.CONFIGS["strong"])
    assert strong.calls == 1 and len(outcome.decisions) == 5 and outcome.model_calls == 0  # stand-in has no usage


def test_the_model_failure_case_is_challenged_for_the_model():
    case = next(c for c in cases.all_cases() if c.id == "guardrail_model_failure")
    outcome = backends.RealBackend(strong_tier=EchoStrong()).run(case, run.CONFIGS["engineered"])
    assert outcome.decision == "challenge" and "risk:model_unavailable" in outcome.record.reasons


def test_the_whole_deterministic_set_runs_and_reports(tmp_path):
    from eval import report

    results = tmp_path / "results"
    rows = run.run_set("deterministic", "engineered", backends.RealBackend(strong_tier=EchoStrong()), results=results)
    assert all(r["acceptable"] for r in rows) and not any(r["not_run"] for r in rows)
    built = report.build(results=results)
    assert built["backends"] == ["real"]


def test_generated_cases_run_through_the_real_backend(tmp_path, backend):
    from eval import generate, sets
    from zeta_one.contracts import Case

    rows = generate.combos("test", data=tmp_path)
    wording = [{"id": r["id"], "invoice_text": "Invoice for services.", "agent_rationale": "Paying the bill.", "memo": "m"}
               for r in rows]
    sets.write_jsonl(tmp_path / "test" / "wording" / "batch_00.output.jsonl", wording)
    for raw in generate.assemble("test", data=tmp_path)[::7]:
        outcome = backend.run(Case.model_validate({**raw, "expected": "allow"}), run.CONFIGS["engineered"])
        assert outcome.decision in ("allow", "challenge", "block")
        assert outcome.record.identity.result == "verified" and outcome.record.risk.tiers_run[0] == "tier0"


def test_a_rules_only_run_needs_no_budget_even_on_the_live_backend(tmp_path, monkeypatch):
    from zeta_one.risk import claude

    def never(self, risk_input):
        raise AssertionError("a rules run called the strong tier")

    monkeypatch.setattr(claude.StrongTier, "assess", never)  # so a regression can't spend money here
    rows = run.run_set("deterministic", "rules", backends.get_backend("real"), results=tmp_path)
    assert rows and all(r["model_calls"] == 0 for r in rows if not r["not_run"])


def test_a_setup_the_backend_cannot_run_faithfully_is_not_run(backend):
    from zeta_one.contracts import SetupOp
    base = next(c for c in cases.all_cases() if c.id == "guardrail_split_payments")
    twice = base.model_copy(update={"setup": [*base.setup, SetupOp(op="add_spend", args={"amount": 1})]})
    with pytest.raises(backends.Unsupported, match="repeats"):
        backend.run(twice, run.CONFIGS["rules"])
    replay = base.model_copy(update={"agent": "builtin:ap_assistant+replay", "setup": []})
    with pytest.raises(backends.Unsupported, match="replay"):
        backend.run(replay, run.CONFIGS["rules"])


def test_a_follow_up_that_never_gets_a_held_payment_is_not_run(backend):
    case = next(c for c in cases.all_cases() if c.id == "guardrail_self_approval_refused")
    blocked = case.model_copy(update={"agent": "builtin:ap_assistant+unsigned"})
    with pytest.raises(backends.Unsupported, match="held payment"):
        backend.run(blocked, run.CONFIGS["rules"])


def test_a_reason_mismatch_fails_the_case(tmp_path, monkeypatch):
    case = next(c for c in cases.all_cases() if c.id == "authz_expired")
    wrong = case.model_copy(update={"expected_reason": "authorization:status"})
    row = run._row(wrong, "rules", backends.RealBackend(strong_tier=EchoStrong()).run(wrong, run.CONFIGS["rules"]), None)
    assert row["decision"] == "block" and row["reason_ok"] is False and row["acceptable"] is False


def test_generated_cases_reproduce_their_dimensions_in_tier_0(tmp_path, backend):
    from eval import generate, sets
    from zeta_one.contracts import Case

    rows = generate.combos("test", data=tmp_path)
    wording = [{"id": r["id"], "invoice_text": "Invoice for services.", "agent_rationale": "Paying the bill.", "memo": "m"}
               for r in rows]
    sets.write_jsonl(tmp_path / "test" / "wording" / "batch_00.output.jsonl", wording)
    for raw, row in list(zip(generate.assemble("test", data=tmp_path), rows))[::5]:
        dims = row["dimensions"]
        features = backend.run(Case.model_validate({**raw, "expected": "allow"}), run.CONFIGS["rules"]).record.risk.features
        assert features["counterparty_is_new"].value is (dims["tenure"] == "new"), dims
        assert features["payment_method_changed_days_ago"].value == dims["change_days"], dims
        assert features["payment_method_change_confirmed"].value is (dims["change_verified"] == "yes"), dims
        assert features["bill_mismatch"].value is (dims["bill"] == "other_vendor"), dims
        ratio = features["amount_ratio_to_vendor_median"].value
        assert ratio is None if dims["tenure"] == "new" else ratio == dims["amount_ratio"], dims


def test_evaluation_records_carry_the_engine_version(backend):
    from zeta_one.gateway.wiring import engine_version
    case = next(c for c in cases.all_cases() if c.id == "demo_routine_bill")
    record = backend.run(case, run.CONFIGS["rules"]).record
    assert record.engine_version == engine_version() and record.seed_version and record.policy_version


@pytest.mark.parametrize("case", [c for c in cases.all_cases() if c.expected != "allow"], ids=lambda c: c.id)
def test_a_jev_that_clears_everything_lets_no_blocked_or_challenged_case_through(case):
    class LoweringCheap:
        name = "cheap"

        def assess(self, risk_input):
            return TierOutput(result=TierResult(tier="cheap", model="stand-in", level="low", confidence=0.99,
                                                probabilities={"risk_level": 0.99}))

    backend = backends.RealBackend(strong_tier=LoweringStrong(), cheap_tier=LoweringCheap())
    assert backend.run(case, run.CONFIGS["jev"]).decision != "allow"


def test_a_reviewer_confirmed_change_is_not_a_floor_and_an_unconfirmed_one_is(backend):
    from zeta_one.contracts import Case, SetupOp
    base = next(c for c in cases.all_cases() if c.id == "demo_routine_bill")
    change = SetupOp(op="change_payment_method", args={"counterparty_id": "cp_0012", "days_ago": 5})
    unconfirmed = base.model_copy(update={"id": "u", "setup": [change]})
    confirmed = base.model_copy(update={"id": "c", "setup": [change, SetupOp(op="confirm_method_change")]})
    floor_u = backend.run(unconfirmed, run.CONFIGS["rules"]).record.risk.floor
    risk_c = backend.run(confirmed, run.CONFIGS["rules"]).record.risk
    assert "payment_method_changed_days_ago" in floor_u.flags
    assert risk_c.floor is None or "payment_method_changed_days_ago" not in risk_c.floor.flags
    assert risk_c.adjustments and risk_c.adjustments[0].startswith("adj_setup_")


def test_a_confirmation_of_an_earlier_change_does_not_confirm_a_later_one(backend):
    from zeta_one.contracts import SetupOp
    base = next(c for c in cases.all_cases() if c.id == "demo_routine_bill")
    setup = [SetupOp(op="change_payment_method", args={"counterparty_id": "cp_0012", "days_ago": 50,
                                                        "new_method_id": "pm_confirmed"}),
             SetupOp(op="confirm_method_change", args={"method_id": "pm_confirmed", "days_ago": 50}),
             SetupOp(op="change_payment_method", args={"counterparty_id": "cp_0012", "days_ago": 1,
                                                        "new_method_id": "pm_latest"})]
    case = base.model_copy(update={"id": "scoped", "setup": setup,
                                   "proposal": base.proposal.model_copy(update={"payment_method_id": "pm_latest"})})
    result = backend.run(case, run.CONFIGS["rules"])
    assert "payment_method_changed_days_ago" in result.record.risk.floor.flags
    assert result.record.risk.features["payment_method_change_confirmed"].value is False
    confirmation = result.record.context.adjustments[0]
    assert confirmation.subject == result.record.context.payment_method_history[0].id
    assert (result.record.context.payment_method_history[0].changed_at - confirmation.at).days == 0


@pytest.mark.parametrize("paid, needs_approval", [(False, True), (True, False)])
def test_only_a_payee_never_paid_needs_approval_as_new(backend, paid, needs_approval):
    from zeta_one.contracts import SetupOp
    base = next(c for c in cases.all_cases() if c.id == "demo_routine_bill")
    setup = [SetupOp(op="add_counterparty", args={"counterparty_id": "cp_young", "name": "Young Supply",
                                                   "created_days_ago": 10, "payment_method_id": "pm_young"}),
             SetupOp(op="add_bill", args={"bill_id": "bill_young", "counterparty_id": "cp_young", "amount": 46000,
                                          "currency": "USD", "document_text": "Delivery job: $460."})]
    if paid:
        setup.append(SetupOp(op="add_payments", args={"counterparty_id": "cp_young", "count": 1,
                                                      "median_amount": 46000, "currency": "USD", "days_ago": 5}))
    proposal = base.proposal.model_copy(update={"counterparty_id": "cp_young", "payment_method_id": "pm_young",
                                                "bill_id": "bill_young", "source_document_ids": ["bill_young"],
                                                "amount": Money(amount=46000, currency="USD")})
    record = backend.run(base.model_copy(update={"id": "young", "setup": setup, "proposal": proposal}),
                         run.CONFIGS["rules"]).record
    assert record.risk.features["counterparty_is_new"].value is True
    assert ("authorization:new_counterparty_requires_approval" in record.reasons) is needs_approval
