"""Run a set of cases through a configuration and write one JSON line per case.

    python -m eval.run --set dev --config engineered [--backend replay] [--workers 4]

Configurations: always_allow and always_challenge are trivial baselines that never touch the engine;
rules runs tier 0 only; engineered adds the strong model on engineered escalation (decision 0009);
strong runs the model on every request. The models see only the proposal and its context.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval import sets
from eval.backends import Backend, Outcome, Unsupported, get_backend
from zeta_one.contracts import Case, Configuration

RESULTS = sets.DATA / "results"
CONFIGS: dict[str, Configuration | None] = {
    "always_allow": None,
    "always_challenge": None,
    "rules": Configuration(tiers=["tier0"], escalation="none"),
    "engineered": Configuration(tiers=["tier0", "strong"], escalation="engineered"),
    "strong": Configuration(tiers=["tier0", "strong"], escalation="always"),
}
BASELINES = {"always_allow": "allow", "always_challenge": "challenge"}


def result_path(set_name: str, config: str, results: Path = RESULTS) -> Path:
    return results / f"{set_name}-{config}.jsonl"


def _row(case: Case, config: str, outcome: Outcome | None, error: str | None) -> dict:
    row = {
        "case_id": case.id, "set": case.set, "category": case.category, "config": config,
        "truth": case.truth, "detectable": case.detectable, "expected": case.expected,
        "also_acceptable": case.also_acceptable, "not_run": error,
    }
    if outcome is None:
        return {**row, "decision": None, "correct": None, "acceptable": None}
    row["decision"] = outcome.decision
    row["correct"] = outcome.decision == case.expected
    row["acceptable"] = row["correct"] or outcome.decision in case.also_acceptable
    row["stable"] = len(set(outcome.decisions)) <= 1 if outcome.decisions else None
    row["model_calls"] = outcome.model_calls
    if outcome.record is not None:
        row["record"] = outcome.record.model_dump(mode="json", by_alias=True)
    return row


def run_case(case: Case, config: str, backend: Backend) -> dict:
    if config in BASELINES:
        return _row(case, config, Outcome(decision=BASELINES[config]), None)
    try:
        return _row(case, config, backend.run(case, CONFIGS[config]), None)
    except Unsupported as reason:
        return _row(case, config, None, str(reason))


def run_set(set_name: str, config: str, backend: Backend, workers: int = 4, data: Path = sets.DATA,
            results: Path = RESULTS) -> list[dict]:
    if config not in CONFIGS:
        raise ValueError(f"unknown configuration {config!r}; choose from {list(CONFIGS)}")
    cases = sets.load_set(set_name, data)
    sets.check_frozen(set_name, cases, data)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda case: run_case(case, config, backend), cases))
    path = result_path(set_name, config, results)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", required=True, choices=sets.SETS, dest="set_name")
    parser.add_argument("--config", required=True, choices=list(CONFIGS))
    parser.add_argument("--backend", default="replay")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    rows = run_set(args.set_name, args.config, get_backend(args.backend), args.workers)
    ran = [row for row in rows if not row["not_run"]]
    print(f"{args.set_name}/{args.config}: {len(ran)} run, {len(rows) - len(ran)} not run, "
          f"{sum(bool(r['acceptable']) for r in ran)} acceptable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
