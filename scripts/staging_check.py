"""Read-only check of the Rho staging API.

Sends only GET requests. Saves raw responses to data/snapshots/<timestamp>/ (gitignored) and
writes summary.json there: per endpoint, the HTTP status, record count, how often
each field is filled, the values of status and type fields, date ranges and amount ranges.
The summary holds no names, emails, addresses or account numbers.

Usage: python3 scripts/staging_check.py
Reads RHO_API_TOKEN from .env, and RHO_API_BASE_URL if set (defaults to the staging API).
"""

import json
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING_BASE_URL = "https://rhoapi.rho-staging.co/api/v1"
# Cloudflare in front of staging rejects Python's default user agent (error 1010).
USER_AGENT = "zeta-one-staging-check/0.1"
MAX_PAGES = 20
PAGE_SIZE = 100

# (name, path, key holding the records; None for a single object)
ENDPOINTS = [
    ("business", "/business", None),
    ("users", "/users", "users"),
    ("accounts", "/accounts", "accounts"),
    ("cards", "/cards", "cards"),
    ("transactions", "/transactions", "transactions"),
    ("scheduled_transactions", "/scheduled-transactions", "scheduled_transactions"),
    ("counterparties", "/ap/counterparties", "counterparties"),
    ("bills", "/ap/bills", "bills"),
    ("expenses", "/expenses", "expenses"),
    ("reimbursements", "/reimbursements", "reimbursements"),
    ("invoicing_customers", "/invoicing/customers", "customers"),
    ("invoices", "/invoicing/invoices", "invoices"),
    ("statements", "/statements", "statements"),
    ("credit_programs", "/credit-programs", "credit_programs"),
    ("fields", "/fields", "fields"),
]

CATEGORY_KEYS = ("status", "type", "kind", "method", "state", "currency", "category", "direction")
DATE_SUFFIXES = ("_at", "_date", "_on")
AMOUNT_KEYS = ("amount", "balance", "total")


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            env[key] = value.strip().strip('"').strip("'")
    if not env.get("RHO_API_TOKEN"):
        sys.exit("RHO_API_TOKEN is not set in .env")
    base = env.get("RHO_API_BASE_URL") or STAGING_BASE_URL
    return base.rstrip("/"), env["RHO_API_TOKEN"]


def get(base, token, path, params):
    url = f"{base}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, {"error_body": error.read()[:300].decode(errors="replace")}
    except urllib.error.URLError as error:
        return None, {"error_body": str(error.reason)}


def fetch(base, token, path, key):
    if key is None:
        status, body = get(base, token, path, {})
        return status, body, ([body] if status == 200 and isinstance(body, dict) else []), False
    records, token_param, pages = [], None, 0
    while True:
        params = {"page_size": PAGE_SIZE}
        if token_param:
            params["page_token"] = token_param
        status, body = get(base, token, path, params)
        if status != 200:
            return status, body, records, False
        records.extend(body.get(key) or [])
        pages += 1
        token_param = (body.get("page") or {}).get("next_page_token")
        if not token_param:
            return status, None, records, False
        if pages >= MAX_PAGES:
            return status, None, records, True


def is_filled(value):
    return value not in (None, "", [], {})


def amount_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("amount", "value", "amount_cents"):
            if isinstance(value.get(key), (int, float)):
                return float(value[key])
        if isinstance(value.get("amount"), str):
            try:
                return float(value["amount"])
            except ValueError:
                return None
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def summarize(records):
    fields = {}
    for record in records:
        for key, value in record.items():
            entry = fields.setdefault(key, {"filled": 0, "values": {}, "dates": [], "amounts": [], "lengths": []})
            if not is_filled(value):
                continue
            entry["filled"] += 1
            lowered = key.lower()
            if isinstance(value, str) and any(part in lowered for part in CATEGORY_KEYS) and len(value) <= 40:
                entry["values"][value] = entry["values"].get(value, 0) + 1
            elif isinstance(value, bool):
                entry["values"][str(value)] = entry["values"].get(str(value), 0) + 1
            if isinstance(value, str) and lowered.endswith(DATE_SUFFIXES):
                entry["dates"].append(value[:10])
            if any(part in lowered for part in AMOUNT_KEYS):
                number = amount_value(value)
                if number is not None:
                    entry["amounts"].append(number)
            if isinstance(value, list):
                entry["lengths"].append(len(value))
    summary = {}
    for key, entry in fields.items():
        item = {"filled": f"{entry['filled']}/{len(records)}"}
        if entry["values"] and len(entry["values"]) <= 15:
            item["values"] = dict(sorted(entry["values"].items(), key=lambda kv: -kv[1]))
        if entry["dates"]:
            item["date_range"] = [min(entry["dates"]), max(entry["dates"])]
        if entry["amounts"]:
            item["amounts"] = {
                "min": min(entry["amounts"]),
                "median": statistics.median(entry["amounts"]),
                "max": max(entry["amounts"]),
            }
        if entry["lengths"]:
            item["list_length"] = {"min": min(entry["lengths"]), "max": max(entry["lengths"])}
        summary[key] = item
    return summary


def main():
    base, token = load_env()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "data" / "snapshots" / stamp
    out.mkdir(parents=True, exist_ok=True)
    report = {"taken_at": stamp, "base_url": base, "endpoints": {}}
    for name, path, key in ENDPOINTS:
        status, error, records, truncated = fetch(base, token, path, key)
        (out / f"{name}.json").write_text(json.dumps(records, indent=2))
        result = {"path": path, "status": status, "count": len(records)}
        if truncated:
            result["truncated_at_pages"] = MAX_PAGES
        if error and status != 200:
            result["error"] = error.get("error_body") if isinstance(error, dict) else str(error)
        if records:
            result["fields"] = summarize(records)
        report["endpoints"][name] = result
        print(f"{name:24} {str(status):5} {len(records):6} records{' (truncated)' if truncated else ''}")
    (out / "summary.json").write_text(json.dumps(report, indent=2))
    print(f"\nRaw data and summary written to {out.relative_to(ROOT)}/ (gitignored)")


if __name__ == "__main__":
    main()
