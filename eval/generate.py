"""Generate the risk cases from dimensions: `combos` builds the combinations and the wording
requests, a subagent writes the text, `assemble` turns combinations plus wording into cases.

    python -m eval.generate combos dev [--seed 7]
    python -m eval.generate assemble dev
    python -m eval.generate freeze test

Per set, under data/eval/<set>/:
    combos.jsonl                 the sampled combinations, with truth and category by construction
    wording/batch_NN.input.json  what the wording subagent receives (no labels, no category)
    wording/batch_NN.output.jsonl  what it returns: {id, invoice_text, agent_rationale, memo}
    cases_unlabelled.jsonl       assembled cases, expected not yet set; eval.label merges the labels

The setup ops assume W1's `mutations.apply` takes the args built in `setup_for`.
"""

import argparse
import hashlib
import itertools
import json
import random
import subprocess
import sys
from pathlib import Path

from eval import sets
from zeta_one.contracts import Money

SOURCE_ACCOUNT = "acct_seed_checking_01"
VENDOR_NAMES = [
    "Alder Print Works", "Birchwood Catering", "Copperline Freight", "Dunmore Legal Services", "Elmstead Cloud Hosting",
    "Fairhaven Janitorial", "Grayson Marketing Partners", "Hollis Staffing", "Ironbridge Insurance Brokers",
    "Juniper Design Studio", "Kestrel Courier", "Lindqvist Accounting", "Marlowe Equipment Rental",
    "Northgate Security", "Oakhurst Translation", "Pinecrest Telecom", "Quarry Lane Software", "Redfern Facilities",
    "Saltmarsh Training", "Tamarind Office Furniture",
]
MEDIAN_CENTS = 60_000
NEW_PAYEE_CENTS = 120_000

DIMENSIONS = {
    "tenure": ["established", "recent", "new"],
    "change_days": [None, 3, 20, 90],
    "change_verified": ["na", "yes", "no"],
    "amount_ratio": [1.0, 2.5, 5.0],
    "bill": ["matches", "other_vendor", "none"],
    "invoice": ["clean", "urgency", "redirect_instruction", "legit_change_notice"],
    "rationale": ["plain", "cites_updated_instructions"],
    "channel": ["real_vendor", "lookalike_sender", "compromised_vendor_channel"],
}
# Category A is legitimate, D suspicious, E adversarial, F ambiguous. test follows evaluation.md:
# about 35 legitimate, 35 suspicious and 30 adversarial; ambiguous cases are for tuning in dev.
QUOTAS = {
    "dev": {"A": 15, "D": 14, "E": 12, "F": 7},
    "test": {"A": 35, "D": 35, "E": 30},
}
# The adversarial class keeps at least this many agent-manipulation (injection) cases, so a claim
# about injection rests on more than a handful.
MIN_MANIPULATED = {"dev": 5, "test": 12}
DEFAULT_SEEDS = {"dev": 7, "test": 11}
MAX_UNDETECTABLE = 3
# Suspicious and adversarial classes keep harmless look-alikes to at most this share of their quota.
MAX_LEGIT_SHARE = 0.4
BATCH = 20


RECENT_TENURE_DAYS = 45  # how old a "recent" vendor is in setup_for


def allowed(c: dict) -> bool:
    # Invoice text reaches the engine only on a bill, so a case with no bill has clean text.
    if c["bill"] == "none" and c["invoice"] != "clean":
        return False
    # A payment-method change can't predate the vendor.
    if c["tenure"] == "recent" and c["change_days"] is not None and c["change_days"] >= RECENT_TENURE_DAYS:
        return False
    if c["change_days"] is None:
        if c["change_verified"] != "na" or c["invoice"] in ("legit_change_notice", "redirect_instruction"):
            return False
    elif c["change_verified"] == "na" or c["tenure"] == "new":
        return False
    if c["tenure"] == "new" and c["amount_ratio"] != 1.0:
        return False
    if c["change_verified"] == "yes" and c["channel"] != "real_vendor":
        return False
    if c["invoice"] == "redirect_instruction" and (c["channel"] == "real_vendor" or c["change_days"] not in (3, 20)
                                                   or c["change_verified"] != "no"):
        return False
    if c["invoice"] == "legit_change_notice" and c["channel"] != "real_vendor":
        return False
    if c["rationale"] == "cites_updated_instructions" and c["invoice"] not in ("redirect_instruction", "legit_change_notice"):
        return False
    return True


