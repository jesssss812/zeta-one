"""Run the feedback loop end to end on the real stages, in a sandbox, and record it (decisions 0012, 0013).

    .venv/bin/python scripts/demo_loop.py            # rules only: no model call
    .venv/bin/python scripts/demo_loop.py --live     # engineered: escalations call the strong tier (paid)

The story is in zeta_one/demo/story.py. Writes site/data/loop.json, marked recorded and simulated.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zeta_one.contracts import POLICY_VERSION  # noqa: E402
from zeta_one.demo.story import Story  # noqa: E402
from zeta_one.gateway.wiring import engine_version  # noqa: E402

OUT = ROOT / "site" / "data" / "loop.json"
TOKEN = "demo-loop-admin-token"


def run(live_models: bool = False) -> dict:
    story = Story(TOKEN, live_models=live_models)
    try:
        steps = story.run_all()
    finally:
        story.close()
    return {
        "recorded": True, "simulated": True, "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine_version": engine_version(), "policy_version": POLICY_VERSION, "live_models": live_models,
        "note": "A recorded run of the feedback loop on the real engine and synthetic data. Payments are simulated."
                + ("" if live_models else " Models were off: escalations show where a model would review."),
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="engineered configuration: calls the strong tier (paid)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    loop = run(live_models=args.live)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(loop, indent=2, sort_keys=True, default=str) + "\n")
    for number, entry in enumerate(loop["steps"], 1):
        decision = entry.get("decision")
        detail = f" -> {decision['decision']} {decision['reasons']}" if decision else ""
        print(f"{number}. {entry['title']}{detail}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
