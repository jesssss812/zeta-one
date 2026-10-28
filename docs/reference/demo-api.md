# Demo API: the contract between the engine and the site

Agreed 2026-10-27 between the engine (this repo's `zeta_one/`) and the site (`site/`, built in
parallel). The engine serves JSON; the site renders it and holds no decision logic. The static
site reads recorded runs from `site/data/`, written by `scripts/record_runs.py` and
`scripts/demo_loop.py` and marked `"recorded": true`; the fixtures in `data/fixtures/` carry
`"illustrative": true` and no latency or cost figures. Payment execution is simulated, and every
response says so.

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
`http://localhost:8000`. The endpoints below are unauthenticated, except reading decision records:
they are the demo surface, not the signed agent endpoint (`POST /v1/actions/propose_payment`).
A scenario run is a sandbox: a fresh seed, a one-off key for the scenario's agent, its
authorization, and a request signed at the seed's clock, decided on the real identity,
authorization, context and tier-0 stages. A model tier it escalates to replays the answer recorded
in the fixture, so a demo button never calls a paid model. A record names the
signals and the model's rationale that an agent's own response leaves out, so
`GET /v1/decisions` and `GET /v1/decisions/{decision_id}` need
`Authorization: Bearer $ZETA_ADMIN_TOKEN` and refuse agent-signed requests, like the other admin
endpoints. A scenario run returns its record in full.

## Endpoints

| Method and path | Returns |
| --- | --- |
| `GET /v1/health` | `{"engine_version", "policy_version", "data_backend": "seed" \| "live", "simulated": true}` |
| `GET /v1/scenarios` | `[{"name", "title", "summary", "expected"}]` |
| `POST /v1/scenarios/{name}/run` | a **scenario result** (below); runs the scenario fresh each time. Send `Content-Type: application/json` (a body of `{}`): anything else is `415`, so another site can't trigger runs without a CORS preflight. Its record carries `"sandbox": {"scenario": "<name>"}` |
| `GET /v1/decisions/{decision_id}` | the **evidence record** of an earlier run (admin token) |
| `GET /v1/eval/latest` | the evaluation report as JSON once one exists; `404` before |

Admin endpoints, for a person with the admin token; each refuses a request carrying an agent's
signature headers:

| Method and path | Does |
| --- | --- |
| `GET /v1/decisions` | lists evidence records, newest first (`?limit=`, at most 500) |
| `POST /v1/challenges/{challenge_id}/resolve` | `{"outcome": "approve" \| "reject", "by", "note", "finding"?, "verification"?}`; approval executes (simulated) only if a recheck finds nothing changed; a `finding` is recorded as an outcome |
| `POST /v1/decisions/{decision_id}/outcomes` | records a person's finding on any decision: `{"finding": "legitimate" \| "payee_fraud" \| "manipulated_agent" \| "unauthorized", "verification": "callback_known_number" \| "vendor_portal" \| "bank_confirmation" \| "signed_customer_attestation" \| "customer_report" \| "none", "by", "note"}`; returns it with `verified` (decision 0012) |
| `GET /v1/adjustments` | the risk adjustments verified outcomes created (`?business_id=`), oldest first, revocations included (decision 0013) |
| `POST /v1/adjustments/{adjustment_id}/revoke` | `{"by", "reason"}`; appends a revocation, never edits |
| `POST /v1/cases` | `{"decision_id", "by"}`: an AI assistant assembles a case file for a person (decision 0015): the gathered evidence, public web research on the vendor, and a structured file with no verdict; `errors` lists any step that failed |
| `GET /v1/cases/{case_id}`, `GET /v1/decisions/{decision_id}/cases` | a case file; the cases for a decision |
| `GET /v1/records/{record_id}` | any record the case review cites (`dec_`, `pay_`, `chl_`, `adj_`, and the Rho stand-in's `bill_`, `cp_`, `pm_`, `pmh_`, `txn_`, `acct_`), with `source`: the system, the collection and where it lives in production (the Rho API path, or a note that Rho's confirmed API has none) |
| `POST /v1/cases/{case_id}/chat` | `{"question", "by"}`: answered by a local model from this case's evidence only; returns `answer`, the record ids it `cited` that are in the case, and any `not_in_case`. `503 chat_unavailable` says how to start the local model. `GET` returns the case's questions and answers, kept append-only |
| `GET /review` | the case worker's page; it holds no data, asks for the admin token and calls the endpoints above. It shows the vendor's logo from Google's favicon service for the domain the research found (with no referrer), so that service learns which vendor domain was viewed; a monogram stands in when there is none |
| `GET /v1/stats` | decisions by kind, challenge approval rate, verified findings, unverified claims, `missed_fraud` and `unneeded_challenges` decision ids; sandbox scenario runs left out |
| `POST /v1/agents` | registers an agent: `{"agent_id", "business_id", "owner", "public_key"}`, the Ed25519 key as 32 raw bytes in base64; `409` if it exists |
| `POST /v1/agents/{agent_id}/revoke` | revokes the agent's future requests |
| `POST /v1/authorizations` | grants an authorization document to a registered agent of its business; its version must increase |
| `POST /v1/authorizations/{authorization_id}/revoke` | revokes the current version of that authorization |

