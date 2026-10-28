"""Record real engine runs into site/data/ for the static site (decision 0011).

    .venv/bin/python scripts/record_runs.py            # model tiers replay the fixtures' recorded answers
    .venv/bin/python scripts/record_runs.py --live     # escalating scenarios call the strong tier (paid)

Writes, in the demo API's shapes (docs/reference/demo-api.md):
    site/data/index.json                   what was recorded, when, with which versions
    site/data/scenarios/<name>.json         each scenario result, as POST /v1/scenarios/{name}/run returns it
    site/data/eval_report.json              a copy of data/eval/report.json, if it exists

Every file says it is recorded, and every payment in it is simulated. It writes nothing outside
site/data/.
"""

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zeta_one.contracts import POLICY_VERSION  # noqa: E402
from zeta_one.gateway import scenarios  # noqa: E402
from zeta_one.gateway.wiring import engine_version  # noqa: E402

OUT = ROOT / "site" / "data"
EVAL_REPORT = ROOT / "data" / "eval" / "report.json"


def record(out: Path = OUT, live_models: bool = False, eval_report: Path = EVAL_REPORT) -> dict:
    recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
    (out / "scenarios").mkdir(parents=True, exist_ok=True)
    items = []
    for name in scenarios.ORDER:
        result = scenarios.dump(scenarios.run(name, live_models=live_models))
        result["recorded"] = {"at": recorded_at, "live_models": live_models}
        (out / "scenarios" / f"{name}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        record = result["decision_record"]
        items.append({"name": name, "decision": record["decision"], "reasons": record["reasons"],
                      "illustrative": result["illustrative"], "replayed_stages": result["replayed_stages"]})
    has_report = eval_report.exists()
    if has_report:
        shutil.copyfile(eval_report, out / "eval_report.json")
    index = {
        "recorded_at": recorded_at,
        "recorded": True,
        "simulated": True,
        "engine_version": engine_version(),
        "policy_version": POLICY_VERSION,
        "live_models": live_models,
        "scenarios": items,
        "eval_report": "eval_report.json" if has_report else None,
        "note": "Recorded results of real engine runs on synthetic data. Payments are simulated. "
                + ("Escalating scenarios called the strong tier live." if live_models else
                   "Model tiers replay the fixtures' recorded answers, so those scenarios are marked illustrative."),
    }
    (out / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the strong tier for real (paid)")
    args = parser.parse_args(argv)
    index = record(live_models=args.live)
    for item in index["scenarios"]:
        print(f"{item['name']}: {item['decision']} {item['reasons']}" + (" (illustrative)" if item["illustrative"] else ""))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
