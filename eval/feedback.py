"""Turn verified outcomes from the gateway's ledger into evaluation cases (decision 0012).

    python -m eval.feedback [--db data/zeta.db]

Writes data/eval/feedback/cases.jsonl: one case per real decision whose latest verified outcome is a
finding, labelled by that finding, with the outcome's provenance. Claims (a customer report, no
check) are left out, as are sandbox scenario runs and requests that never parsed into a proposal.
A case replays the proposal through the real backend on the seed; it does not restore the context
as it was at decision time.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from eval import sets
from zeta_one import db
from zeta_one.contracts import Case, LabelProvenance, Proposal
from zeta_one.gateway.ledger import Ledger

# Finding -> (category, expected, also acceptable)
LABELS = {
    "legitimate": ("A", "allow", ["challenge"]),
    "payee_fraud": ("D", "block", ["challenge"]),
    "manipulated_agent": ("E", "block", ["challenge"]),
    "unauthorized": ("B", "block", []),
}


def cases_from(connection: sqlite3.Connection) -> list[Case]:
    ledger = Ledger(connection)
    rows = connection.execute(
        "SELECT d.decision_id, p.proposal FROM decisions d JOIN payments p ON p.decision_id = d.decision_id "
        "ORDER BY d.created_at, d.rowid").fetchall()
    cases = []
    for decision_id, proposal in rows:
        record = ledger.decision(decision_id)
        if record.get("sandbox"):
            continue
        verified = [outcome for outcome in record.get("outcomes", []) if outcome.get("verified")]
        if not verified:
            continue
        outcome = verified[-1]
        category, expected, acceptable = LABELS[outcome["finding"]]
        cases.append(Case(
            id=f"feedback_{decision_id}", set="feedback", category=category,
            proposal=Proposal.model_validate_json(proposal),
            truth=outcome["finding"], expected=expected, also_acceptable=acceptable,
            label_provenance=LabelProvenance(sources=[f"verified outcome by {outcome['by']}"], agreed=None),
            provenance=(f"feedback: decision {decision_id} ({record['decision']}), {outcome['finding']} verified by "
                        f"{outcome['verification']} on {outcome['at']}; replayed on the seed"),
        ))
    return cases


def export(connection: sqlite3.Connection, data: Path = sets.DATA) -> list[Case]:
    cases = cases_from(connection)
    sets.write_jsonl(data / "feedback" / "cases.jsonl", [case.model_dump(mode="json") for case in cases])
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=db.DEFAULT_PATH)
    args = parser.parse_args(argv)
    if not args.db.exists():
        raise SystemExit(f"no gateway database at {args.db}")
    cases = export(db.connect(args.db))
    print(json.dumps({"feedback_cases": len(cases), "by_finding": {
        finding: sum(case.truth == finding for case in cases) for finding in LABELS}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
