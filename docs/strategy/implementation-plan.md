# Implementation plan

Written 2026-10-27 (Tuesday evening), before any code. Submissions close Thu Oct 29, 5:00 PM CT.
The decisions this plan carries out are in [../decisions/](../decisions/); what it measures is in
[evaluation.md](evaluation.md). When something here turns out wrong during the build, change the
code and leave this doc as the dated plan; [../roadmap.md](../roadmap.md) tracks what is left.

## What "done" looks like

A judge clones the repo, runs two commands, opens one page, clicks through six scenarios and sees
each proposed agent payment decided (allow / challenge / block) with an evidence record, then opens
an evaluation table showing four configurations side by side with accuracy, challenge rate, cost per
action and latency. The Loom shows the same, plus thirty seconds of the live, read-only Rho
connection. Payment execution is labelled simulated everywhere.

## Architecture

```
                 signed request                       ┌──────────────────────────────┐
  Agent  ───────────────────────────▶  Gateway (FastAPI)                               │
 (customer's                            │  1 identity   registry + Ed25519 verify      │
  or 3rd party)                         │  2 authorization    deterministic checks           │
                                        │  3 risk       tier0 → Jev → Claude           │
                                        │  4 policy     allow / challenge / block      │
                                        │  5 evidence   record, policy version         │
                                        │  6 execute    SIMULATED payment write        │
                                        └───────┬──────────────────────────────────────┘
                                                │ one interface, two backends
                                   ┌────────────┴─────────────┐
                            snapshot/SQLite               live Rho (read-only)
                            seed or staging snapshot      rhoapi.rho-staging.co
                            + payments, method history,   over VPN, demo only
                              bills with invoice text
```

Only the gateway's `execute` module can write a payment, and only to the stand-in. Agents hold a
signing key and nothing else.

## Modules

```
zeta_one/
  rho/        models.py (Counterparty, PaymentMethod, Bill, Transaction, Account, Money)
              store.py (Protocol)  snapshot.py (SQLite)  live.py (httpx, read-only)  seed.py
  identity/   registry.py  signing.py
  authorization/    schema.py  check.py
  risk/       features.py  tier0.py  jev.py  claude.py  escalation.py  schema.py
  decide/     policy.py  evidence.py
  gateway/    app.py (FastAPI)  execute.py  scenarios.py
  ui/         index.html (+ one css, one js file)
eval/         cases.py (generator)  run.py  report.py
scripts/      snapshot_staging.py (local, VPN)  make_seed.py  keygen.py
tests/
data/         seed/ (committed, synthetic)  snapshots/ (gitignored)  eval/ (cases.jsonl, results)
```

