# Implementation plan

Written 2026-10-27 (Tuesday evening), before any code. Submissions close Thu Oct 29, 5:00 PM CT.
The decisions this plan carries out are in [../decisions/](../decisions/); what it measures is in
[evaluation.md](evaluation.md). When something here turns out wrong during the build, change the
code and leave this doc as the dated plan; [../roadmap.md](../roadmap.md) tracks what is left.

## Shape of the build

**A thin first version that runs end to end by Wednesday night with every principle in it, seven
seams designed in, then extensions on Thursday morning in a fixed order, each one droppable.** The
principles are not deferrable because they are the product and they cost minutes on day one:
identity, authorization and risk as separate fields in every record; deterministic blocks no model
can lift; an evidence record for every decision; "simulated" on every payment; provenance on every
dataset.

## What "done" looks like

A judge clones the repo, runs two commands, opens one page, clicks through five scenarios and sees
each proposed agent payment decided (allow / challenge / block) with an evidence record showing the
three questions answered separately, then opens an evaluation table with four configurations side
by side: accuracy, hard-constraint accuracy, detection, challenge rate, cost per action, latency.
The Loom shows the same. Payment execution is labelled simulated everywhere.

## Architecture

```
                 signed request                       ┌──────────────────────────────┐
  Agent  ───────────────────────────▶  Gateway (FastAPI)                               │
 (customer's                            │  1 identity   registry + Ed25519 verify      │
  or 3rd party)                         │  2 authorization  deterministic checks       │
                                        │  3 risk       tier0 → cheap tier → Claude    │
                                        │  4 policy     allow / challenge / block      │
                                        │  5 evidence   record, policy version         │
                                        │  6 execute    SIMULATED payment write        │
                                        └───────┬──────────────────────────────────────┘
                                                │ one interface, two backends
                                   ┌────────────┴─────────────┐
                            snapshot/SQLite               live Rho (read-only)
                            committed synthetic seed      rhoapi.rho-staging.co
                            + payments, method history,   over VPN, demo only (ext. 1)
                              bills with invoice text
```

Only the gateway's `execute` module can write a payment, and only to the stand-in. Agents hold a
signing key and nothing else.

## First version (must run end to end by Wednesday night)

| Layer | In the first version | Extension |
| --- | --- | --- |
| Identity | registered agents, Ed25519 signature, timestamp + nonce, `active` / `revoked` | automation-detection signals |
| Authorization | `actions`, `counterparties` (any / allowlist / denylist), `limits.per_payment`, `expires_at`, `status`, `human_approval_above` | `limits.rolling`, `source_accounts`, `payment_method_types`, `allow_new_counterparties`, signed grants |
| Risk | tier 0 with five features: `counterparty_is_new`, `payment_method_changed_days_ago`, `amount_ratio_to_vendor_median`, `bill_mismatch`, `document_instruction_patterns`; tier 2 `claude-opus-5-5` structured output; cheap tier `claude-haiku-5-5`; cascade on tier-0 band and cheap-tier confidence | Jev as the cheap tier; `lookalike_counterparty`, `off_hours`, `agent_velocity`, `duplicate_candidate` |
| Policy | `allow` / `challenge` (type `confirm`) / `block`; versioned ordered rule table | challenge types `renew_authorization`, `verify_payee`, `notify` (decision 0008) |
| Evidence | the full schema below, from the first commit | nothing: the schema is the extensibility |
| Execution | simulated; `held` on challenge; `POST /v1/challenges/{id}/resolve` | observe mode |
| Data | committed synthetic seed, deterministic from a fixed random seed, minor-unit amounts | live Rho backend (shows one vendor and one deposit: the connection, not the data) |
| Evaluation | ~40 cases in categories A–E; four configurations; `report.md` and `report.json` | category F, friction score, chart |
| Interface | the demo API in [../reference/demo-api.md](../reference/demo-api.md), served with CORS; the site in `site/` renders it | registration and grant endpoints for the site; resolve with type; evaluation JSON |

Haiku standing in for Jev keeps all four evaluation configurations meaningful even if Jev never
arrives; the report names what ran.

## The seven seams

Designed once, so each extension is additive:

1. `rho.store.Store` protocol; `snapshot.py` implements it now, `live.py` later.
2. `risk.RiskTier` protocol: `assess(ctx) -> TierResult {level, confidence, signals, model_id,
   usage, latency_ms}`; the active configuration is a list of tier names; Jev, Haiku and Opus are
   adapters of one shape.
3. `authorization.check` is an ordered list of `check_<field>` functions, each returning a
   violation `{field, kind: scope | limit, limit, observed}` or nothing; unknown fields in a stored
   authorization are ignored.
