"""Record synthetic workspace recipes through the real deterministic engine, without model calls."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def record(out: Path = ROOT / "site" / "workspace" / "data.json") -> dict:
    from zeta_one.demo.workspace import export_state

    state = export_state()
    state["mode"] = "preview"
    for payment in state["payments"]:
        payment["provenance"] += " Recorded deterministic result; no models called. Browsing does not run a fresh assessment."
    state["recorded"] = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "synthetic": True,
        "simulated": True,
        "live_models": False,
        "source": "Versioned workspace recipes assessed by the real deterministic engine; no fixture replay.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    return state


if __name__ == "__main__":
    result = record()
    print(f"Recorded {len(result['payments'])} synthetic, simulated workspace examples without model calls.")