Stand-in tables beyond Rho's shapes: `payment_method_history(counterparty_id, method_id, change,
changed_at, changed_by)`, `bill_documents(bill_id, text)`, `payments(id, proposal, decision_id,
status, executed_at)`, `agents`, `authorizations`, `nonces`, `decisions`.

## Gateway API

| Method and path | Purpose | Auth |
| --- | --- | --- |
| `POST /v1/actions/propose_payment` | the one agent action; returns the decision and evidence id | signed |
| `GET /v1/decisions/{id}` | evidence record | none (demo) |
| `GET /v1/decisions` | recent decisions for the UI | none |
| `POST /v1/agents`, `POST /v1/agents/{id}/revoke` | registry | none (demo; admin in reality) |
| `POST /v1/authorizations`, `POST /v1/authorizations/{id}/revoke` | authorizations | none |
| `POST /v1/challenges/{id}/resolve` | a human approves or rejects a challenged action; recorded with provenance | none |
| `POST /v1/scenarios/{name}/run` | runs a named demo scenario end to end using a built-in signed agent | none |
| `GET /v1/eval/latest` | the last evaluation report as JSON | none |
| `GET /v1/rho/health` | which backend is active; in live mode, counts from a read call | none |

## Decision flow and policy (policy version `2026-10-28.1`)

1. **Identity.** Not `verified` → **block**, reason `identity:<result>`. Stop.
2. **Authorization.** Any violation → **block**, reasons `authorization:<field>`. Stop. Violations are listed in
   full even though the first one suffices.
3. **Risk.** Tier 0 always; tiers 1 and 2 per the active configuration and the escalation rule
   ([0007](../decisions/0007-risk-tiers.md)). Result: `level` (low / elevated / high), `signals[]`,
   `tiers_run[]`, `model_ids[]`, `usage`, `latency_ms`.
4. **Policy table.**

   | Condition (first match) | Decision | Reason code |
   | --- | --- | --- |
   | risk high **and** (`bill_mismatch` or `document_targets_agent` or `lookalike_counterparty`) | block | `risk:high_with_redirect_pattern` |
   | risk high | challenge | `risk:high` |
   | `counterparty_is_new` and authorization `allow_new_counterparties` is false | challenge | `authorization:new_counterparty_requires_approval` |
   | amount > authorization `human_approval_above` | challenge | `authorization:human_approval_threshold` |
   | risk elevated | challenge | `risk:elevated` |
   | otherwise | allow | `clean` |

5. **Execute.** `allow` → simulated payment `executed`; `challenge` → payment `held` until a human
   resolves it; `block` → payment `blocked`. Every outcome writes the evidence record first.

## Evidence record

```json
{
  "decision_id": "...", "created_at": "...", "policy_version": "2026-10-28.1",
  "configuration": {"tiers": [0, 1, 2], "escalation": {"confidence_min": 0.8}},
  "action": { "...the proposal as received..." },
  "identity": {"claimed_agent_id": "...", "result": "verified", "business_id": "...",
               "owner": "...", "key_id": "...", "checked": ["known", "active", "timestamp", "nonce", "signature"]},
  "authorization": {"authorization_id": "...", "version": 1, "violations": [], "snapshot": { "...as stored..." }},
  "risk": {"level": "elevated", "tiers_run": [0, 1],
           "features": {"payment_method_changed_days_ago": {"value": 3, "evidence": ["pmh_42"]}, "...": "..."},
           "tier1": {"model": "typesafe/jev-1.14", "answers": {"...": "..."}, "latency_ms": 95},
           "tier2": null,
           "signals": [{"name": "payment_method_changed", "severity": "elevated", "evidence": ["pmh_42"]}]},
  "decision": "challenge", "reasons": ["risk:elevated"],
  "execution": {"status": "held", "simulated": true},
  "cost": {"input_tokens": 410, "output_tokens": 0, "usd": 0.000017},
  "latency_ms": {"identity": 1, "authorization": 2, "risk": 97, "total": 104},
  "review": null
}
```

`review`, when a human resolves a challenge, holds `{by, at, outcome, note, provenance:
"human_ui"}`. Model rationales live under `risk.tier2.rationale`, labelled model output.

## Seed data and scenarios

`scripts/make_seed.py` writes `data/seed/`: one business, 3 accounts, ~40 counterparties (each with
1–2 payment methods and a created date), ~400 outgoing transactions over 12 months with per-vendor
amount distributions, ~60 bills (some paid, some ready for payment) with short invoice texts, and a
payment-method history. If `data/snapshots/` exists locally, `make_seed.py` reads its summary
statistics (counts, amount quantiles per vendor bucket, method-type mix) to shape the seed, and the
README says which happened. Seeds are deterministic from a fixed random seed.

`eval/cases.py` writes `data/eval/cases.jsonl`, ~60 cases, each with `category`, `setup` (mutations
to apply to the seed before the proposal, such as "change method 3 days ago" or "insert invoice
text"), `proposal`, `agent` (which built-in agent signs, or how the signature is broken),
`expected`, `also_acceptable`, `provenance: "synthetic:eval/cases.py@<git sha>"`.

| Category | Count | Expected | Examples |
| --- | --- | --- | --- |
| A legitimate routine | 15 | allow | established vendor, typical amount, bill matches, inside authorization |
| B authorization violations | 12 | block | over per-payment cap, over rolling cap, expired, revoked authorization, denylisted counterparty, wrong source account, disallowed method type |
| C identity failures | 8 | block | unknown agent, bad signature, replayed nonce, stale timestamp, revoked agent, unsigned |
| D authorized but suspicious | 12 | challenge | method changed <7 days, amount 5× vendor median, duplicate invoice, lookalike vendor name, first wire to an old ACH vendor |
| E adversarial | 8 | block (challenge acceptable) | invoice text instructing "remit to new account", proposal counterparty ≠ bill counterparty, rationale citing "updated instructions", amount matches bill but method is a new international wire |
| F ambiguous | 5 | challenge (allow acceptable for the cleanest) | new vendor, small amount, clean documents, inside authorization |

The six **demo scenarios** are one hand-picked case from each category, exposed as
`POST /v1/scenarios/{name}/run` and as buttons in the UI.

## Evaluation runner

`eval/run.py --config rules|jev|claude|cascade` applies each case's `setup` to a fresh copy of the
seed, signs and sends the proposal, records the decision and evidence, and restores. Output:
`data/eval/results/<config>.jsonl` and a combined `report.json` and `report.md` with, per
configuration: accuracy against `expected`, accuracy counting `also_acceptable`, hard-constraint
accuracy on B and C (must be 100%), non-allow rate on D and E (detection), challenge rate on A
(friction), cost per action, p50/p95 latency, and a confusion matrix. The UI's evaluation tab reads
`report.json`. Prices used are printed in the report.

Budget on the owner's Console key: the `claude` arm is ~60 calls to Opus 5.5 at roughly 2k input
and 400 output tokens, about $0.50–1.00 per full run; the cascade arm is a fraction of that; Jev is
negligible. Ten full runs during development stay under $15.

## UI

One page, three panes: **Scenarios** (six buttons plus a free-form proposal editor), **Decision**
(a large allow / challenge / block card with reasons, the three dimensions shown as separate rows:
identity, authorization, risk; a "resolve challenge" control), **Evidence** (the record as a collapsible
tree). A fourth tab, **Evaluation**, renders `report.json` as a comparison table and a cost-versus-
accuracy chart. A persistent banner reads "Payments are simulated. Rho data: seed | snapshot |
live (read-only)". Styling follows [messaging.md](messaging.md): the ζ = 1 mark, a decaying
oscillation, restrained colour.

## Testing

`pytest` on: signature verify (good, bad, replay, stale, revoked); each authorization field (one violation
each); tier 0 features on fixtures; the policy table row by row; evidence record completeness
(every required key present, `simulated: true`); the eval runner on three cases with model tiers
stubbed. Model tiers are stubbed in tests; a `--live-models` flag runs them for real.

## Schedule

| When | Build | Done means |
| --- | --- | --- |
| **Tue evening** | This plan. Locally: VPN + `GET /business`; run `snapshot_staging.py`; note counts in `reference/rho-api.md`. Sign up for Jev (or OpenRouter), make one call, correct `reference/jev.md`. Confirm the Console key works | snapshot summary committed as text; Jev request shape known |
| **Wed morning** | `rho/models.py`, `store.py`, `snapshot.py`, `seed.py`, `make_seed.py`; `eval/cases.py` and the cases file; tests for the store | `data/seed/` and `cases.jsonl` committed |
| **Wed midday** | `identity/`, `authorization/`, `decide/policy.py`, `decide/evidence.py`; gateway endpoints; `execute.py`; tests | categories B and C pass end to end with tier 0 only |
| **Wed afternoon** | `risk/features.py`, `tier0.py`, `jev.py`, `claude.py`, `escalation.py`; tests with stubs; first real model calls | all six categories produce sensible decisions in the cascade |
| **Wed evening** | `eval/run.py`, `report.py`; first full four-arm run; `ui/index.html` scenario and decision panes | `report.md` exists with real numbers |
| **Thu morning** | UI evidence and evaluation panes; `live.py` and `/v1/rho/health`; README (quick start, diagram, reproduction, data provenance, limitations, next steps); `.env.example` | a stranger can run it from the README |
| **Thu 12:00–14:00** | Loom: problem (30 s), six scenarios (2 min), evaluation table (45 s), live Rho read (30 s), limits and next steps (30 s) | video uploaded |
| **Thu 14:00–16:00** | write-up from [vision.md](vision.md); repo audit (no `.env`, no snapshots, no personal data); make public; submit | form submitted by 16:30 |
| **Thu 16:30–17:00** | buffer | |

## Cut list, in order

If behind schedule, drop from the bottom up: live Rho backend in the demo (keep the module) →
evaluation chart (keep the table) → lookalike-vendor and off-hours features → rolling limit →
category F → Jev tier (Haiku fallback becomes the cheap arm) → the free-form proposal editor.

Never cut: signatures, authorization checks, the policy table, the evidence record, the four-arm
evaluation, the simulated label, the README.

## Risks

| Risk | Mitigation |
| --- | --- |
| Staging is sparse or the VPN fails | The seed is shaped from assumptions and says so; the live read is a 30-second aside |
| Jev's request shape differs from the guides | One adapter file; Haiku fallback behind the same interface |
| Model tiers disagree with hand labels on E and F | Report it; those categories exist to show where the strong tier earns its cost |
| Time | The cut list; the schedule front-loads what is scored |