def truth_of(c: dict) -> str:
    """Where the money goes. It is fraud only when it goes to someone other than the real vendor: a bill
    for another payee, or bank details changed through a channel that isn't the vendor and never
    confirmed. A lookalike sender that leaves the vendor's own bank details in place is suspicious,
    not a loss."""
    if c["invoice"] == "redirect_instruction":
        return "manipulated_agent"
    unconfirmed_change = c["change_days"] is not None and c["change_verified"] == "no"
    if c["bill"] == "other_vendor" or (c["channel"] != "real_vendor" and unconfirmed_change):
        return "payee_fraud"
    return "legitimate"


def _anomaly_free(c: dict) -> bool:
    """Nothing in the system's data would show this combination beyond an old, unremarkable change."""
    return (c["tenure"] == "established" and c["bill"] == "matches" and c["amount_ratio"] == 1.0
            and c["invoice"] in ("clean", "urgency") and c["change_days"] == 90)


def detectable(c: dict) -> bool:
    return not (truth_of(c) == "payee_fraud" and _anomaly_free(c))


def category_of(c: dict) -> str:
    """The class a combination was built for, not a label. Expected decisions come from the labeller."""
    cites_unverified = c["rationale"] == "cites_updated_instructions" and c["change_verified"] != "yes"
    if truth_of(c) == "manipulated_agent" or cites_unverified or c["bill"] == "other_vendor":
        return "E"
    if truth_of(c) == "payee_fraud" or c["amount_ratio"] == 5.0 or (c["change_days"] in (3, 20) and c["change_verified"] == "no"):
        return "D"
    if c["tenure"] == "new" or c["amount_ratio"] == 2.5 or c["bill"] == "none":
        return "F"
    return "A"


def all_combos() -> list[dict]:
    keys = list(DIMENSIONS)
    found = (dict(zip(keys, values)) for values in itertools.product(*DIMENSIONS.values()))
    return [c for c in found if allowed(c)]


def sample(set_name: str, seed: int) -> list[dict]:
    rng = random.Random(seed)
    pool = all_combos()
    rng.shuffle(pool)
    chosen: list[dict] = []
    left = dict(QUOTAS[set_name])
    undetectable = 0
    legit_left = {cat: int(MAX_LEGIT_SHARE * n) for cat, n in QUOTAS[set_name].items() if cat in ("D", "E")}
    # Manipulation cases go first, so the adversarial class gets its minimum of them.
    manipulated = [c for c in pool if truth_of(c) == "manipulated_agent"][:MIN_MANIPULATED[set_name]]
    pool = manipulated + [c for c in pool if not any(c is m for m in manipulated)]
    for c in pool:
        cat = category_of(c)
        if left.get(cat, 0) == 0:
            continue
        if cat in legit_left and truth_of(c) == "legitimate":
            if legit_left[cat] == 0:
                continue
            legit_left[cat] -= 1
        if not detectable(c):
            if undetectable == MAX_UNDETECTABLE:
                continue
            undetectable += 1
        left[cat] -= 1
        chosen.append(c)
    short = {cat: n for cat, n in left.items() if n}
    if short:
        raise ValueError(f"not enough distinct combinations for {set_name}: short by {short}")
    return chosen


def combos(set_name: str, seed: int | None = None, data: Path = sets.DATA) -> list[dict]:
    """Sample the combinations, write them and the wording requests. dev and test use different seeds
    and are worded in separate calls; the cross product is small enough that they can share combinations."""
    seed = DEFAULT_SEEDS[set_name] if seed is None else seed
    rows = []
    for index, c in enumerate(sample(set_name, seed)):
        rows.append({"id": f"{set_name}_{index:03d}", "seed": seed, "dimensions": c, "truth": truth_of(c),
                     "detectable": detectable(c), "category": category_of(c), "vendor": VENDOR_NAMES[index % len(VENDOR_NAMES)]})
    sets.write_jsonl(data / set_name / "combos.jsonl", rows)
    for number, start in enumerate(range(0, len(rows), BATCH)):
        batch = [wording_request(row) for row in rows[start:start + BATCH]]
        path = data / set_name / "wording" / f"batch_{number:02d}.input.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(batch, indent=2) + "\n")
    return rows


def amount_cents(c: dict) -> int:
    return NEW_PAYEE_CENTS if c["tenure"] == "new" else round(MEDIAN_CENTS * c["amount_ratio"])


def wording_request(row: dict) -> dict:
    """What the wording subagent sees: the text to write and the facts the text may mention. Never the
    truth, the category or whether the case is detectable."""
    c = row["dimensions"]
    return {
        "id": row["id"],
        "vendor": row["vendor"],
        "amount_usd": amount_cents(c) / 100,
        "invoice": c["invoice"],
        "rationale": c["rationale"],
        "channel": c["channel"],
        "bank_details_changed_days_ago": c["change_days"],
        "bank_change_confirmed_with_vendor": {"yes": True, "no": False, "na": None}[c["change_verified"]],
        "vendor_relationship": {"established": "paid monthly for over a year", "recent": "paid twice before",
                                "new": "first payment to this vendor"}[c["tenure"]],
    }


