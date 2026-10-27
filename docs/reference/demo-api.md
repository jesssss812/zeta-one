# Demo API: the contract between the engine and the site

Agreed 2026-10-27 between the engine (this repo's `zeta_one/`) and the site (`site/`, built in
parallel). The engine serves JSON; the site renders it and holds no decision logic. Until the
engine runs, the site uses the fixture in `data/fixtures/`, which carries `"illustrative": true`
and no latency or cost figures. Payment execution is simulated before and after integration, and
every response says so.

## Ownership

| Path | Owner | Notes |
| --- | --- | --- |
| `zeta_one/`, `eval/`, `scripts/`, `tests/`, `data/`, `docs/` | engine | includes this contract and the fixtures |
| `site/` | site | any framework; `site/node_modules/`, `site/dist/`, `site/.next/` are gitignored |
| `README.md` | engine | the site sends text for its own section |
| `AGENTS.md`, `.gitignore` | owner | the engine adds ignore lines the site needs |

Changes to this contract or to a fixture are proposed in chat and made by the engine side, so the
two efforts never edit the same file.

## Running the engine

```bash
pip install -r requirements.txt
uvicorn zeta_one.gateway.app:app --port 8000
```

CORS allows `http://localhost:*` so a dev server for the site can call it. Base URL
`http://localhost:8000`. All endpoints below are unauthenticated: they are the demo surface, not the
signed agent endpoint (`POST /v1/actions/propose_payment`, which the scenario runner calls
internally with a built-in signed agent).

## Endpoints

| Method and path | Returns |
| --- | --- |
| `GET /v1/health` | `{"engine_version", "policy_version", "data_backend": "seed" \| "live", "simulated": true}` |
| `GET /v1/scenarios` | `[{"name", "title", "summary", "expected"}]` |
| `POST /v1/scenarios/{name}/run` | a **scenario result** (below); runs the scenario fresh each time |
| `GET /v1/decisions/{decision_id}` | the **evidence record** of an earlier run |
| `GET /v1/eval/latest` | the evaluation report as JSON once one exists; `404` before |

Error responses are `{"error": {"code", "message"}}` with a 4xx or 5xx status.

## Scenario result

```json
{
  "illustrative": false,
  "scenario": {"name": "vendor_payment_method_changed", "title": "...", "summary": "...", "expected": "challenge"},
  "context": {
    "business": {"id", "name"},
    "counterparty": {"id", "name", "status", "created_at", "payment_methods": [{"id", "type", "bank_name", "is_default", "added_at"}]},
    "payment_method_history": [{"id", "method_id", "change", "changed_at", "changed_by", "summary"}],
    "bill": {"id", "invoice_number", "invoice_date", "due_date", "amount": {"amount", "currency"}, "memo", "document_excerpt"} ,
    "payment_history": {"count", "first_at", "last_at", "median_amount": {"amount", "currency"}, "recent": [{"id", "posted_at", "amount", "method_type"}]}
  },
  "proposal": {"bill_id", "counterparty_id", "payment_method_id", "source_account_id", "amount": {"amount", "currency"}, "memo", "agent_rationale", "source_document_ids"},
  "decision_record": { "...the evidence record below..." }
}
```

`context` is what the engine looked at, in Rho's shapes, with money as integer minor units and an
ISO 4217 code. `bill` and `payment_method_history` may be `null` or empty for scenarios without
them.

## Evidence record

The engine's record for one decision ([../strategy/implementation-plan.md](../strategy/implementation-plan.md)
describes how it is produced). Fields the site should rely on:

```json
{
  "schema_version": 1,
  "decision_id": "dec_...", "created_at": "...", "policy_version": "2026-10-28.1",
  "configuration": {"tiers": ["tier0", "cheap", "strong"], "escalation": {"confidence_min": 0.8}},
  "decision": "allow" | "challenge" | "block",
  "reasons": ["risk:elevated"],
  "challenge": null | {"type": "confirm" | "renew_authorization" | "verify_payee", "routed_to": "...", "user_sees": "..."},
  "friction_rung": 0,
  "identity": {"result": "verified" | "unsigned" | "unknown_agent" | "revoked" | "stale_timestamp" | "replay" | "invalid_signature",
               "claimed_agent_id", "business_id", "owner", "key_id", "checked": ["known", "active", "timestamp", "nonce", "signature"]},
  "authorization": {"authorization_id", "version", "violations": [{"field", "kind": "scope" | "limit", "limit", "observed"}], "snapshot": {"...as stored..."}},
  "risk": {
    "level": "low" | "elevated" | "high",
    "tiers_run": ["tier0", "cheap"],
    "features": {"<name>": {"value", "evidence": ["<record id>"]}},
    "tier_results": [{"tier", "model", "level", "confidence", "signals": [...], "latency_ms", "usage": {"input_tokens", "output_tokens"}}],
    "signals": [{"name", "severity": "low" | "elevated" | "high", "evidence": ["<record id>"], "source": "tier0" | "cheap" | "strong"}],
    "model_rationale": null | "..."
  },
  "execution": {"status": "executed" | "held" | "blocked", "simulated": true},
  "cost": null | {"input_tokens", "output_tokens", "usd", "prices_used": {"<model>": {"input_per_mtok", "output_per_mtok"}}},
  "latency_ms": null | {"identity", "authorization", "risk", "total"},
  "review": null | {"by", "at", "outcome", "note", "provenance"}
}
```

Rules the site can count on:

- `identity`, `authorization` and `risk` are always present and independent. An identity failure
  leaves `authorization.violations` empty and `risk.tiers_run` empty: nothing further was evaluated.
- `cost` and `latency_ms` are `null` when not measured. The site shows "not measured", never a
  placeholder number. Fixtures always have them `null`.
- `model_rationale` is model output; label it so.
- `execution.simulated` is always `true` in this build.
- Evidence ids in `features` and `signals` refer to records in `context` (payment-method history
  ids, transaction ids, bill ids) so the site can link a signal to the row it came from.

## First scenario: `vendor_payment_method_changed`

A verified agent proposes paying a bill from a vendor the business has paid monthly for over a
year. The bill amount is typical. Three days ago the vendor's default ACH method was replaced with
one at a different bank. Identity verifies; the authorization permits the payment; tier-0 risk
flags the change and the cheap tier agrees at moderate confidence; the strong tier is not needed.
Expected: **challenge**, type `confirm` in the first engine version (`verify_payee` once extension
3 lands). The held payment is simulated.

Fixture: [`../../data/fixtures/vendor_payment_method_changed.json`](../../data/fixtures/vendor_payment_method_changed.json).
