import json

import pytest

from eval import generate, label, sets


@pytest.fixture
def prepared(tmp_path):
    rows = generate.combos("test", data=tmp_path)
    wording = [{"id": r["id"], "invoice_text": "Invoice", "agent_rationale": "ok", "memo": "m"} for r in rows]
    sets.write_jsonl(tmp_path / "test" / "wording" / "batch_00.output.jsonl", wording)
    generate.assemble("test", data=tmp_path)
    guide = tmp_path / "guide.md"
    guide.write_text("Guide text.")
    assert label.export("test", lambda setup, proposal: {"counterparty": proposal.counterparty_id},
                        data=tmp_path, guide=guide) == len(rows)
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
    by_id = {c.id: c for c in label.load_unlabelled("test", prepared)}
    assert {by_id[i].category for i in sample} <= set(label.JUDGED_CATEGORIES)


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


def test_an_adjudication_is_final_and_agreement_stays_on_the_blind_labels(prepared):
    ids = _write_ai(prepared, lambda case_id: "block")
    out = prepared / "test" / "label"
    reverse = {case_id: blind for blind, case_id in ids.items()}
    sample = json.loads((out / "owner_sample.json").read_text())
    sets.write_jsonl(out / "owner.jsonl", [{"id": reverse[c], "expected": "challenge", "also_acceptable": []} for c in sample])
    sets.write_jsonl(out / "adjudicated.jsonl", [{"id": reverse[sample[0]], "expected": "block", "also_acceptable": ["challenge"]}])

    result = label.merge("test", data=prepared)
    assert result["agreement"]["agreement"] == 0.0
    assert (result["agreement"]["adjudicated"], result["agreement"]["adjudicated_to_ai"]) == (1, 1)
    cases = {c.id: c for c in sets.load_set("test", prepared)}
    settled, kept = cases[sample[0]], cases[sample[1]]
    assert (settled.expected, settled.also_acceptable) == ("block", ["challenge"])
    assert settled.label_provenance.agreed is False and settled.label_provenance.adjudicated_by == "owner"
    assert kept.expected == "challenge"


def test_an_adjudication_must_settle_a_case_the_owner_labelled(prepared):
    ids = _write_ai(prepared, lambda case_id: "block")
    out = prepared / "test" / "label"
    sample = set(json.loads((out / "owner_sample.json").read_text()))
    outside = next(blind for blind, case_id in ids.items() if case_id not in sample)
    sets.write_jsonl(out / "adjudicated.jsonl", [{"id": outside, "expected": "allow", "also_acceptable": []}])
    with pytest.raises(label.LabelError, match="did not label"):
        label.merge("test", data=prepared)


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


def test_export_before_assembling_says_so(tmp_path):
    guide = tmp_path / "guide.md"
    guide.write_text("Guide text.")
    with pytest.raises(label.LabelError, match="assemble"):
        label.export("dev", data=tmp_path, guide=guide)


def test_the_default_context_is_the_seed_with_the_case_setup_applied(tmp_path):
    rows = generate.combos("dev", data=tmp_path)
    ops, proposal = generate.setup_for(rows[0])
    from zeta_one.contracts import Proposal, SetupOp
    context = label.seed_context([SetupOp(**op) for op in ops],
                                 Proposal.model_validate({**proposal, "memo": "", "agent_rationale": ""}))
    assert context["counterparty"]["id"] == proposal["counterparty_id"]
    assert context["counterparty"]["name"] == rows[0]["vendor"]


def test_the_seed_context_never_shows_labels(tmp_path):
    rows = generate.combos("test", data=tmp_path)
    from zeta_one.contracts import Proposal, SetupOp
    for row in rows:
        ops, proposal = generate.setup_for(row)
        text = json.dumps(label.seed_context([SetupOp(**op) for op in ops],
                                             Proposal.model_validate({**proposal, "memo": "", "agent_rationale": ""})))
        for word in ("payee_fraud", "manipulated_agent", "truth", "detectable", row["id"], "Unrelated",
                     "_other", "_original", "_new\"", "_new_"):
            assert word not in text


@pytest.mark.parametrize("where", ["ai", "owner"])
def test_an_unknown_blind_id_is_a_label_error(prepared, where):
    _write_ai(prepared, lambda case_id: "allow")
    out = prepared / "test" / "label"
    row = [{"id": "c999", "expected": "allow"}]
    if where == "ai":
        sets.write_jsonl(out / "ai" / "batch_01.jsonl", row)
        (out / "ai" / "batch_01.meta.json").write_text(json.dumps({"tool_calls": 0}))
    else:
        sets.write_jsonl(out / "owner.jsonl", row)
    with pytest.raises(label.LabelError, match="unknown blind id"):
        label.merge("test", data=prepared)


def test_the_agreement_says_blindness_is_self_reported(prepared):
    ids = _write_ai(prepared, lambda case_id: "challenge")
    out = prepared / "test" / "label"
    reverse = {case_id: blind for blind, case_id in ids.items()}
    sample = json.loads((out / "owner_sample.json").read_text())
    sets.write_jsonl(out / "owner.jsonl", [{"id": reverse[c], "expected": "challenge"} for c in sample])
    assert "self-reported" in label.merge("test", data=prepared)["agreement"]["labeller_blindness"]


