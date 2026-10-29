"""Blind labelling: `export` the view the labeller may see, `merge` the AI labels, the owner's labels
and adjudications into labelled cases.

    python -m eval.label sheet dev           # 20 cases to read before writing the labelling guide
    python -m eval.label export dev          # after `eval.generate assemble dev`
    python -m eval.label ai dev              # the AI labels, through the Anthropic API with no tools (paid)
    python -m eval.label merge dev

Under data/eval/<set>/label/:
    ids.json                      blind id -> case id
    batch_NN.prompt.md            the prompt for one labelling subagent, cases inside, no file access needed
    owner_sample.json             test only: the stratified cases the owner labels without seeing the AI label
    owner_view.json               the blind view of those cases
    ai/batch_NN.jsonl             the AI labeller's answer
    ai/batch_NN.meta.json         {"tool_calls": N, ...}: merge refuses N != 0. `ai` writes it with
                                  "route": "anthropic_api" and no tools offered, so the labeller could
                                  not open a file; a batch from a subagent run carries the count the
                                  owner copied from it, which is self-reported. The agreement says which.
    owner.jsonl                   {id (blind), expected, also_acceptable}: the owner's blind labels,
                                  written before the AI labels are read; agreement is measured on these
    adjudicated.jsonl             {id (blind), expected, also_acceptable}: the owner's label after reading
                                  the AI's, for disagreements the owner settled; final where present

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
from typing import Any

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
API_BLINDNESS = ("every batch sent through the Anthropic API with no tools offered, so the labeller could "
                 "not open a file; it saw only its prompt")
AI_MAX_TOKENS = 16_000

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

    from eval.cases import EVAL_OPS, confirmed_change

    with Store() as store:
        for op in setup:
            if op.op not in EVAL_OPS:
                mutations.apply(store, op)
        context = context_for(store)(proposal, mutations.BUSINESS, SEED_NOW)
        confirm = next((op for op in setup if op.op == "confirm_method_change"), None)
        if confirm:
            confirmation = confirmed_change(store, proposal, mutations.BUSINESS, SEED_NOW, confirm.args)
            # As the gateway would show it: the business's active adjustments that bear on the payee.
            context = context.model_copy(update={"adjustments": [confirmation] if confirmation else []})
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
    # Case ids follow the generator's sampling order, which groups classes, so blind ids and the
    # order of the prompts follow a seeded shuffle instead: position must say nothing about the label.
    shuffled = sorted(cases, key=lambda c: c.id)
    random.Random(f"blind:{set_name}").shuffle(shuffled)
    ids = {f"c{index:03d}": case.id for index, case in enumerate(shuffled)}
    reverse = {case_id: blind for blind, case_id in ids.items()}
    by_id = {c.id: c for c in cases}
    views = {case_id: blind_view(case, reverse[case_id], context_for(case.setup, case.proposal))
             for case_id, case in by_id.items()}
    out = label_dir(set_name, data)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ids.json").write_text(json.dumps(ids, indent=2) + "\n")
    template = (PROMPTS / "label.md").read_text()
    ordered = [views[case_id] for case_id in ids.values()]
    for number, start in enumerate(range(0, len(ordered), BATCH)):
        text = template.replace("{{GUIDE}}", guide_path.read_text().strip()).replace(
            "{{CASES}}", json.dumps(ordered[start:start + BATCH], indent=2))
        (out / f"batch_{number:02d}.prompt.md").write_text(text)
    if set_name == "test":
        sample = sample_for_owner(cases)
        (out / "owner_sample.json").write_text(json.dumps(sample, indent=2) + "\n")
        blind_order = sorted(sample, key=lambda case_id: reverse[case_id])
        (out / "owner_view.json").write_text(json.dumps([views[case_id] for case_id in blind_order], indent=2) + "\n")
    return len(ordered)


def reading_sheet(set_name: str, n: int = 20, context_for: ContextFor = seed_context, data: Path = sets.DATA) -> Path:
    """A Markdown sheet of `n` cases as the labeller will see them, for the owner to read before writing
    the labelling guide. Cases are in the blind, shuffled order, under blind ids; no labels."""
    cases = [c for c in load_unlabelled(set_name, data) if c.category in ("A", "D", "E", "F")]
    shuffled = sorted(cases, key=lambda c: c.id)
    random.Random(f"blind:{set_name}").shuffle(shuffled)
    lines = [f"# {set_name}: {min(n, len(shuffled))} cases as the labeller sees them", "",
             "Synthetic cases from eval/generate.py. No labels: read them, then write eval/prompts/label_guide.md.", ""]
    for index, case in enumerate(shuffled[:n]):
        context = context_for(case.setup, case.proposal)
        payee, history = context["counterparty"], context["payment_history"]
        bill = context.get("bill")
        changes = context.get("payment_method_history") or []
        confirmed = {a["subject"] for a in context.get("adjustments") or [] if a["kind"] == "confirmed_method_change"}
        lines += [
            f"## c{index:03d}",
            "",
            f"- Pays **{payee['name']}** {case.proposal.amount.amount / 100:,.2f} {case.proposal.amount.currency}"
            f" to method `{case.proposal.payment_method_id}`; payee created {payee['created_at'][:10]}",
            f"- History: {history['count']} payments"
            + (f", median {history['median_amount']['amount'] / 100:,.2f}" if history.get("median_amount") else ""),
            "- Method changes: " + ("; ".join(f"{c['change']} {c['changed_at'][:10]}"
                                              + (" (verified by the business's reviewer, call-back)"
                                                 if c["id"] in confirmed else "")
                                              for c in changes) or "none"),
            f"- Bill: " + (f"{bill['counterparty_name']}, {bill['amount']['amount'] / 100:,.2f}" if bill else "none named"),
            "",
            "Invoice text (untrusted):",
            "",
            *[f"> {line}" for line in ((bill or {}).get("document_excerpt") or "(none)").splitlines()],
            "",
            f"Agent's rationale (untrusted): {case.proposal.agent_rationale}",
            "",
        ]
    path = label_dir(set_name, data) / "reading.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def ai_label(set_name: str, client: Any = None, data: Path = sets.DATA) -> list[str]:
    """Label each exported batch with the AI labeller through the Anthropic API, offering no tools, and
    write ai/batch_NN.jsonl with its meta. A batch already labelled is kept, so a failure resumes.
    Returns the batches labelled now."""
    out = label_dir(set_name, data)
    ids: list[str] = list(json.loads((out / "ids.json").read_text()))
    (out / "ai").mkdir(exist_ok=True)
    if client is None:
        from zeta_one.risk import claude
        client = claude.client(timeout=600.0)
    done = []
    for prompt_path in sorted(out.glob("batch_*.prompt.md")):
        name = prompt_path.name.removesuffix(".prompt.md")
        answer_path = out / "ai" / f"{name}.jsonl"
        if answer_path.exists():
            continue
        number = int(name.removeprefix("batch_"))
        expected = ids[number * BATCH:(number + 1) * BATCH]
        with client.messages.stream(model=AI_SOURCE, max_tokens=AI_MAX_TOKENS, thinking={"type": "adaptive"},
                                    messages=[{"role": "user", "content": prompt_path.read_text()}]) as stream:
            response = stream.get_final_message()
        if response.stop_reason != "end_turn":
            raise LabelError(f"{name}: the labeller stopped with {response.stop_reason}")
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        rows = _answer_rows(text, name)
        if [row.get("id") for row in rows] != expected:
            raise LabelError(f"{name}: the answer's ids are not this batch's {len(expected)} cases in order")
        for row in rows:
            _check_label(row)
        sets.write_jsonl(answer_path, rows)
        usage = response.usage
        answer_path.with_suffix(".meta.json").write_text(json.dumps({
            "tool_calls": 0, "tools_offered": [], "route": "anthropic_api", "model": response.model,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
        }, indent=2) + "\n")
        done.append(name)
    return done


def _answer_rows(text: str, source: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise LabelError(f"{source}: a line is not JSON: {error}") from None
    return rows


def _blindness(set_name: str, data: Path) -> str:
    metas = [json.loads(path.read_text()) for path in sorted((label_dir(set_name, data) / "ai").glob("batch_*.meta.json"))]
    return API_BLINDNESS if metas and all(meta.get("route") == "anthropic_api" for meta in metas) else BLINDNESS


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
    adjudicated_path = out / "adjudicated.jsonl"
    adjudicated = ({_case_id(ids, row, "adjudicated.jsonl"): row for row in sets.read_jsonl(adjudicated_path)}
                   if adjudicated_path.exists() else {})
    for row in [*owner.values(), *adjudicated.values()]:
        _check_label(row)
    if set(adjudicated) - set(owner):
        raise LabelError("adjudicated.jsonl settles a case the owner did not label")

    cases, pairs = [], []
    for raw in sets.read_jsonl(data / set_name / "cases_unlabelled.jsonl"):
        case_id = raw["id"]
        if case_id not in ai and case_id not in owner:
            raise LabelError(f"{case_id} has no label")
        final = adjudicated.get(case_id) or owner.get(case_id) or ai[case_id]
        sources = [AI_SOURCE] * (case_id in ai) + ["owner"] * (case_id in owner)
        both = case_id in ai and case_id in owner
        agreed = ai[case_id]["expected"] == owner[case_id]["expected"] if both else None
        if both and raw["category"] in JUDGED_CATEGORIES:
            pairs.append((ai[case_id]["expected"], owner[case_id]["expected"]))
        settled = agreed is False or case_id in adjudicated
        provenance = LabelProvenance(sources=sources, agreed=agreed, adjudicated_by="owner" if settled else None)
        cases.append(Case.model_validate({**raw, "expected": final["expected"],
                                          "also_acceptable": final.get("also_acceptable", []),
                                          "label_provenance": provenance.model_dump()}).model_dump(mode="json"))
    sets.write_jsonl(data / set_name / "cases.jsonl", cases)
    agreement = stats.kappa_bootstrap([a for a, _ in pairs], [o for _, o in pairs]) if pairs else None
    paths = [out / "agreement.json"] + ([data / "agreement.json"] if set_name == "test" else [])
    for path in paths:
        if agreement:
            agreement["labeller_blindness"] = _blindness(set_name, data)
            agreement["adjudicated"] = len(adjudicated)
            agreement["adjudicated_to_ai"] = sum(adjudicated[c]["expected"] == ai[c]["expected"] for c in adjudicated
                                                 if c in ai)
            path.write_text(json.dumps(agreement, indent=2) + "\n")
        else:
            path.unlink(missing_ok=True)  # a relabel with no owner overlap must not leave old agreement behind
    return {"cases": len(cases), "agreement": agreement}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["export", "ai", "merge", "sheet"])
    parser.add_argument("set", choices=["dev", "test"])
    args = parser.parse_args(argv)
    if args.command == "sheet":
        print(f"wrote {reading_sheet(args.set)}")
    elif args.command == "export":
        print(f"{export(args.set)} cases exported")
    elif args.command == "ai":
        done = ai_label(args.set)
        print(f"labelled {', '.join(done) or 'nothing new'}")
    else:
        print(json.dumps(merge(args.set), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
