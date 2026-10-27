import json

import pytest

from eval import generate, label, sets


@pytest.fixture
def prepared(tmp_path):
    rows = generate.combos("test", data=tmp_path)
    wording = [{"id": r["id"], "invoice_text": "Invoice", "agent_rationale": "ok", "memo": "m"} for r in rows]
    sets.write_jsonl(tmp_path / "test" / "wording" / "batch_00.output.jsonl", wording)
    generate.assemble("test", data=tmp_path)
    # load_set reads cases.jsonl; for export the unlabelled cases need an expected, so label provisionally
    provisional = [{**r, "expected": "allow"} for r in sets.read_jsonl(tmp_path / "test" / "cases_unlabelled.jsonl")]
    sets.write_jsonl(tmp_path / "test" / "cases.jsonl", provisional)
    guide = tmp_path / "guide.md"
    guide.write_text("Guide text.")
    label.export("test", lambda case: {"counterparty": "cp_eval_01"}, data=tmp_path, guide=guide)
    return tmp_path


def test_export_is_blind(prepared):
    out = prepared / "test" / "label"
    text = "".join(p.read_text() for p in out.glob("batch_*.prompt.md"))
    assert "Guide text." in text and "{{" not in text
    for word in ("payee_fraud", "manipulated_agent", "legitimate", "truth", "detectable", "setup", "category", "test_0"):
        assert word not in text
    ids = json.loads((out / "ids.json").read_text())
    assert all(blind.startswith("c") for blind in ids)
    sample = json.loads((out / "owner_sample.json").read_text())
    assert len(sample) == label.OWNER_SAMPLE and sample == sorted(sample)
    by_id = {c.id: c for c in sets.load_set("test", prepared)}
    assert {by_id[i].category for i in sample} <= set(label.RISK_CATEGORIES)


def test_export_needs_the_guide(tmp_path):
    with pytest.raises(label.LabelError):
        label.export("dev", lambda case: {}, data=tmp_path, guide=tmp_path / "missing.md")


def _write_ai(prepared, expected_of, tool_calls=0):
    out = prepared / "test" / "label"
    ids = json.loads((out / "ids.json").read_text())
    rows = [{"id": blind, "expected": expected_of(case_id), "also_acceptable": []} for blind, case_id in ids.items()]
    (out / "ai").mkdir()
    sets.write_jsonl(out / "ai" / "batch_00.jsonl", rows)
    (out / "ai" / "batch_00.meta.json").write_text(json.dumps({"tool_calls": tool_calls}))
    return ids


def test_merge_records_provenance_agreement_and_owner_final(prepared):
    ids = _write_ai(prepared, lambda case_id: "challenge")
    out = prepared / "test" / "label"
    reverse = {case_id: blind for blind, case_id in ids.items()}
    sample = json.loads((out / "owner_sample.json").read_text())
    owner = [{"id": reverse[case_id], "expected": "challenge" if i % 4 else "block", "also_acceptable": ["allow"]}
             for i, case_id in enumerate(sample)]
    sets.write_jsonl(out / "owner.jsonl", owner)

    result = label.merge("test", data=prepared)
    assert result["cases"] == 100
    agreement = json.loads((prepared / "agreement.json").read_text())
    assert agreement["n"] == len(sample) and agreement["agreement"] == pytest.approx(0.75)

    cases = {c.id: c for c in sets.load_set("test", prepared)}
    disagreed = cases[sample[0]]
    assert disagreed.expected == "block" and disagreed.also_acceptable == ["allow"]
    assert disagreed.label_provenance.agreed is False and disagreed.label_provenance.adjudicated_by == "owner"
    agreed = cases[sample[1]]
    assert agreed.label_provenance.agreed is True and agreed.label_provenance.sources[-1] == "owner"
    ai_only = next(c for c in cases.values() if c.id not in sample)
    assert ai_only.label_provenance.sources == [label.AI_SOURCE] and ai_only.label_provenance.agreed is None


def test_merge_refuses_a_labeller_that_used_tools(prepared):
    _write_ai(prepared, lambda case_id: "allow", tool_calls=3)
    with pytest.raises(label.LabelError):
        label.merge("test", data=prepared)


def test_merge_refuses_unlabelled_cases_and_bad_labels(prepared):
    ids = _write_ai(prepared, lambda case_id: "allow")
    out = prepared / "test" / "label"
    sets.write_jsonl(out / "ai" / "batch_00.jsonl", [{"id": next(iter(ids)), "expected": "maybe"}])
    with pytest.raises(label.LabelError):
        label.merge("test", data=prepared)
    sets.write_jsonl(out / "ai" / "batch_00.jsonl", [{"id": next(iter(ids)), "expected": "allow"}])
    with pytest.raises(label.LabelError):
        label.merge("test", data=prepared)