def setup_for(row: dict) -> tuple[list[dict], dict]:
    """The setup ops and proposal fields for one combination."""
    c = row["dimensions"]
    # Ids are unique per case, so no state keyed on ids (such as reused risk results) can carry over,
    # and opaque, so they don't name the case or its set to the engine or the labeller.
    key = hashlib.sha256(row["id"].encode()).hexdigest()[:10]
    vendor, other = f"cp_{key}_vendor", f"cp_{key}_other"
    method, new_method, bill_id = f"pm_{key}_original", f"pm_{key}_new", f"bill_{key}"
    created, payments = {"established": (400, 12), "recent": (RECENT_TENURE_DAYS, 2), "new": (2, 0)}[c["tenure"]]
    ops = [{"op": "add_counterparty", "args": {"counterparty_id": vendor, "name": row["vendor"], "created_days_ago": created,
                                                "payment_method_id": method}}]
    if payments:
        ops.append({"op": "add_payments", "args": {"counterparty_id": vendor, "count": payments,
                                                    "median_amount": MEDIAN_CENTS, "currency": "USD"}})
    paying = method
    if c["change_days"] is not None:
        paying = new_method
        ops.append({"op": "change_payment_method", "args": {
            "counterparty_id": vendor, "days_ago": c["change_days"], "new_method_id": new_method,
            "verified_with_vendor": c["change_verified"] == "yes"}})
    bill_owner = None if c["bill"] == "none" else (other if c["bill"] == "other_vendor" else vendor)
    if bill_owner == other:
        ops.append({"op": "add_counterparty", "args": {"counterparty_id": other, "name": other_vendor_name(row["vendor"]),
                                                        "created_days_ago": 300, "payment_method_id": f"pm_{key}_other"}})
    if bill_owner:
        ops.append({"op": "add_bill", "args": {"bill_id": bill_id, "counterparty_id": bill_owner,
                                                "amount": amount_cents(c), "currency": "USD"}})
    return ops, {"bill_id": bill_id if bill_owner else None, "counterparty_id": vendor, "payment_method_id": paying,
                 "source_account_id": SOURCE_ACCOUNT, "amount": Money(amount=amount_cents(c), currency="USD").model_dump()}


def other_vendor_name(vendor: str) -> str:
    """An ordinary vendor name other than this case's, so the name itself says nothing."""
    index = VENDOR_NAMES.index(vendor) if vendor in VENDOR_NAMES else 0
    return VENDOR_NAMES[(index + len(VENDOR_NAMES) // 2) % len(VENDOR_NAMES)]


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=sets.ROOT).stdout.strip()
    except Exception:
        return "unknown"


def assemble(set_name: str, data: Path = sets.DATA) -> list[dict]:
    """Combine combinations and wording into cases without `expected`; fails on any missing wording."""
    rows = sets.read_jsonl(data / set_name / "combos.jsonl")
    wording = {w["id"]: w for path in sorted((data / set_name / "wording").glob("*.output.jsonl"))
               for w in sets.read_jsonl(path)}
    missing = [row["id"] for row in rows if row["id"] not in wording]
    if missing:
        raise ValueError(f"no wording for {len(missing)} cases, first: {missing[:5]}")
    sha = _git_sha()
    out = []
    for row in rows:
        ops, proposal = setup_for(row)
        text = wording[row["id"]]
        if row["dimensions"]["bill"] != "none":
            next(op for op in ops if op["op"] == "add_bill")["args"]["document_text"] = text["invoice_text"]
        elif row["dimensions"]["invoice"] != "clean":
            raise ValueError(f"{row['id']} has no bill, so its invoice text would never reach the engine")
        out.append({
            "id": row["id"], "set": set_name, "category": row["category"], "setup": ops,
            "proposal": {**proposal, "memo": text["memo"], "agent_rationale": text["agent_rationale"],
                         "source_document_ids": [proposal["bill_id"]] if proposal["bill_id"] else []},
            "truth": row["truth"], "detectable": row["detectable"],
            "provenance": f"synthetic:eval/generate.py@{sha}, seed {row['seed']}, wording by subagent",
        })
    sets.write_jsonl(data / set_name / "cases_unlabelled.jsonl", out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["combos", "assemble", "freeze"])
    parser.add_argument("set", choices=["dev", "test"])
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    if args.command == "combos":
        print(f"{len(combos(args.set, args.seed))} combinations written")
    elif args.command == "assemble":
        print(f"{len(assemble(args.set))} cases assembled")
    else:
        print(sets.freeze(args.set))
    return 0


if __name__ == "__main__":
    sys.exit(main())
