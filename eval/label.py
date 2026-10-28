"""Blind labelling: `export` the view the labeller may see, `merge` the AI labels, the owner's labels
and adjudications into labelled cases.

    python -m eval.label export dev          # after `eval.generate assemble dev`
    python -m eval.label merge dev

Under data/eval/<set>/label/:
    ids.json                      blind id -> case id
    batch_NN.prompt.md            the prompt for one labelling subagent, cases inside, no file access needed
    owner_sample.json             test only: the stratified cases the owner labels without seeing the AI label
    owner_view.json               the blind view of those cases
    ai/batch_NN.jsonl             the subagent's answer, saved by the owner
    ai/batch_NN.meta.json         {"tool_calls": N}: copied by the owner from the subagent's run; merge
                                  refuses N != 0. It is self-reported, and the agreement says so.
    owner.jsonl                   {id (blind), expected, also_acceptable}: the owner's labels, final

Export reads the assembled, unlabelled cases. The labeller sees the proposal and the context its
setup produces on a fresh copy of the seed, never `truth`, the category, the setup or the dimension
values. The guide is written by the owner after reading ~20 generated dev cases, and lives
at eval/prompts/label_guide.md.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from eval import sets, stats
from zeta_one.contracts import Case, LabelProvenance, Proposal, SetupOp

PROMPTS = Path(__file__).resolve().parent / "prompts"
BATCH = 20
OWNER_SAMPLE = 40
# The categories the owner's sample and the agreement cover: where the labels are judgement.
JUDGED_CATEGORIES = ("D", "E", "F")
DECISIONS = ("allow", "challenge", "block")
AI_SOURCE = "claude-sonnet-5-5"
BLINDNESS = "tool_calls 0 for every batch, as copied by the owner from each subagent run (self-reported)"

# The context a case's setup produces for its proposal: what the labeller may see.
ContextFor = Callable[[list[SetupOp], Proposal], dict]


@dataclass(frozen=True)
class Unlabelled:
    id: str
    category: str
    setup: list[SetupOp]
    proposal: Proposal


def load_unlabelled(set_name: str, data: Path = sets.DATA) -> list[Unlabelled]:
    path = data / set_name / "cases_unlabelled.jsonl"
    if not path.exists():
        raise LabelError(f"no {path}; run `python -m eval.generate assemble {set_name}` first")
    return [Unlabelled(id=raw["id"], category=raw["category"], setup=[SetupOp(**op) for op in raw["setup"]],
                       proposal=Proposal.model_validate(raw["proposal"])) for raw in sets.read_jsonl(path)]


def seed_context(setup: list[SetupOp], proposal: Proposal) -> dict:
    """The context the engine would build: the setup applied to a fresh seed, read at the seed clock."""
    from zeta_one.rho import mutations
    from zeta_one.rho.seed import SEED_NOW
    from zeta_one.rho.snapshot import Store
    from zeta_one.rho.view import context_for

    with Store() as store:
        for op in setup:
            mutations.apply(store, op)
        context = context_for(store)(proposal, mutations.BUSINESS, SEED_NOW)
    return context.model_dump(mode="json")


class LabelError(ValueError):
    pass


def label_dir(set_name: str, data: Path) -> Path:
    return data / set_name / "label"


def blind_view(case: Unlabelled, blind_id: str, context: dict) -> dict:
    return {"id": blind_id, "proposal": case.proposal.model_dump(mode="json"), "context": context}


def sample_for_owner(cases: list[Unlabelled], n: int = OWNER_SAMPLE, seed: int = 0) -> list[str]:
    """Stratified by category over the judged categories, proportional to size, seeded."""
    groups: dict[str, list[str]] = defaultdict(list)
    for case in sorted(cases, key=lambda c: c.id):
        if case.category in JUDGED_CATEGORIES:
            groups[case.category].append(case.id)
    total = sum(len(ids) for ids in groups.values())
    rng = random.Random(seed)
    chosen: list[str] = []
    for category in sorted(groups):
        take = min(len(groups[category]), round(n * len(groups[category]) / total))
        chosen += rng.sample(groups[category], take)
    return sorted(chosen)


def export(set_name: str, context_for: ContextFor = seed_context, data: Path = sets.DATA,
           guide: Path | None = None) -> int:
    guide_path = guide or PROMPTS / "label_guide.md"
    if not guide_path.exists():
        raise LabelError(f"write the labelling guide at {guide_path} first (after reading ~20 dev cases)")
    cases = [c for c in load_unlabelled(set_name, data) if c.category in ("A", "D", "E", "F")]
    ids = {f"c{index:03d}": case.id for index, case in enumerate(sorted(cases, key=lambda c: c.id))}
    reverse = {case_id: blind for blind, case_id in ids.items()}
    by_id = {c.id: c for c in cases}
    views = {case_id: blind_view(case, reverse[case_id], context_for(case.setup, case.proposal))
             for case_id, case in by_id.items()}
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
            labels[_case_id(ids, row, path.name)] = row
    return labels


def _case_id(ids: dict[str, str], row: dict, source: str) -> str:
    if row.get("id") not in ids:
        raise LabelError(f"{source}: unknown blind id {row.get('id')!r}")
    return ids[row["id"]]


def _check_label(row: dict) -> None:
    if row.get("expected") not in DECISIONS or not set(row.get("also_acceptable", [])) <= set(DECISIONS):
        raise LabelError(f"bad label: {row}")


def merge(set_name: str, data: Path = sets.DATA) -> dict:
    """Write cases.jsonl with every case labelled; return the label agreement on the owner's sample."""
    out = label_dir(set_name, data)
    ids: dict[str, str] = json.loads((out / "ids.json").read_text())
    ai = _read_ai(set_name, ids, data)
    owner_path = out / "owner.jsonl"
    owner = {_case_id(ids, row, "owner.jsonl"): row for row in sets.read_jsonl(owner_path)} if owner_path.exists() else {}
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
        if both and raw["category"] in JUDGED_CATEGORIES:
            pairs.append((ai[case_id]["expected"], owner[case_id]["expected"]))
        provenance = LabelProvenance(sources=sources, agreed=agreed, adjudicated_by="owner" if agreed is False else None)
        cases.append(Case.model_validate({**raw, "expected": final["expected"],
                                          "also_acceptable": final.get("also_acceptable", []),
                                          "label_provenance": provenance.model_dump()}).model_dump(mode="json"))
    sets.write_jsonl(data / set_name / "cases.jsonl", cases)
    agreement = stats.kappa_bootstrap([a for a, _ in pairs], [o for _, o in pairs]) if pairs else None
    if agreement:
        agreement["labeller_blindness"] = BLINDNESS
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
        print(f"{export(args.set)} cases exported")
    else:
        print(json.dumps(merge(args.set), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
