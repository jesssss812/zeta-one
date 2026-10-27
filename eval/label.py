"""Blind labelling: `export` the view the labeller may see, `merge` the AI labels, the owner's labels
and adjudications into labelled cases.

    python -m eval.label export dev          # needs the data layer (W1) for the context each case produces
    python -m eval.label merge dev

Under data/eval/<set>/label/:
    ids.json                      blind id -> case id
    batch_NN.prompt.md            the prompt for one labelling subagent, cases inside, no file access needed
    owner_sample.json             test only: the stratified cases the owner labels without seeing the AI label
    owner_view.json               the blind view of those cases
    ai/batch_NN.jsonl             the subagent's answer, saved by the owner
    ai/batch_NN.meta.json         {"tool_calls": N}: from the subagent's run; merge refuses N != 0
    owner.jsonl                   {id (blind), expected, also_acceptable}: the owner's labels, final

The labeller sees the proposal and the context, never `truth`, the category, the setup or the
dimension values. The guide is written by the owner after reading ~20 generated dev cases, and lives
at eval/prompts/label_guide.md.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from eval import sets, stats
from zeta_one.contracts import Case, LabelProvenance

PROMPTS = Path(__file__).resolve().parent / "prompts"
BATCH = 20
OWNER_SAMPLE = 40
RISK_CATEGORIES = ("D", "E", "F")
DECISIONS = ("allow", "challenge", "block")
AI_SOURCE = "claude-sonnet-5-5"

ContextFor = Callable[[Case], dict]


class LabelError(ValueError):
    pass


def label_dir(set_name: str, data: Path) -> Path:
    return data / set_name / "label"


def blind_view(case: Case, blind_id: str, context: dict) -> dict:
    return {"id": blind_id, "proposal": case.proposal.model_dump(mode="json"), "context": context}


def sample_for_owner(cases: list[Case], n: int = OWNER_SAMPLE, seed: int = 0) -> list[str]:
    """Stratified by category over D, E, F, proportional to size, seeded."""
    groups: dict[str, list[str]] = defaultdict(list)
    for case in sorted(cases, key=lambda c: c.id):
        if case.category in RISK_CATEGORIES:
            groups[case.category].append(case.id)
    total = sum(len(ids) for ids in groups.values())
    rng = random.Random(seed)
    chosen: list[str] = []
    for category in sorted(groups):
        take = min(len(groups[category]), round(n * len(groups[category]) / total))
        chosen += rng.sample(groups[category], take)
    return sorted(chosen)


def export(set_name: str, context_for: ContextFor, data: Path = sets.DATA, guide: Path | None = None) -> int:
    guide_path = guide or PROMPTS / "label_guide.md"
    if not guide_path.exists():
        raise LabelError(f"write the labelling guide at {guide_path} first (after reading ~20 dev cases)")
    cases = [c for c in sets.load_set(set_name, data) if c.category in ("A", "D", "E", "F")]
    ids = {f"c{index:03d}": case.id for index, case in enumerate(sorted(cases, key=lambda c: c.id))}
    reverse = {case_id: blind for blind, case_id in ids.items()}
    by_id = {c.id: c for c in cases}
    views = {case_id: blind_view(case, reverse[case_id], context_for(case)) for case_id, case in by_id.items()}
    out = label_dir(set_name, data)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ids.json").write_text(json.dumps(ids, indent=2) + "\n")
    template = (PROMPTS / "label.md").read_text()
    ordered = [views[case_id] for case_id in sorted(views)]
    for number, start in enumerate(range(0, len(ordered), BATCH)):
        text = template.replace("{{GUIDE}}", guide_path.read_text().strip()).replace(
            "{{CASES}}", json.dumps(ordered[start:start + BATCH], indent=2))
        (out / f"batch_{number:02d}.prompt.md").write_text(text)
    if set_name == "test":
        sample = sample_for_owner(cases)
        (out / "owner_sample.json").write_text(json.dumps(sample, indent=2) + "\n")
        (out / "owner_view.json").write_text(json.dumps([views[case_id] for case_id in sample], indent=2) + "\n")
    return len(ordered)


def _read_ai(set_name: str, ids: dict[str, str], data: Path) -> dict[str, dict]:
    labels: dict[str, dict] = {}
    for path in sorted((label_dir(set_name, data) / "ai").glob("batch_*.jsonl")):
        meta_path = path.with_suffix(".meta.json")
        calls = json.loads(meta_path.read_text()).get("tool_calls") if meta_path.exists() else None
        if calls != 0:
            raise LabelError(f"{path.name}: tool_calls is {calls!r}, not 0; the labeller must be blind")
        for row in sets.read_jsonl(path):
            _check_label(row)
            labels[ids[row["id"]]] = row
    return labels


def _check_label(row: dict) -> None:
    if row.get("expected") not in DECISIONS or not set(row.get("also_acceptable", [])) <= set(DECISIONS):
        raise LabelError(f"bad label: {row}")


def merge(set_name: str, data: Path = sets.DATA) -> dict:
    """Write cases.jsonl with every case labelled; return the label agreement on the owner's sample."""
    out = label_dir(set_name, data)
    ids: dict[str, str] = json.loads((out / "ids.json").read_text())
    ai = _read_ai(set_name, ids, data)
    owner_path = out / "owner.jsonl"
    owner = {ids[row["id"]]: row for row in sets.read_jsonl(owner_path)} if owner_path.exists() else {}
    for row in owner.values():
        _check_label(row)

    cases, pairs = [], []
    for raw in sets.read_jsonl(data / set_name / "cases_unlabelled.jsonl"):
        case_id = raw["id"]
        if case_id not in ai and case_id not in owner:
            raise LabelError(f"{case_id} has no label")
        final = owner.get(case_id) or ai[case_id]
        sources = [AI_SOURCE] * (case_id in ai) + ["owner"] * (case_id in owner)
        both = case_id in ai and case_id in owner
        agreed = ai[case_id]["expected"] == owner[case_id]["expected"] if both else None
        if both and raw["category"] in RISK_CATEGORIES:
            pairs.append((ai[case_id]["expected"], owner[case_id]["expected"]))
        provenance = LabelProvenance(sources=sources, agreed=agreed, adjudicated_by="owner" if agreed is False else None)
        cases.append(Case.model_validate({**raw, "expected": final["expected"],
                                          "also_acceptable": final.get("also_acceptable", []),
                                          "label_provenance": provenance.model_dump()}).model_dump(mode="json"))
    sets.write_jsonl(data / set_name / "cases.jsonl", cases)
    agreement = stats.kappa_bootstrap([a for a, _ in pairs], [o for _, o in pairs]) if pairs else None
    if agreement:
        (out / "agreement.json").write_text(json.dumps(agreement, indent=2) + "\n")
        if set_name == "test":
            (data / "agreement.json").write_text(json.dumps(agreement, indent=2) + "\n")
    return {"cases": len(cases), "agreement": agreement}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["export", "merge"])
    parser.add_argument("set", choices=["dev", "test"])
    args = parser.parse_args(argv)
    if args.command == "export":
        raise SystemExit("export needs the context each case produces, which needs the data layer (W1); "
                         "it is not on main yet. Call eval.label.export(set, context_for) with a ContextFor.")
    print(json.dumps(merge(args.set), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
