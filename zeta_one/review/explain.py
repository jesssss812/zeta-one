"""A decision in one line a reviewer can act on, built from the evidence record alone (no model).

The three questions stay separate (AGENTS.md rule 6): who is acting, whether it was authorized, and
what about the payment needs attention. Each answer carries the record ids that show it.
"""

from typing import Any

ACTIONS = {"allow": "Paid", "challenge": "Confirm before paying", "block": "Blocked"}
# How many times the vendor's usual amount reads as unusual.
UNUSUAL_RATIO = 1.5


def money(amount: dict[str, Any] | None) -> str:
    if not amount:
        return "?"
    value = f"{amount['amount'] / 100:,.2f}"
    return f"${value}" if amount.get("currency") == "USD" else f"{value} {amount.get('currency', '')}".strip()


def summary(record: dict[str, Any]) -> dict[str, Any]:
    """The inbox row and headline for one served evidence record."""
    proposal, context = record.get("proposal") or {}, record.get("context") or {}
    risk = record.get("risk") or {}
    # Each question is asked only once the one before it passed, as the engine does.
    parts = [_identity(record.get("identity") or {})]
    if parts[-1]["ok"]:
        parts.append(_authorization(record.get("authorization") or {}, proposal))
    if parts[-1]["ok"]:
        parts.append(_risk(risk))
    outcomes = record.get("outcomes") or []
    latency = record.get("latency_ms") or {}
    return {
        "decision_id": record["decision_id"],
        "created_at": record.get("created_at"),
        "decision": record["decision"],
        "action": ACTIONS.get(record["decision"], record["decision"]),
        "vendor": (context.get("counterparty") or {}).get("name") or proposal.get("counterparty_id") or "Unknown payee",
        "amount": proposal.get("amount"),
        "status": (record.get("execution") or {}).get("status"),
        "sandbox": bool(record.get("sandbox")),
        "headline": " · ".join(part["text"] for part in parts),
        "parts": parts,
        "stages": {name: ms for name, ms in latency.items() if name != "total"},
        "total_ms": latency.get("total"),
        "models": [tier for tier in risk.get("tiers_run") or [] if tier != "tier0"],
        "outcome": outcomes[-1] if outcomes else None,
    }


def _identity(identity: dict[str, Any]) -> dict[str, Any]:
    if identity.get("result") == "verified":
        return {"question": "identity", "ok": True, "text": "Agent verified", "evidence": []}
    result = str(identity.get("result") or "not verified").replace("_", " ")
    return {"question": "identity", "ok": False, "text": f"Agent not verified: {result}", "evidence": []}


def _authorization(authorization: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    evidence = [authorization["authorization_id"]] if authorization.get("authorization_id") else []
    violations = authorization.get("violations") or []
    if violations:
        first = violations[0]
        if first.get("kind") == "limit" and first.get("limit") and first.get("observed"):
            text = f"{money(first['observed'])} is over its {money(first['limit'])} limit"
        else:
            text = "Outside its authority: " + str(first.get("field") or first.get("kind")).replace("_", " ")
        return {"question": "authorization", "ok": False, "text": text, "evidence": evidence}
    if not authorization.get("authorization_id"):
        return {"question": "authorization", "ok": False, "text": "No authorization", "evidence": []}
    limit = (((authorization.get("snapshot") or {}).get("limits") or {}).get("per_payment"))
    text = f"within its {money(limit)} limit" if limit else "within its authority"
    return {"question": "authorization", "ok": True, "text": text, "evidence": evidence}


def _risk(risk: dict[str, Any]) -> dict[str, Any]:
    features = risk.get("features") or {}
    findings: list[tuple[str, list[str]]] = []

    def feature(name: str) -> tuple[Any, list[str]]:
        found = features.get(name) or {}
        return found.get("value"), list(found.get("evidence") or [])

    for name, describe in (
        ("payment_method_blocked", lambda v: "this bank account was blocked after a verified fraud finding" if v else None),
        ("document_instruction_patterns", lambda v: "the invoice text gives the agent instructions" if v else None),
        ("bill_mismatch", lambda v: "the payment doesn't match the bill" if v else None),
        ("payment_method_changed_days_ago", lambda v: _changed(v)),
        ("counterparty_is_new", lambda v: "a payee never paid before" if v else None),
        ("amount_ratio_to_vendor_median",
         lambda v: f"{v:.1f}× the usual amount" if isinstance(v, int | float) and v >= UNUSUAL_RATIO else None),
        ("duplicate_candidate", lambda v: "possibly a duplicate payment" if v else None),
        ("bill_not_referenced", lambda v: "no bill referenced" if v else None),
    ):
        value, evidence = feature(name)
        text = describe(value)
        if text:
            findings.append((text, evidence))
    confirmed, evidence = feature("payment_method_change_confirmed")
    if confirmed:
        changed = next((i for i, (text, _) in enumerate(findings) if text.startswith("bank details changed")), None)
        if changed is None:
            findings.append(("a person confirmed the bank change", evidence))
        else:
            text, refs = findings[changed]
            findings[changed] = (text + ", confirmed by a person", [*refs, *evidence])
    if not findings:
        return {"question": "risk", "ok": True, "text": "nothing unusual about the payment", "evidence": []}
    level = risk.get("level") or "low"
    return {"question": "risk", "ok": level == "low",
            "text": "; ".join(text for text, _ in findings[:2]),
            "evidence": list(dict.fromkeys(ref for _, refs in findings[:2] for ref in refs))}


def _changed(days: Any) -> str | None:
    if not isinstance(days, int | float):
        return None
    if days < 1:
        return "bank details changed today"
    return f"bank details changed {int(days)} day{'s' if int(days) != 1 else ''} ago"
