"""Every hand-written case through the gateway on the real stages, with a stand-in strong tier."""

import pytest

from eval import backends, cases, run
from zeta_one.contracts import TierOutput, TierResult


class EchoStrong:
    """Agrees with tier 0, so the result is tier 0's and no paid model runs."""

    name = "strong"

    def __init__(self):
        self.calls = 0

    def assess(self, risk_input):
        self.calls += 1
        return TierOutput(result=TierResult(tier="strong", model="stand-in", level=risk_input.tier0.level))


@pytest.fixture(scope="module")
def backend():
    return backends.RealBackend(strong_tier=EchoStrong())


@pytest.mark.parametrize("case", cases.all_cases(), ids=lambda c: c.id)
@pytest.mark.parametrize("config", ["rules", "engineered"])
def test_every_hand_written_case_passes_on_the_real_stages(backend, case, config):
    outcome = backend.run(case, run.CONFIGS[config])
    assert outcome.decision == case.expected or outcome.decision in case.also_acceptable, outcome.record.reasons
    assert len(set(outcome.decisions)) <= 1


def test_a_live_strong_tier_makes_the_backend_paid():
    assert backends.get_backend("real").paid is True
    assert backends.RealBackend(strong_tier=EchoStrong()).paid is False


def test_the_runner_refuses_the_live_backend_without_a_budget(tmp_path):
    with pytest.raises(run.BudgetRequired):
        run.run_set("deterministic", "engineered", backends.get_backend("real"), results=tmp_path)


def test_a_repeated_adversarial_proposal_reaches_the_model_once():
    strong = EchoStrong()
    case = next(c for c in cases.all_cases() if c.id == "guardrail_repeat_not_rerolled")
    outcome = backends.RealBackend(strong_tier=strong).run(case, run.CONFIGS["engineered"])
    assert strong.calls == 1 and len(outcome.decisions) == 5


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
