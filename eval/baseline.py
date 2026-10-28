"""Keep a set's current results as a named baseline, and compare later runs with it.

    python -m eval.baseline snapshot dev 2026-10-28    # data/eval/baselines/dev-2026-10-28/
    python -m eval.baseline compare dev 2026-10-28     # every case whose decision changed since

Results under data/eval/results/ are rewritten by each run and not committed; a baseline keeps one
compact row per case and configuration (label, decision, reasons, tiers run, cost, versions) and the
report as it stood, so it can be committed and compared after tuning.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from eval import sets
from eval.run import RESULTS

BASELINES = sets.DATA / "baselines"
REPORT = sets.DATA / "report.md"


def compact(row: dict) -> dict:
    record = row.get("record") or {}
    risk = record.get("risk") or {}
    return {
        "config": row["config"], "case_id": row["case_id"], "category": row["category"], "truth": row["truth"],
        "expected": row["expected"], "also_acceptable": row["also_acceptable"], "decision": row["decision"],
        "acceptable": row["acceptable"], "not_run": row["not_run"], "reasons": record.get("reasons"),
        "tiers_run": risk.get("tiers_run"), "level": risk.get("level"),
        "floor": (risk.get("floor") or {}).get("flags"), "lowered": bool(risk.get("lowered")),
        "model_calls": row.get("model_calls"), "cost_usd": row.get("cost_usd"),
        "engine_version": record.get("engine_version"), "policy_version": record.get("policy_version"),
        "set_hash": row.get("set_hash"),
    }


def snapshot(set_name: str, name: str, results: Path = RESULTS, out: Path = BASELINES, report: Path = REPORT) -> Path:
    """Write every result of `set_name` as one baseline; refuses to overwrite an existing one."""
    target = out / f"{set_name}-{name}"
    if target.exists():
        raise FileExistsError(f"{target} exists: a baseline is a record, so pick a new name")
    rows = [compact(row) for path in sorted(results.glob(f"{set_name}-*.jsonl")) for row in sets.read_jsonl(path)]
    if not rows:
        raise FileNotFoundError(f"no results for {set_name} under {results}")
    target.mkdir(parents=True)
    sets.write_jsonl(target / "decisions.jsonl", rows)
    if report.exists():
        shutil.copyfile(report, target / "report.md")
    return target


def compare(set_name: str, name: str, results: Path = RESULTS, out: Path = BASELINES) -> list[dict]:
    """Each case and configuration whose decision differs from the baseline, with both answers."""
    before = {(row["config"], row["case_id"]): row for row in sets.read_jsonl(out / f"{set_name}-{name}" / "decisions.jsonl")}
    changes = []
    for path in sorted(results.glob(f"{set_name}-*.jsonl")):
        for row in map(compact, sets.read_jsonl(path)):
            old = before.get((row["config"], row["case_id"]))
            if old and (old["decision"], old["acceptable"]) != (row["decision"], row["acceptable"]):
                changes.append({"config": row["config"], "case_id": row["case_id"], "expected": row["expected"],
                                "before": old["decision"], "after": row["decision"],
                                "now_acceptable": row["acceptable"]})
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["snapshot", "compare"])
    parser.add_argument("set", choices=sets.SETS)
    parser.add_argument("name")
    args = parser.parse_args(argv)
    if args.command == "snapshot":
        print(f"wrote {snapshot(args.set, args.name)}")
    else:
        for change in compare(args.set, args.name):
            print(json.dumps(change))
    return 0


if __name__ == "__main__":
    sys.exit(main())
