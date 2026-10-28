"""The script that records real runs for the site writes the demo API's shapes and says they are recorded."""

import json

from scripts import record_runs
from zeta_one.contracts import ScenarioResult
from zeta_one.gateway.scenarios import ORDER, load_fixture


def test_recording_writes_every_scenario_an_index_and_the_report(tmp_path):
    report = tmp_path / "report.json"
    report.write_text('{"sets": {}}')
    index = record_runs.record(out=tmp_path / "data", eval_report=report)
    assert index["recorded"] is True and index["simulated"] is True and index["live_models"] is False
    assert [item["name"] for item in index["scenarios"]] == ORDER
    for name in ORDER:
        raw = json.loads((tmp_path / "data" / "scenarios" / f"{name}.json").read_text())
        result = ScenarioResult.model_validate(raw)
        assert result.decision_record.decision == load_fixture(name).scenario.expected
        assert result.decision_record.execution.simulated is True
        assert raw["recorded"]["live_models"] is False
    assert json.loads((tmp_path / "data" / "eval_report.json").read_text()) == {"sets": {}}
    assert json.loads((tmp_path / "data" / "index.json").read_text())["eval_report"] == "eval_report.json"


def test_without_a_report_the_index_says_so(tmp_path):
    index = record_runs.record(out=tmp_path / "data", eval_report=tmp_path / "missing.json")
    assert index["eval_report"] is None and not (tmp_path / "data" / "eval_report.json").exists()