Error responses are `{"error": {"code", "message"}}` with a 4xx or 5xx status, framework errors
(unknown route, bad parameter, wrong method) and unexpected crashes included.
A signed proposal that is malformed or names records that don't exist or don't belong together is
`400 invalid_proposal` and is not recorded; this is checked before authorization, so the response
is the same whatever the amount.

## Scenario result

```json
{
  "illustrative": false,
  "replayed_stages": [],
  "scenario": {"name": "vendor_payment_method_changed", "title": "...", "summary": "...", "expected": "challenge"},
  "context": {
    "business": {"id", "name"},
    "counterparty": {"id", "name", "status", "created_at", "payment_methods": [{"id", "type", "bank_name", "is_default", "added_at"}]},
    "payment_method_history": [{"id", "method_id", "change", "changed_at", "changed_by", "summary"}],
    "bill": {"id", "counterparty_id", "counterparty_name", "invoice_number", "invoice_date", "due_date", "amount": {"amount", "currency"}, "memo", "document_excerpt"},
    "payment_history": {"count", "first_at", "last_at", "median_amount": {"amount", "currency"}, "recent": [{"id", "posted_at", "amount", "method_type"}]},
    "bill_counterparty": "present only when the proposal's counterparty differs from the bill's: that counterparty, same shape as `counterparty`",
    "bill_counterparty_payment_history": "present with `bill_counterparty`: its payment history, same shape as `payment_history`",
    "open_bills": "the proposed counterparty's unpaid bills as the engine found them itself, same shape as `bill`; may be empty"
  },
  "proposal": {"bill_id", "counterparty_id", "payment_method_id", "source_account_id", "amount": {"amount", "currency"}, "memo", "agent_rationale", "source_document_ids"},
  "decision_record": { "...the evidence record below..." }
}
```

