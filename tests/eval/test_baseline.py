"""A baseline keeps a compact record of a set's results, refuses to be overwritten, and shows what changed."""

import pytest

from eval import baseline, sets


def _row(config, case_id, decision, acceptable):
    return {"config": config, "case_id": case_id, "category": "A", "truth": "legitimate", "expected": "allow",
            "also_acceptable": [], "decision": decision, "acceptable": acceptable, "not_run": None,
            "model_calls": 1, "cost_usd": 0.02, "set_hash": "h",
            "record": {"reasons": ["clean"], "engine_version": "v1", "policy_version": "p",
                       "risk": {"tiers_run": ["tier0", "strong"], "level": "low", "floor": None, "lowered": []}}}


def test_snapshot_keeps_compact_rows_and_the_report_then_compare_shows_changes(tmp_path):
    results, out, report = tmp_path / "results", tmp_path / "baselines", tmp_path / "report.md"
    sets.write_jsonl(results / "dev-engineered.jsonl", [_row("engineered", "d1", "challenge", False),
                                                        _row("engineered", "d2", "allow", True)])
    report.write_text("# report")
    target = baseline.snapshot("dev", "b1", results=results, out=out, report=report)
    rows = sets.read_jsonl(target / "decisions.jsonl")
    assert [r["case_id"] for r in rows] == ["d1", "d2"] and "record" not in rows[0]
    assert rows[0]["tiers_run"] == ["tier0", "strong"] and (target / "report.md").read_text() == "# report"
    with pytest.raises(FileExistsError):
        baseline.snapshot("dev", "b1", results=results, out=out, report=report)

    sets.write_jsonl(results / "dev-engineered.jsonl", [_row("engineered", "d1", "allow", True),
                                                        _row("engineered", "d2", "allow", True)])
    assert baseline.compare("dev", "b1", results=results, out=out) == [
        {"config": "engineered", "case_id": "d1", "expected": "allow", "before": "challenge", "after": "allow",
         "now_acceptable": True}]


def test_snapshot_without_results_says_so(tmp_path):
    with pytest.raises(FileNotFoundError):
        baseline.snapshot("dev", "b1", results=tmp_path, out=tmp_path / "baselines")
