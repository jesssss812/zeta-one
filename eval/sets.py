"""Where each set of cases lives, how it is hashed and how `test` is frozen.

deterministic: eval/cases.py. dev: the demo cases there plus data/eval/dev/cases.jsonl. test:
data/eval/test/cases.jsonl. hard: data/eval/hard/*.jsonl, written by the owner.
"""

import hashlib
import json
from pathlib import Path

from eval import cases as hand_cases
from zeta_one.contracts import Case

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval"
SETS = ("deterministic", "dev", "test", "hard")


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


def freeze(name: str, data: Path = DATA) -> str:
    """Record the set's hash; later runs refuse a set that no longer matches."""
    digest = set_hash(load_set(name, data))
    (data / name / "frozen.sha256").write_text(digest + "\n")
    return digest


def check_frozen(name: str, cases: list[Case], data: Path = DATA) -> str | None:
    """The frozen hash if the set has one. `test` must have one before it is scored."""
    path = data / name / "frozen.sha256"
    if not path.exists():
        if name == "test":
            raise FrozenSetChanged("test is not frozen: run `python -m eval.generate freeze test` after labelling")
        return None
    if path.read_text().strip() != set_hash(cases):
        raise FrozenSetChanged(f"{name} changed since it was frozen")
    return path.read_text().strip()
