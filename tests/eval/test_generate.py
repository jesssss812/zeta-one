import json
from collections import Counter

import pytest

from eval import generate, sets
from zeta_one.contracts import Case


def test_combinations_are_possible_and_cover_every_dimension_value():
    found = generate.all_combos()
    assert all(generate.allowed(c) for c in found)
    for key, values in generate.DIMENSIONS.items():
        assert {c[key] for c in found} == set(values), key


def test_redirect_text_only_arrives_through_a_channel_that_is_not_the_vendor():
    redirects = [c for c in generate.all_combos() if c["invoice"] == "redirect_instruction"]
    assert redirects and all(c["channel"] != "real_vendor" and c["change_verified"] == "no" for c in redirects)


@pytest.mark.parametrize("set_name", ["dev", "test"])
def test_sample_meets_its_quotas_and_caps_undetectable_cases(set_name):
    chosen = generate.sample(set_name, generate.DEFAULT_SEEDS[set_name])
    assert Counter(generate.category_of(c) for c in chosen) == generate.QUOTAS[set_name]
    assert sum(not generate.detectable(c) for c in chosen) <= generate.MAX_UNDETECTABLE
    assert generate.sample(set_name, generate.DEFAULT_SEEDS[set_name]) == chosen


def test_dev_and_test_use_different_seeds_and_sizes(tmp_path):
    dev = generate.combos("dev", data=tmp_path)
    test = generate.combos("test", data=tmp_path)
    assert {row["seed"] for row in dev} != {row["seed"] for row in test}
    assert len(dev) == sum(generate.QUOTAS["dev"].values()) and len(test) == sum(generate.QUOTAS["test"].values())


def test_wording_request_never_carries_labels(tmp_path):
    rows = generate.combos("dev", data=tmp_path)
    for path in (tmp_path / "dev" / "wording").glob("*.input.json"):
        for item in json.loads(path.read_text()):
            assert set(item) == {"id", "vendor", "amount_usd", "invoice", "rationale", "channel",
                                 "bank_details_changed_days_ago", "bank_change_confirmed_with_vendor", "vendor_relationship"}
    assert max(len(json.loads(p.read_text())) for p in (tmp_path / "dev" / "wording").glob("*.input.json")) == generate.BATCH
    assert len(rows) > generate.BATCH


def test_assemble_builds_cases_and_refuses_missing_wording(tmp_path):
    rows = generate.combos("dev", data=tmp_path)
    with pytest.raises(ValueError):
        generate.assemble("dev", data=tmp_path)
    out = [{"id": row["id"], "invoice_text": f"Invoice {row['id']}", "agent_rationale": "ok", "memo": "m"} for row in rows]
    sets.write_jsonl(tmp_path / "dev" / "wording" / "batch_00.output.jsonl", out)
    cases = generate.assemble("dev", data=tmp_path)
    assert len(cases) == len(rows)
    for raw in cases:
        Case.model_validate({**raw, "expected": "allow"})
        assert raw["proposal"]["source_document_ids"] == ([raw["proposal"]["bill_id"]] if raw["proposal"]["bill_id"] else [])
    with_bill = next(c for c in cases if c["proposal"]["bill_id"])
    assert next(op for op in with_bill["setup"] if op["op"] == "add_bill")["args"]["document_text"].startswith("Invoice")