def test_blind_order_says_nothing_about_the_label(prepared):
    """The generator samples manipulation cases first; the labeller must not see that order."""
    ids = json.loads((prepared / "test" / "label" / "ids.json").read_text())
    truths = {r["id"]: r["truth"] for r in sets.read_jsonl(prepared / "test" / "combos.jsonl")}
    in_blind_order = [truths[case_id] for case_id in ids.values()]
    first = in_blind_order[:12]
    assert first.count("manipulated_agent") < 8
    assert list(ids.values()) != sorted(ids.values())
    views = json.loads((prepared / "test" / "label" / "owner_view.json").read_text())
    assert [v["id"] for v in views] == sorted(v["id"] for v in views)


def test_the_reading_sheet_shows_cases_blind(tmp_path):
    rows = generate.combos("dev", data=tmp_path)
    wording = [{"id": r["id"], "invoice_text": "Invoice for October services.", "agent_rationale": "Paying it.", "memo": "m"}
               for r in rows]
    sets.write_jsonl(tmp_path / "dev" / "wording" / "batch_00.output.jsonl", wording)
    generate.assemble("dev", data=tmp_path)
    text = label.reading_sheet("dev", n=5, data=tmp_path).read_text()
    assert text.count("\n## c") == 5 and "Agent's rationale (untrusted)" in text
    for word in ("payee_fraud", "manipulated_agent", "legitimate", "category", "truth", "dev_0"):
        assert word not in text.split("No labels:")[1]


def test_a_relabel_without_owner_overlap_removes_old_agreement(prepared):
    ids = _write_ai(prepared, lambda case_id: "challenge")
    out = prepared / "test" / "label"
    reverse = {case_id: blind for blind, case_id in ids.items()}
    sample = json.loads((out / "owner_sample.json").read_text())
    sets.write_jsonl(out / "owner.jsonl", [{"id": reverse[c], "expected": "challenge"} for c in sample])
    label.merge("test", data=prepared)
    assert (prepared / "agreement.json").exists()
    (out / "owner.jsonl").unlink()
    label.merge("test", data=prepared)
    assert not (prepared / "agreement.json").exists() and not (out / "agreement.json").exists()


def test_the_labeller_sees_a_reviewer_confirmation_in_the_context(tmp_path):
    from zeta_one.contracts import Proposal, SetupOp
    rows = generate.combos("test", data=tmp_path)
    row = next(r for r in rows if r["dimensions"]["change_verified"] == "yes")
    ops, proposal = generate.setup_for(row)
    context = label.seed_context([SetupOp(**op) for op in ops],
                                 Proposal.model_validate({**proposal, "memo": "", "agent_rationale": ""}))
    [adjustment] = context["adjustments"]
    assert adjustment["kind"] == "confirmed_method_change"
    assert adjustment["subject"] == max(context["payment_method_history"], key=lambda c: c["changed_at"])["id"]


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Labeller:
    """A stand-in for the Anthropic client: answers each batch from the blind ids in its prompt."""

    def __init__(self, answer=None, stop_reason="end_turn"):
        self.calls, self._answer, self._stop = [], answer, stop_reason
        self.messages = self

    def stream(self, **request):
        self.calls.append(request)
        cases = json.loads(request["messages"][0]["content"].split("## Cases", 1)[1].split("## Answer", 1)[0])
        text = self._answer(cases) if self._answer else "\n".join(
            json.dumps({"id": case["id"], "expected": "challenge", "also_acceptable": [], "reason": "r"}) for case in cases)
        response = type("Response", (), {"stop_reason": self._stop, "content": [_Block(text)], "model": "claude-sonnet-5-5",
                                         "usage": type("Usage", (), {"input_tokens": 10, "output_tokens": 5})()})()
        return type("Stream", (), {"__enter__": lambda s: s, "__exit__": lambda s, *a: None,
                                   "get_final_message": lambda s: response})()


def test_ai_labels_every_batch_with_no_tools_and_says_so(prepared):
    client = _Labeller()
    done = label.ai_label("test", client=client, data=prepared)
    out = prepared / "test" / "label"
    assert done == [p.name.removesuffix(".prompt.md") for p in sorted(out.glob("batch_*.prompt.md"))]
    assert all("tools" not in call and call["model"] == label.AI_SOURCE for call in client.calls)
    meta = json.loads((out / "ai" / "batch_00.meta.json").read_text())
    assert (meta["tool_calls"], meta["tools_offered"], meta["route"]) == (0, [], "anthropic_api")
    assert label.ai_label("test", client=client, data=prepared) == []  # resumes: nothing left to label
    ids = json.loads((out / "ids.json").read_text())
    reverse = {case_id: blind for blind, case_id in ids.items()}
    sample = json.loads((out / "owner_sample.json").read_text())
    sets.write_jsonl(out / "owner.jsonl", [{"id": reverse[c], "expected": "challenge"} for c in sample])
    blindness = label.merge("test", data=prepared)["agreement"]["labeller_blindness"]
    assert "no tools offered" in blindness and "self-reported" not in blindness


@pytest.mark.parametrize("answer, stop, message", [
    (lambda cases: "", "end_turn", "ids"),
    (lambda cases: "\n".join(json.dumps({"id": c["id"], "expected": "allow"}) for c in reversed(cases)), "end_turn", "ids"),
    (lambda cases: "\n".join(json.dumps({"id": c["id"], "expected": "pay"}) for c in cases), "end_turn", "bad label"),
    (None, "max_tokens", "max_tokens"),
])
def test_a_bad_answer_writes_nothing(prepared, answer, stop, message):
    with pytest.raises(label.LabelError, match=message):
        label.ai_label("test", client=_Labeller(answer, stop), data=prepared)
    assert not list((prepared / "test" / "label" / "ai").glob("*.jsonl"))
