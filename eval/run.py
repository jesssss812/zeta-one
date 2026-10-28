"""Run a set of cases through a configuration and write one JSON line per case.

    python -m eval.run --set dev --config engineered [--backend replay] [--workers 4]
    python -m eval.run ... --backend <paid> --live --max-usd 5     # a backend that calls a paid model

Configurations: always_allow and always_challenge are trivial baselines that never touch the engine;
rules runs tier 0 only; engineered adds the strong model on engineered escalation (decision 0009);
jev puts Jev between them, so the strong model runs only on Jev's rule (decision 0007); strong runs
the model on every request. The models see only the proposal and its context.

Each row records the backend, the set's hash at run time and whether its latency is measured, so the
report reads them from the results rather than from its own arguments. A case that raises is
recorded as not run; the results file is always written. A paid backend runs only with `live` and a
budget: once the recorded cost of every send reaches `max_usd`, the remaining cases are not run.
Cases already running finish, so the spend can pass the budget by up to `workers` cases.
"""

import argparse
import json
import math
import sys
import threading
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
    "jev": Configuration(tiers=["tier0", "cheap", "strong"], escalation="jev"),
    "strong": Configuration(tiers=["tier0", "strong"], escalation="always"),
}
BASELINES = {"always_allow": "allow", "always_challenge": "challenge"}


def result_path(set_name: str, config: str, results: Path = RESULTS) -> Path:
    return results / f"{set_name}-{config}.jsonl"


class BudgetRequired(ValueError):
    pass


def _row(case: Case, config: str, outcome: Outcome | None, error: str | None) -> dict:
    row = {
        "case_id": case.id, "set": case.set, "category": case.category, "config": config,
        "truth": case.truth, "detectable": case.detectable, "expected": case.expected,
        "also_acceptable": case.also_acceptable, "not_run": error,
    }
    if outcome is None:
        return {**row, "decision": None, "correct": None, "acceptable": None, "stable": None}
    # A case that sends its request more than once passes only if every send got the same decision,
    # and a case that names its expected reason passes only if the decision carries it.
    row["stable"] = len(set(outcome.decisions)) <= 1 if outcome.decisions else None
    steady = row["stable"] is not False
    reasons = outcome.record.reasons if outcome.record is not None else None
    row["reason_ok"] = None if case.expected_reason is None or reasons is None else case.expected_reason in reasons
    sound = steady and row["reason_ok"] is not False
    row["decision"] = outcome.decision
    row["correct"] = outcome.decision == case.expected and sound
    row["acceptable"] = (outcome.decision == case.expected or outcome.decision in case.also_acceptable) and sound
    row["model_calls"] = outcome.model_calls
    row["cost_usd"] = outcome.cost_usd
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
    except Exception as error:  # one broken case must not lose the others' results, or money spent on them
        return _row(case, config, None, f"error: {type(error).__name__}: {error}")


class _Budget:
    def __init__(self, max_usd: float | None):
        self.max_usd, self.spent, self._lock = max_usd, 0.0, threading.Lock()

    def exhausted(self) -> bool:
        with self._lock:
            return self.max_usd is not None and self.spent >= self.max_usd

    def add(self, row: dict) -> None:
        """Every send's cost, not only the judged record's: a repeat's first send is the one that paid."""
        if row.get("cost_usd") is not None:
            spent = row["cost_usd"]
        else:
            spent = ((row.get("record") or {}).get("cost") or {}).get("usd") or 0.0
        with self._lock:
            self.spent += spent


def run_set(set_name: str, config: str, backend: Backend, workers: int = 4, data: Path = sets.DATA,
            results: Path = RESULTS, live: bool = False, max_usd: float | None = None) -> list[dict]:
    if config not in CONFIGS:
        raise ValueError(f"unknown configuration {config!r}; choose from {list(CONFIGS)}")
    models = config not in BASELINES and any(tier != "tier0" for tier in CONFIGS[config].tiers)
    paid_for = getattr(backend, "paid_for", None)
    paid = models and (paid_for(CONFIGS[config]) if paid_for else getattr(backend, "paid", True))
    if paid and (not live or max_usd is None):
        raise BudgetRequired(f"the {backend.name} backend calls a paid model: pass live=True and max_usd")
    if max_usd is not None and not (math.isfinite(max_usd) and max_usd > 0):
        raise BudgetRequired(f"max_usd must be a positive number, not {max_usd!r}")
    cases = sets.load_set(set_name, data)
    sets.check_frozen(set_name, cases, data)
    digest = sets.set_hash(cases)
    budget = _Budget(max_usd if paid else None)

    def one(case: Case) -> dict:
        if budget.exhausted():
            row = _row(case, config, None, f"budget: ${budget.max_usd:.2f} spent before this case")
        else:
            row = run_case(case, config, backend)
            budget.add(row)
        return {**row, "backend": backend.name, "set_hash": digest,
                "measured_latency": bool(getattr(backend, "measures_latency", False))}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, cases))
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
    parser.add_argument("--live", action="store_true", help="allow a backend that calls a paid model")
    parser.add_argument("--max-usd", type=float, help="stop starting cases once the recorded cost reaches this")
    args = parser.parse_args(argv)
    rows = run_set(args.set_name, args.config, get_backend(args.backend), args.workers, live=args.live,
                   max_usd=args.max_usd)
    ran = [row for row in rows if not row["not_run"]]
    print(f"{args.set_name}/{args.config}: {len(ran)} run, {len(rows) - len(ran)} not run, "
          f"{sum(bool(r['acceptable']) for r in ran)} acceptable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
