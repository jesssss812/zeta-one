"""Where each set of cases lives, how it is hashed and how `test` is frozen.

deterministic: eval/cases.py. dev: the demo cases there plus data/eval/dev/cases.jsonl. test:
data/eval/test/cases.jsonl. hard: data/eval/hard/*.jsonl, written by the owner. feedback:
data/eval/feedback/cases.jsonl, from verified outcomes (eval/feedback.py).
"""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from eval import cases as hand_cases
from zeta_one.contracts import Case

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval"
SETS = ("deterministic", "dev", "test", "hard", "feedback")


class FrozenSetChanged(RuntimeError):
    pass


def set_dir(name: str) -> Path:
    return DATA / name


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def load_set(name: str, data: Path = DATA) -> list[Case]:
    if name == "deterministic":
        return hand_cases.deterministic_cases()
    if name not in SETS:
        raise ValueError(f"unknown set {name!r}; choose from {SETS}")
    files = sorted((data / name).glob("*.jsonl")) if name == "hard" else [data / name / "cases.jsonl"]
    loaded = [Case.model_validate(row) for file in files if file.exists() for row in read_jsonl(file)]
    if name == "dev":
        loaded = [case for case in hand_cases.demo_cases() if case.set == "dev"] + loaded
    ids = [case.id for case in loaded]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate case ids in {name}")
    wrong = [case.id for case in loaded if case.set != name]
    if wrong:
        raise ValueError(f"cases in {name} that say another set: {wrong}")
    return loaded


def set_hash(cases: list[Case]) -> str:
    """sha256 over the cases in id order, canonical JSON; provenance and label provenance included."""
    payload = json.dumps([c.model_dump(mode="json") for c in sorted(cases, key=lambda c: c.id)], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class AlreadyFrozen(RuntimeError):
    pass


def freeze(name: str, data: Path = DATA, force: bool = False, note: str | None = None) -> str:
    """Record the set's hash, and when and at which commit it was frozen; later runs refuse a set that
    no longer matches. A frozen set is not re-frozen unless `force`, and a forced re-freeze records why:
    `test` is frozen before its first scored run and never tuned on."""
    path = data / name / "frozen.sha256"
    if path.exists() and not force:
        raise AlreadyFrozen(f"{name} is already frozen; re-freezing needs force and a note saying why")
    if force and path.exists() and not note:
        raise AlreadyFrozen("a forced re-freeze needs a note saying why")
    digest = set_hash(load_set(name, data))
    path.write_text(digest + "\n")
    meta = {"sha256": digest, "frozen_at": datetime.now(UTC).isoformat(), "commit": _git_sha(), "note": note,
            **engine_inputs()}
    # Not *.jsonl: the hard set's loader reads every .jsonl in its folder.
    with (data / name / FREEZE_LOG).open("a") as log:
        log.write(json.dumps(meta, sort_keys=True) + "\n")
    return digest


FREEZE_LOG = "frozen.log"


def engine_inputs() -> dict[str, str]:
    """What else a frozen set is scored against: the seed's version and tier 0's frozen lexicon."""
    from zeta_one.rho.snapshot import Store
    from zeta_one.risk.features import INSTRUCTION_PATTERN_LEXICON

    with Store() as store:
        seed_version = store.seed_version
    lexicon = hashlib.sha256(json.dumps(INSTRUCTION_PATTERN_LEXICON).encode()).hexdigest()
    return {"seed_version": seed_version, "lexicon_sha256": lexicon}


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=ROOT).stdout.strip()
    except Exception:
        return "unknown"


def check_frozen(name: str, cases: list[Case], data: Path = DATA) -> str | None:
    """The frozen hash if the set has one. `test` must have one before it is scored."""
    path = data / name / "frozen.sha256"
    if not path.exists():
        if name == "test":
            raise FrozenSetChanged("test is not frozen: run `python -m eval.generate freeze test` after labelling")
        return None
    if path.read_text().strip() != set_hash(cases):
        raise FrozenSetChanged(f"{name} changed since it was frozen")
    log = data / name / FREEZE_LOG
    if log.exists():
        last = json.loads(log.read_text().splitlines()[-1])
        current = engine_inputs()
        changed = [key for key, value in current.items() if key in last and last[key] != value]
        if changed:
            raise FrozenSetChanged(f"{name} was frozen against a different {', '.join(changed)}")
    return path.read_text().strip()
