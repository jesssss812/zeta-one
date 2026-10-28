"""Resolve a record id the case review shows to the record itself and where it came from.

A case worker used to open each of these systems to assemble a case; the review page links every id
it cites here instead. Each answer names the system, and the place the record lives in production:
for Rho's records, the read endpoint docs/reference/rho-api.md confirms, or a plain statement that
Rho's API has none and the record is the synthetic stand-in's.
"""

from typing import Any

from zeta_one.gateway.adjustments import Adjustments
from zeta_one.gateway.ledger import Ledger

LEDGER = "Zeta One gateway ledger"
RHO = "Rho (synthetic stand-in seed)"


def _source(system: str, collection: str, production: str) -> dict[str, str]:
    return {"system": system, "collection": collection, "production": production}


def resolve(record_id: str, ledger: Ledger, adjustments: Adjustments, seed: Any) -> dict[str, Any] | None:
    """The record and its source, or None if the id is unknown or of a kind the gateway doesn't hold."""
    prefix = record_id.split("_", 1)[0]
    found = None
    if prefix == "dec":
        found = ledger.decision(record_id), _source(LEDGER, "decisions", "GET /v1/decisions/{id} on this gateway")
    elif prefix in ("pay", "chl"):
        column = "payment_id" if prefix == "pay" else "challenge_id"
        row = ledger.connection.execute(f"SELECT * FROM payments WHERE {column} = ?", (record_id,)).fetchone()
        found = (dict(row) if row else None), _source(LEDGER, "simulated payments",
                                                      "the gateway's payments table; executed payments are simulated")
    elif prefix == "adj":
        match = next((row for row in adjustments.all() if row.adjustment_id == record_id), None)
        found = (match.model_dump(mode="json") if match else None), _source(
            LEDGER, "risk adjustments", "GET /v1/adjustments on this gateway (decision 0013)")
    elif seed is not None:
        found = _seed(record_id, prefix, seed)
    if not found or found[0] is None:
        return None
    record, source = found
    return {"id": record_id, "source": source, "record": record}


def _seed(record_id: str, prefix: str, seed: Any):
    if prefix == "bill" or record_id.startswith("paid_"):
        bill = seed.get("bills", record_id)
        if bill:
            text = seed.get("bill_text", record_id)
            return {**bill, "document_text": text["text"] if text else None}, _source(
                RHO, "bills", "GET /ap/bills/{bill_id} in Rho's API, with the invoice file at /ap/bills/{bill_id}/files/{file_id}")
    if prefix == "cp":
        return seed.get("counterparties", record_id), _source(RHO, "counterparties", "GET /ap/counterparties/{counterparty_id} in Rho's API")
    if prefix == "pm":
        owner = next((cp for cp in seed.all("counterparties")
                      if any(method.get("id") == record_id for method in cp.get("payment_methods", []))), None)
        if owner:
            method = next(method for method in owner["payment_methods"] if method.get("id") == record_id)
            return {**method, "counterparty_id": owner["id"], "counterparty_name": owner["legal_name"],
                    "added": seed.get("method_dates", record_id)}, _source(
                RHO, "counterparty payment methods", "part of GET /ap/counterparties/{counterparty_id} in Rho's API")
    if prefix in ("pmh", "pmc"):
        return seed.get("method_history", record_id), _source(
            RHO, "payment-method changes", "not in Rho's confirmed API: the change history is the stand-in's")
    if prefix == "txn":
        return seed.get("transactions", record_id), _source(RHO, "transactions", "GET /transactions/{id} in Rho's API")
    if prefix == "acct":
        return seed.get("accounts", record_id), _source(RHO, "accounts", "GET /accounts/{account_id} in Rho's API")
    return None