`context` is a **derived view** of what the engine looked at, with money as integer minor units
and an ISO 4217 code. Only `zeta_one/rho/models.py` follows Rho's schemas exactly; the view adds
fields Rho doesn't have, from the stand-in's own tables: `payment_methods[].added_at` and the
whole `payment_method_history` (Rho exposes no method timestamps), `bill.document_excerpt` (bill
text), `payment_history.recent[].method_type` (derived from Rho's `transaction_type`), and
`counterparty.name` (Rho's `legal_name`). Vendor payment history is joined through paid bills,
because Rho's transactions carry a counterparty name and no id. `context.counterparty` is always
the **proposed** payee. `bill` and `payment_method_history` may be `null` or empty for scenarios
without them; `payment_history.count` is `0` with `median_amount: null` for a payee never paid
before.

## Evidence record

The engine's record for one decision ([../strategy/implementation-plan.md](../strategy/implementation-plan.md)
describes how it is produced). Fields the site should rely on:

```json
{
  "schema_version": 1,
  "decision_id": "dec_...", "created_at": "...", "policy_version": "2026-10-28.4",
  "engine_version": "<git sha>" | null, "seed_version": "<hash>" | null,
  "configuration": {"tiers": ["tier0", "strong"] | ["tier0", "cheap", "strong"], "escalation": "engineered" | "jev" | "always" | "none", "jev_min_confidence": 0.8, "jev_min_finding_confidence": 0.9},
  "decision": "allow" | "challenge" | "block",
  "reasons": ["risk:elevated"],
  "challenge": null | {"type": "confirm" | "renew_authorization" | "verify_payee", "routed_to": "...", "user_sees": "..."},
  "friction_rung": 0 | 1 | 2 | 3 | 4 | 5,
  "identity": {"result": "verified" | "unsigned" | "unknown_agent" | "revoked" | "stale_timestamp" | "replay" | "invalid_signature",
               "claimed_agent_id", "business_id", "owner", "key_id", "timestamp", "nonce",
               "checked": ["present", "known", "active", "timestamp", "nonce", "signature"]},
  "authorization": {"authorization_id", "version", "violations": [{"field", "kind": "scope" | "limit", "limit", "observed"}], "snapshot": {"...as stored..."}},
  "risk": {
    "level": "low" | "elevated" | "high" | null,
    "level_set_by": "tier0" | "cheap" | "strong" | "open_weight" | null,
    "floor": null | {"level": "elevated" | "high", "flags": ["<feature name>"]},
    "tiers_run": ["tier0", "strong"],
    "features": {"<name>": {"value", "evidence": ["<record id>"]}},
    "tier_results": [{"tier": "tier0" | "cheap" | "strong" | "open_weight", "model": "<model id>" | null, "level", "confidence": 0.0-1.0 | null, "signals": ["<signal name>"], "latency_ms", "usage": null | {"input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}, "error": null | "...", "recommended_decision": "allow" | "challenge" | "block" (language-model tiers only), "answered_level": "<level>" (when the tier raised the model's own level), "probabilities": {"<question>": 0.0-1.0} and "answers": {"<question>": value} (Jev only)}],
    "signals": [{"name", "severity": "low" | "elevated" | "high", "evidence": ["<record id>"], "source": "tier0" | "cheap" | "strong" | "open_weight"}],
    "lowered": null | {"from": "elevated" | "high", "to": "low" | "elevated", "by": "cheap" | "strong", "signals": ["<soft signal name>"]},
    "reused_from": null | "dec_...",
    "repeat_limit_reached": false,
    "adjustments": ["adj_..."],
    "model_rationale": null | "..."
  },
  "execution": {"status": "executed" | "held" | "blocked", "simulated": true},
  "cost": null | {"input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "usd", "prices_used": {"<model>": {"input_per_mtok", "output_per_mtok", "cache_read_multiplier", "cache_write_multiplier"}}, "unpriced_models": ["<model>"]},
  "latency_ms": null | {"identity", "authorization", "risk", "total"},
  "review": null | {"by", "at", "outcome", "note", "provenance"},
  "proposal": null | {the proposal as above, as it was submitted},
  "context": null | {the context as above, as the risk stage read it}
}
```

Rules the site can count on:

- `identity`, `authorization` and `risk` are always present and independent. When a stage never
  ran, its object is present with `null` ids, empty lists and `risk.level: null`: an identity
  failure leaves `authorization.snapshot: null` and `risk.tiers_run: []`; an authorization block
  leaves `risk.tiers_run: []`. "Not evaluated" is a state the site should show, distinct from
  "passed".
- `cost` and `latency_ms` are `null` when not measured. The site shows "not measured", never a
  placeholder number. Fixtures always have them `null`. Records the engine writes always carry
  `cost`: `usd` is `0` when no model ran, cache reads and writes are priced from the input price,
  and a model with no known price is listed in `unpriced_models` and left out of `usd`.
  `latency_ms` has a key for each stage that ran (`identity`, `authorization`, `risk`) and
  `total`; a stage that didn't run has no key.
- A strong tier result's `recommended_decision` is the model's suggestion, recorded for people;
  the policy never reads it. Like `model_rationale`, it is model output an attacker may have
  steered.
- `model_rationale` is model output, and `proposal.agent_rationale` is the agent's own text; both
  can be written by an attacker. Label both as untrusted text, never as findings.
- `friction_rung` is `0` for allow, `2`–`4` for the challenge types, `5` for block
  ([../decisions/0008-friction-ladder.md](../decisions/0008-friction-ladder.md)).
- `risk.lowered` is set when a model lowered soft signals below tier 0's level, and the reasons
  then include `risk:lowered_by_model`; show it, since an allow a model cleared is not the same as
  a clean one. `risk.reused_from` names an earlier decision whose risk result was reused for the
  same proposal, after tier 0 ran again and found the same. `risk.repeat_limit_reached` is `true`
  when the agent had already had three different proposals to the same payee and method assessed
  by the models within 24 hours: only tier 0 ran, and the decision is `challenge` with
  `risk:repeat_limit`. A `tier_results` entry may carry
  `error` when that tier failed; the decision is then `challenge`, with `risk:model_unavailable`
  for a model tier or `risk:tier0_unavailable` when tier 0 or the context it reads failed (the
  risk `level` is then null). All three are optional; fixtures omit them.
- `risk.floor` names the tier-0 facts no model was allowed to lower; `risk.level_set_by` names the
  tier that set the final level. `tier_results[].confidence` is non-null only for a calibrated
  tier (Jev); language-model tiers report `null`, because their self-reported confidence is not
  calibrated and never gates a decision. `tier_results[].signals` is a list of signal names, which
  index into `risk.signals`.
- Tier roles are `tier0`, `cheap` (Jev, or an open-weight model in that comparison arm) and
  `strong`; the model id is in `model`. In the first engine version the configuration is
  `["tier0", "strong"]` with engineered escalation: the strong tier runs only when tier 0 isn't
  clean, so a routine payment shows `tiers_run: ["tier0"]` and no model.
  `escalation: "none"` runs tier 0 alone (the evaluation's rules-only arm); `"always"` runs the
  model tiers on every case. `"jev"` runs `["tier0", "cheap", "strong"]`: Jev when tier 0 isn't
  clean, then the strong tier only on Jev's rule, so a record may show `tiers_run: ["tier0", "cheap"]`
  with Jev's level, confidence and probabilities. `["tier0", "open_weight"]` puts an open-weight
  model in the strong tier's place (decision 0014). The live gateway runs `engineered` unless
  `ZETA_RISK_CONFIGURATION` is `jev` or `open_weight`.
- `execution.simulated` is always `true` in this build.
- A record keeps what was decided on: `proposal` whenever the body parsed (an unverified request's
  too, kept for the reviewer and never acted on) and `context` whenever it was loaded (never for an
  unverified request). Later changes to the business's records don't change them.
- `risk.adjustments` lists the risk adjustments (decision 0013) that changed the assessment: a
  blocked payment method (hard flag `payment_method_blocked`, floor `high`, blocked as a redirect
  pattern) or a confirmed bank change (`payment_method_change_confirmed`: that change is a soft
  signal, not a floor). Show them with the finding and person behind them.
- A record may carry `outcomes`: each `{"finding", "verification", "verified", "by", "at", "note", "source": "resolve" | "report"}`, oldest first. Show unverified ones as claims, never as findings.
- A scenario result's `illustrative` is `true` when any stage replayed the fixture instead of
  running, and `replayed_stages` names them (`["strong"]` for the two scenarios that escalate).
  Show replayed model output as recorded, not as a live answer.
- Proposal amounts must be positive integer minor units, at most 10^12 ($10 billion), in an
  uppercase three-letter ISO 4217 currency code. Ids are 1 to 128 characters, `memo` at most
  1,000, `agent_rationale` at most 4,000, and `source_document_ids` at most 20 ids. Anything else
  is a malformed request, rejected before authorization or risk runs. The strong tier also cuts
  each untrusted text field, invoice text included, to 8,000 characters and says so in the prompt.
- Evidence ids in `features` and `signals` refer to records in `context` (payment-method history
  ids, transaction ids, bill ids) so the site can link a signal to the row it came from.
- `amount_ratio_to_vendor_median` may also carry `raw_value`, the unrounded ratio used for
  risk thresholds. Its `value` remains rounded to two decimals for display; older records
  without `raw_value` use `value` for thresholds.

## Scenarios

Five, one per evaluation category; each has a fixture in `data/fixtures/<name>.json`. The site's
first version shows the first; the other four follow, in this order, so the three questions are
each seen failing on their own.

| Name | What happens | Which question decides | Expected |
| --- | --- | --- | --- |
| `vendor_payment_method_changed` | Verified, authorized agent pays a long-standing vendor a typical amount; the vendor's default ACH was replaced three days ago. Tier 0 flags the change and sets an `elevated` floor; the strong tier runs on escalation and agrees. The authorization deliberately permits any payee, which is why only risk can see this | risk | **challenge** (`confirm` in the first engine version, `verify_payee` once extension 5 lands); payment held |
| `routine_bill_payment` | Same agent pays a recurring monthly invoice: same vendor, amount and method as the last year. Tier 0 clean, so no model runs at all | none fails | **allow**; payment executed (simulated); no prompt |
| `over_per_payment_limit` | Same agent proposes $7,200 against a $5,000 per-payment limit | authorization (`limit`) | **block** before any risk tier runs; `risk.tiers_run` is empty |
| `unknown_agent` | The routine payment, signed with a key Zeta One has never seen | identity | **block**; authorization and risk not evaluated |
| `invoice_redirect_instructions` | The invoice carries instructions aimed at automated AP systems to pay a day-old lookalike payee; the agent follows them. Authorization permits any payee, so only risk can catch it: proposal disagrees with the bill, instruction patterns in the document, new payee; the strong tier runs on escalation and confirms | risk | **block**, `risk:high_with_redirect_pattern`; `context.bill_counterparty` holds the real vendor |

Fixtures:
[`vendor_payment_method_changed`](../../data/fixtures/vendor_payment_method_changed.json),
[`routine_bill_payment`](../../data/fixtures/routine_bill_payment.json),
[`over_per_payment_limit`](../../data/fixtures/over_per_payment_limit.json),
[`unknown_agent`](../../data/fixtures/unknown_agent.json),
[`invoice_redirect_instructions`](../../data/fixtures/invoice_redirect_instructions.json).
Fixture `tier_results[].model` is `"illustrative"`; `model_rationale`, where present, starts with
`[illustrative model output]`. Live runs replace both.