4. `decide.policy` is an ordered list of rules `(condition, decision, challenge_type, reason_code)`
   under a version string; a new rung is a row.
5. `ChallengeType` and `ReviewOutcome` enums, one member each at first.
6. A scenario is data: `{category, setup, agent, proposal, expected, also_acceptable, provenance}`.
7. The evidence record is a versioned schema with required keys tested and extra keys allowed.

## Modules

```
zeta_one/
  rho/            models.py  store.py  snapshot.py  seed.py  live.py (ext. 1)
  identity/       registry.py  signing.py
  authorization/  schema.py  check.py
  risk/           features.py  tier0.py  tiers.py (protocol)  claude.py  jev.py (ext. 2)  escalation.py
  decide/         policy.py  evidence.py
  gateway/        app.py  execute.py  scenarios.py
eval/             cases.py  run.py  report.py
site/             the demo site, separate effort (see Site and integration)
scripts/          check.py  staging_check.py (exist)  make_seed.py  keygen.py
tests/
data/             seed/ (committed, synthetic)  fixtures/ (illustrative API responses)  eval/ (cases.jsonl, results/)  snapshots/ (gitignored)
```

Stand-in tables beyond Rho's shapes: `payment_method_history(counterparty_id, method_id, change,
changed_at, changed_by)`, `bill_documents(bill_id, text)`, `payments(id, proposal, decision_id,
status, executed_at)`, `agents`, `authorizations`, `nonces`, `decisions`.

## Gateway API

| Method and path | Purpose | Auth |
| --- | --- | --- |
| `POST /v1/actions/propose_payment` | the one agent action; returns the decision and evidence id | signed |
| `GET /v1/decisions/{id}`, `GET /v1/decisions` | evidence records | none (demo) |
| `POST /v1/agents`, `POST /v1/agents/{id}/revoke` | registry | none (demo; admin in reality) |
| `POST /v1/authorizations`, `POST /v1/authorizations/{id}/revoke` | authorizations | none |
| `POST /v1/challenges/{id}/resolve` | a human approves or rejects a held action; recorded with provenance | none |
| `POST /v1/scenarios/{name}/run` | runs a named demo scenario end to end with a built-in signed agent | none |
| `GET /v1/eval/latest` | the last evaluation report as JSON | none |
| `GET /v1/rho/health` | active backend; in live mode, counts from one read call (ext. 1) | none |

## Decision flow and policy (policy version `2026-10-28.1`)

1. **Identity.** Not `verified` → **block**, reason `identity:<result>`. Stop.
2. **Authorization.** Any violation → **block**, reasons `authorization:<field>`, all violations
   listed. Stop. (Extension 3 moves `limit` violations to `challenge: renew_authorization`.)
3. **Risk.** Tier 0 always; the cheap tier and tier 2 per the active configuration and the
   escalation rule ([0007](../decisions/0007-risk-tiers.md)). Result: `level`, `signals[]`,
   `tiers_run[]`, `model_ids[]`, `usage`, `latency_ms`.
4. **Policy table**, first match:

   | Condition | Decision | Challenge type | Reason code |
   | --- | --- | --- | --- |
   | risk high **and** (`bill_mismatch` or `document_instruction_patterns` or model `injection_detected`) | block | | `risk:high_with_redirect_pattern` |
   | risk high | challenge | `confirm` (`verify_payee` in ext. 3) | `risk:high` |
   | amount > `human_approval_above` | challenge | `confirm` | `authorization:human_approval_threshold` |
   | risk elevated | challenge | `confirm` (`verify_payee` in ext. 3) | `risk:elevated` |
   | otherwise | allow | | `clean` |

5. **Execute.** `allow` → simulated payment `executed`; `challenge` → `held` until resolved; `block`
   → `blocked`. The evidence record is written before any of these.

## Evidence record

```json
{
  "schema_version": 1, "decision_id": "...", "created_at": "...", "policy_version": "2026-10-28.1",
  "configuration": {"tiers": ["tier0", "haiku", "opus"], "escalation": {"confidence_min": 0.8}},
  "action": { "...the proposal as received..." },
  "identity": {"claimed_agent_id": "...", "result": "verified", "business_id": "...", "owner": "...",
               "key_id": "...", "checked": ["known", "active", "timestamp", "nonce", "signature"]},
  "authorization": {"authorization_id": "...", "version": 1, "violations": [], "snapshot": { "...as stored..." }},
  "risk": {"level": "elevated", "tiers_run": ["tier0", "haiku"],
           "features": {"payment_method_changed_days_ago": {"value": 3, "evidence": ["pmh_42"]}},
           "tier_results": [{"tier": "haiku", "model": "claude-haiku-5-5", "level": "elevated", "confidence": 0.71, "latency_ms": 640}],
           "signals": [{"name": "payment_method_changed", "severity": "elevated", "evidence": ["pmh_42"]}],
           "model_rationale": null},
  "decision": "challenge", "reasons": ["risk:elevated"],
  "challenge": {"type": "confirm", "routed_to": "owner", "user_sees": "one approve / reject"},
  "friction_rung": 2,
  "execution": {"status": "held", "simulated": true},
  "cost": {"input_tokens": 1900, "output_tokens": 120, "usd": 0.00025},
  "latency_ms": {"identity": 1, "authorization": 2, "risk": 644, "total": 650},
  "review": null
}
```

`review`, once a human resolves a challenge, holds `{by, at, outcome, note, provenance:
"human_ui"}`. `model_rationale` is model output and labelled so by the site.

## Seed data and scenarios

`scripts/make_seed.py` writes `data/seed/`: one business, 3 accounts, ~40 counterparties (1–2
payment methods each, created dates), ~400 outgoing transactions over 12 months with per-vendor
amount distributions, ~60 bills with short invoice texts, a payment-method history. Deterministic
from a fixed random seed. Staging holds one vendor, no bills and a single funding deposit
([../reference/staging-data.md](../reference/staging-data.md)), so the seed is shaped from
assumptions about a small business's payables, not from staging statistics, and the README says so.
Amounts follow Rho's `Money` shape: integer minor units with a currency code. The one real vendor's
shape (five payment methods: ACH, wire, check, two international) is a useful template for
synthetic counterparties.

`eval/cases.py` writes `data/eval/cases.jsonl`. Each case: `category`, `setup` (mutations applied
to a fresh seed, e.g. "change method 3 days ago", "insert invoice text"), `agent` (which built-in
agent signs, or how the signature is broken), `proposal`, `expected`, `also_acceptable`,
`provenance: "synthetic:eval/cases.py@<git sha>"`.

| Category | Count | Expected | Examples |
| --- | --- | --- | --- |
| A legitimate routine | 10 | allow | established vendor, typical amount, bill matches, inside authorization |
| B authorization violations | 8 | block | over per-payment cap, expired, revoked, denylisted counterparty, action not permitted |
| C identity failures | 6 | block | unknown agent, bad signature, replayed nonce, stale timestamp, revoked agent, unsigned |
| D authorized but suspicious | 8 | challenge | method changed <7 days, amount 5× vendor median, new counterparty |
| E adversarial | 8 | block (challenge acceptable) | invoice text instructing "remit to new account", proposal counterparty ≠ bill counterparty, rationale citing "updated instructions" |
| F ambiguous (ext. 6) | 5 | challenge (allow acceptable) | new vendor, small amount, clean documents |

The five **demo scenarios** are one hand-picked case from each of A–E, exposed as
`POST /v1/scenarios/{name}/run` and to the site through the demo API.

## Evaluation runner

`eval/run.py --config rules|cheap|strong|cascade` applies each case's `setup` to a fresh copy of
the seed, signs and sends the proposal, records the decision and evidence, and restores. Output:
`data/eval/results/<config>.jsonl` and a combined `report.json` / `report.md` with the metrics in
[evaluation.md](evaluation.md) and a confusion matrix per configuration. The site
reads `report.json`.

Budget on the owner's Console key: the `strong` arm is ~40 calls to Opus 5.5 at roughly 2k input
and 300 output tokens, about $0.40–0.60 per run; `cheap` and `cascade` are a fraction of that.
Ten full runs during development stay under $10.

## Site and integration

The demo interface is a separate effort in `site/`, built in parallel against
[../reference/demo-api.md](../reference/demo-api.md) and the fixture in `data/fixtures/`; it holds
no decision logic. The engine's job is to serve that contract: `GET /v1/health`,
`GET /v1/scenarios`, `POST /v1/scenarios/{name}/run` returning the scenario result (context,
proposal, evidence record), `GET /v1/decisions/{id}`, `GET /v1/eval/latest`, with CORS for a local
dev server. `zeta_one/ui/` is **not** built unless integration slips past Thursday 10:00; then a
single plain page that renders the same JSON is the fallback, and the Loom shows that.

The site's first version shows one scenario, `vendor_payment_method_changed`; the other four
follow as a fast follow on the site, each with a fixture already in `data/fixtures/`. If the site
hasn't added them by the Loom, they stay reachable through the API and the fallback page.

## What the judge sees (five clicks, or one on the site)

1. Routine bill → **allow**; three rows green; no prompt.
2. Same agent, over its per-payment limit → **block**; authorization row red; no model ran.
3. Unknown agent → **block**; identity row red; nothing else evaluated.
4. Known vendor whose payment method changed 3 days ago, inside authorization → **challenge:
   confirm**; risk row amber; the feature cites the change record.
5. Invoice says "remit to new account", proposal follows it → **block**; bill mismatch, instruction
   pattern, model signal; rationale labelled as model output.

Then the evaluation tab: four configurations, accuracy against cost and latency.

## Testing

`pytest` on: signature verify (good, bad, replay, stale, revoked); each authorization check (one
violation each); tier 0 features on fixtures; the policy table row by row; evidence record required
keys and `simulated: true`; the eval runner on three cases with model tiers stubbed. Model tiers
are stubbed in tests; `--live-models` runs them for real.

## Schedule

| When | Build | Done means |
| --- | --- | --- |
| **Tue evening** | This plan. Staging checked (`scripts/staging_check.py`, done). Create a TypeSafe key, make one call, correct `reference/jev.md`. Confirm the Console key | Jev request shape known, or Haiku stays |
| **Wed morning** | `rho/models.py`, `store.py`, `snapshot.py`, `seed.py`, `make_seed.py`; `eval/cases.py` and `cases.jsonl`; store tests | `data/seed/` and `cases.jsonl` committed |
| **Wed midday** | `identity/`, `authorization/`, `decide/policy.py`, `decide/evidence.py`; gateway endpoints; `execute.py`; tests | categories B and C pass end to end with tier 0 only |
| **Wed afternoon** | `risk/features.py`, `tier0.py`, `tiers.py`, `claude.py` (Haiku and Opus adapters), `escalation.py`; stubbed tests; first real model calls | all five categories decide sensibly in the cascade |
| **Wed evening** | `eval/run.py`, `report.py`; first full four-arm run; `/v1/scenarios` and `/v1/health` match the contract; replace the fixture with a real run | `report.md` with real numbers; the site runs against the live engine |
| **Thu 08:00–11:30** | README first (quick start, diagram, reproduction, provenance, limitations, next steps); then extensions in order below; fallback page only if the site isn't integrated by 10:00 | a stranger can run it; extensions in as time allows |
| **Thu 11:30** | hard stop on extensions; smoke-run the five scenarios and the eval | |
| **Thu 12:00–14:00** | Loom: problem (30 s), the site's scenario (1 min), the other four via API or fallback page (1 min), evaluation table (45 s), live Rho read if ext. 1 landed (30 s), limits and next steps (30 s) | video uploaded |
| **Thu 14:00–16:00** | write-up from [vision.md](vision.md); repo audit (no `.env`, no snapshots, no personal data); make public; submit | form submitted by 16:30 |
| **Thu 16:30–17:00** | buffer | |

## Extensions, Thursday morning, in order

Each is ≤ 1 hour and droppable on its own; stop wherever 11:30 lands.

1. **Live Rho read**: `live.py` reusing `staging_check.py`'s client (named user agent, token from
   `.env`), `/v1/rho/health`, backend name in the banner.
2. **Jev as the cheap tier**: `jev.py` adapter; the configuration names it; Haiku stays as fallback.
3. **Challenge types** `renew_authorization` (limit violations by a verified agent) and
   `verify_payee` (payee-side risk); friction score in the report (decision 0008).
4. **Grant-authorization opening beat**: `POST /v1/agents` and `POST /v1/authorizations` exposed
   for the site to show registration, grant, then scenario 1.
5. `limits.rolling`, `lookalike_counterparty`, `off_hours`, `duplicate_candidate`.
6. Category F and the `notify` rung.
7. Observe mode: decide and record, execute regardless.
8. Evaluation chart.

## Cut list for the first version

If Wednesday slips, drop in this order: `GET /v1/eval/latest` (the site shows `report.md` as a
link) → the resolve endpoint (challenges stay held) → category E down to 4 cases → the cheap tier
(three arms: rules, strong, strong-on-tier0-band).

Never cut: signatures, authorization checks, the policy table, the evidence record, the four-arm
evaluation (or three if cut above), the simulated label, the README.

## Risks

| Risk | Mitigation |
| --- | --- |
| Staging is nearly empty (confirmed) | The seed is shaped from assumptions and says so; the live read in extension 1 shows the connection, and the video says the data is synthetic |
| Jev's request shape differs from the guides | One adapter file; Haiku is in the first version regardless |
| Model tiers disagree with hand labels on D and E | Report it; those categories exist to show where the strong tier earns its cost |
| Time | The first version is scoped to Wednesday; everything on Thursday morning is droppable |
