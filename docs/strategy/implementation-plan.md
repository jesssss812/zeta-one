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
three questions answered separately, then opens an evaluation table with the configurations side
by side with intervals: accuracy, hard-constraint accuracy, detection, challenge rate, cost per
action, latency, on generated and hand-written cases.
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
| Authorization | `actions`, `counterparties` (any / allowlist / denylist), `allow_new_counterparties`, `limits.per_payment` (currency-strict), `expires_at`, `status`, `human_approval_above`; `source_account_id` ∈ business always | `limits.rolling` (ext. 4), `source_accounts`, `payment_method_types`, signed grants |
| Risk | tier 0 with five features: `counterparty_is_new`, `payment_method_changed_days_ago`, `amount_ratio_to_vendor_median`, `bill_mismatch`, `document_instruction_patterns`; the merge rule (tier-0 flags are a floor); strong tier `claude-opus-5-5` structured output; **engineered escalation**: strong runs only when tier 0 is not clean (decision 0009) | Jev as the cheap tier (ext. 5); `duplicate_candidate`, `lookalike_counterparty`, `off_hours`, `agent_velocity`; an open-weight comparison arm |
| Policy | `allow` / `challenge` (type `confirm`) / `block`; versioned ordered rule table | challenge types `renew_authorization`, `verify_payee`, `notify` (decision 0008) |
| Evidence | the full schema below, from the first commit | nothing: the schema is the extensibility |
| Execution | simulated; `held` on challenge; `POST /v1/challenges/{id}/resolve` | observe mode |
| Data | committed synthetic seed, deterministic from a fixed random seed, minor-unit amounts | live Rho backend (shows one vendor and one deposit: the connection, not the data) |
| Evaluation | the five demo cases first; ~14 identity and authorization cases; generated risk sets `dev` ~50 and `test` ~100 plus a hand-written `hard` set; one AI labeller checked by the owner; trivial baselines and three configurations (rules, engineered cascade, strong everywhere); per-category `report.md` and `report.json` with intervals; property tests for rule 7 | repeat runs, attacking model, expected cost, the Jev and open-weight arms, friction score |
| Interface | the demo API in [../reference/demo-api.md](../reference/demo-api.md), served with CORS; the site in `site/` renders it | registration and grant endpoints for the site; resolve with type; evaluation JSON |

Nothing on Wednesday's path depends on Jev: the engineered cascade is the default configuration,
and the Jev arm joins on Thursday when its call works.

## The seven seams

Designed once, so each extension is additive:

1. `rho.store.Store` protocol; `snapshot.py` implements it now, `live.py` later.
2. `risk.RiskTier` protocol: `assess(ctx) -> TierResult {level, confidence, signals, model_id,
   usage, latency_ms}`; the active configuration is a list of tier names plus an escalation rule
   per tier kind; Jev, Claude and an OpenAI-compatible adapter are three implementations of one
   shape. `escalation.merge()` applies the floor rule from 0007 and is the only place a level is
   combined.
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
  risk/           features.py  tier0.py  tiers.py (protocol)  escalation.py (merge + rules)  claude.py  jev.py (ext. 5)  openai_compat.py (optional)
  decide/         policy.py  evidence.py
  gateway/        app.py  execute.py  scenarios.py
eval/             cases.py  generate.py  label.py  run.py  stats.py  report.py  attack.py (ext. 3)
site/             the demo site, separate effort (see Site and integration)
scripts/          check.py  staging_check.py (exist)  make_seed.py  keygen.py
tests/
data/             seed/ (committed, synthetic)  fixtures/ (illustrative API responses)  eval/ (dev, test, hard, labels, results/)  snapshots/ (gitignored)
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
   listed. Stop. (Extension 6 moves `limit` violations to `challenge: renew_authorization`.)
3. **Risk.** The request is first validated (payment method belongs to the counterparty, else
   rejected). Tier 0 always; later tiers per the active configuration and its escalation rules;
   the final level comes from the merge rule, with tier-0 flags as a floor
   ([0007](../decisions/0007-risk-tiers.md)). Result: `level`, `level_set_by`, `floor`,
   `signals[]`, `tiers_run[]`, `tier_results[]`.
4. **Policy table**, first match:

   | Condition | Decision | Challenge type | Reason code |
   | --- | --- | --- | --- |
   | risk high **and** (`bill_mismatch` or `document_instruction_patterns` or model `injection_detected`) | block | | `risk:high_with_redirect_pattern` |
   | risk high | challenge | `confirm` (`verify_payee` in ext. 6) | `risk:high` |
   | `counterparty_is_new` and `allow_new_counterparties` is false | challenge | `confirm` | `authorization:new_counterparty_requires_approval` |
   | amount > `human_approval_above` | challenge | `confirm` | `authorization:human_approval_threshold` |
   | risk elevated | challenge | `confirm` (`verify_payee` in ext. 6) | `risk:elevated` |
   | otherwise | allow | | `clean` |

   The table is data: a list of rows under `policy_version`, evaluated in order. Rows that depend on
   risk read the merged level, which a model cannot lower below the tier-0 floor, so the first row
   holds whenever tier 0 saw a redirect pattern.

5. **Execute.** `allow` → simulated payment `executed`; `challenge` → `held` until resolved; `block`
   → `blocked`. The evidence record is written before any of these.

## Evidence record

```json
{
  "schema_version": 1, "decision_id": "...", "created_at": "...", "policy_version": "2026-10-28.1",
  "engine_version": "<git sha>", "seed_version": "<sha256 of data/seed>",
  "configuration": {"tiers": ["tier0", "strong"], "escalation": "engineered"},
  "action": { "...the proposal as received..." },
  "identity": {"claimed_agent_id": "...", "result": "verified", "business_id": "...", "owner": "...",
               "key_id": "...", "timestamp": "...", "nonce": "...",
               "checked": ["present", "known", "active", "timestamp", "nonce", "signature"]},
  "authorization": {"authorization_id": "...", "version": 1, "violations": [], "snapshot": { "...as stored..." }},
  "risk": {"level": "elevated", "level_set_by": "tier0", "floor": {"level": "elevated", "flags": ["payment_method_changed_days_ago"]},
           "tiers_run": ["tier0"],
           "features": {"payment_method_changed_days_ago": {"value": 3, "evidence": ["pmh_42"]}},
           "tier_results": [{"tier": "tier0", "model": null, "level": "elevated", "confidence": null, "signals": ["payment_method_changed"], "latency_ms": 2, "usage": null}],
           "signals": [{"name": "payment_method_changed", "severity": "elevated", "evidence": ["pmh_42"], "source": "tier0"}],
           "model_rationale": null},
  "decision": "challenge", "reasons": ["risk:elevated"],
  "challenge": {"type": "confirm", "routed_to": "owner", "user_sees": "one approve / reject"},
  "friction_rung": 2,
  "execution": {"status": "held", "simulated": true},
  "cost": {"input_tokens": 0, "output_tokens": 0, "usd": 0.0, "prices_used": {}},
  "latency_ms": {"identity": 1, "authorization": 2, "risk": 2, "total": 6},
  "review": null
}
```

Tier roles are `tier0`, `cheap` (Jev, or an open-weight model in that arm) and `strong`; the model
id lives in `model`. `review`, once a human resolves a challenge, holds `{by, at, outcome, note,
provenance: "human_ui"}`. `model_rationale` and `action.agent_rationale` are both text an attacker
can influence and are labelled so by the site. A pytest loads every fixture in `data/fixtures/`
into the evidence-record model, so the contract and the engine can't drift silently.

## Seed data and scenarios

`scripts/make_seed.py` writes `data/seed/`, **time-boxed to two hours**: one business, 3 accounts,
the ~8 counterparties the five scenarios need plus ~15 filler (1–2 payment methods each), ~150
outgoing transactions over 12 months with per-vendor amount distributions, ~30 bills with short
invoice texts, a payment-method history. Deterministic from a fixed random seed; a hash of the
directory is the `seed_version` in every record. Staging holds one vendor, no bills and a single
funding deposit ([../reference/staging-data.md](../reference/staging-data.md)), so the seed is
shaped from assumptions about a small business's payables, not from staging statistics, and the
README says so. The one real vendor's shape (five payment methods: ACH, wire, check, two
international) is the template for synthetic counterparties.

The seed follows Rho's shapes where Rho has them and says where it doesn't: `Money` is integer
minor units with a currency code; a transaction carries `counterparty_name` and no counterparty id,
so **vendor payment history is joined through bills** (`Bill.counterparty.id` → `Bill.transaction.id`)
and `method_type` is derived from `transaction_type` (`ach_debit`, `wire_out`, `check_payment`,
`international_wire_out`); payment methods carry no timestamps in Rho, so `added_at` and the
payment-method history are stand-in tables; bill document text is a stand-in table. `rho/models.py`
follows Rho; everything served to the site is a derived view and the contract says so.

Cases are data: `category`, `setup` (mutations applied to a fresh seed, e.g. "change method 3
days ago", "insert invoice text"), `agent` (which built-in agent signs, or how the signature is
broken), `proposal`, `truth`, `detectable`, `expected`, `also_acceptable`, `label_provenance`,
`provenance` (e.g. `"synthetic:eval/generate.py@<git sha>, seed 7"`). Only `proposal` and the data
reach a model tier; `category`, `setup`, labels and the name never do. How cases are generated and
labelled, and why, is in [evaluation.md](evaluation.md).

- `eval/cases.py` holds the five demo cases and ~14 identity and authorization cases, one per
  check, written by hand with labels by construction.
- `eval/generate.py` builds the risk sets from dimensions: code picks the combinations, one model
  call per case writes the invoice text and rationale. `dev` ~50 and `test` ~100 use different
  seeds and wording; `test` is hashed and frozen before its first scored run.
- `data/eval/hard/` holds 15–20 risk cases the owner writes by hand.
- `eval/label.py` runs one AI labeller, blind to `truth` and the dimensions, and merges the owner's
  labels and adjudications.

| Category | Expected | Examples |
| --- | --- | --- |
| A legitimate routine | allow | established vendor, typical amount, bill matches, inside authorization; also harmless look-alikes such as a verified change of bank details |
| B authorization violations | block | over per-payment cap, expired, revoked, denylisted counterparty, action not permitted |
| C identity failures | block | unknown agent, bad signature, replayed nonce, stale timestamp, revoked agent, unsigned |
| D authorized but suspicious | challenge | method changed <7 days, amount 5× vendor median, new counterparty |
| E adversarial | block (challenge acceptable) | invoice text instructing "remit to new account", proposal counterparty ≠ bill counterparty, rationale citing "updated instructions" |
| F ambiguous | challenge (allow acceptable) | new vendor, small amount, clean documents |

B and C are the ~14 hand-written cases. A, D, E and F make up the risk sets: `test` has about 35
legitimate, 35 suspicious and 30 adversarial or ambiguous.

The five **demo scenarios** are one hand-picked case from each of A–E, exposed as
`POST /v1/scenarios/{name}/run` and to the site through the demo API.

## Evaluation runner

`eval/run.py --set dev|test|hard|authz --config always_allow|always_challenge|rules|engineered|strong|jev|openweight [--runs N]`
applies each case's `setup` to a fresh copy of the seed, signs and sends the proposal, records the
decision and evidence, and restores. Cases within an arm run concurrently (a few at a time); no
model response is cached. Output: `data/eval/results/<set>-<config>.jsonl` and a combined
`report.json` / `report.md` with the per-category metrics in [evaluation.md](evaluation.md):
Wilson intervals, a confusion matrix per configuration, the discordant-case table, `dev` / `test` /
`hard` side by side, failures by stage, label agreement, and the seed, set hashes, model ids and
prices. The site reads `report.json`.

Budget on the owner's Console key, at Opus 5.5's $4 / $20 per million input / output tokens: one
call at roughly 2k input and 300 output tokens, plus thinking at effort `medium` (it can't be turned
off), costs about $0.015–0.03. A full `strong` run over all risk sets (~170 cases) is about $3–5;
`engineered` is a fraction of that. Repeat runs don't need latency, so they go through the Message
Batches API at half price. Generating and labelling the sets once is about $3–5 on the API, or runs
as Claude Code subagents on the owner's subscription with the prompts committed. Development and
final runs stay under $40. The subscription doesn't cover the gateway's own model calls: those need
the Console key, which is also what a judge reproducing the run would use.

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

Then the evaluation: configurations side by side, per category, accuracy against cost and latency.

## Testing

`pytest` on: signature verify (good, bad, replay, stale, revoked, nonce recorded only after
verify); each authorization check (one violation each, plus a wrong-currency and an equal-to-cap
case); tier 0 features on fixtures; the merge rule (a model answer of `low` cannot lower a tier-0
floor); the policy table row by row; evidence record required keys and `simulated: true`; every
file in `data/fixtures/` loads into the evidence-record model; the eval runner on three cases with
model tiers stubbed; Wilson intervals and the discordant table against known values. Property tests
(Hypothesis) with a hostile model stub that always answers `low` and `allow`: the merged level
never falls below the tier-0 floor and no identity or authorization block is lifted. Model tiers are stubbed in tests; `--live-models` runs them for real.

## Schedule

| When | Build | Done means |
| --- | --- | --- |
| **Tue evening** | This plan. Staging checked (done). Create a TypeSafe key, make one Jev call, correct `reference/jev.md`. Confirm the Console key, the Claude model ids and `messages.parse` with one request. Test Rho's MCP connector in claude.ai and note the tool list | Jev request shape known or the arm waits; Rho connector facts recorded |
| **Wed 08:00–10:00** | `rho/models.py`, `store.py`, `snapshot.py`, `seed.py`, `make_seed.py` (two-hour box); the five demo cases in `eval/cases.py` | `data/seed/` and the five cases committed |
| **Wed 10:00–13:00** | `risk/features.py`, `tier0.py`, `escalation.merge`, `decide/policy.py`, `decide/evidence.py`, `execute.py`; `gateway/app.py` with `/v1/health`, `/v1/scenarios`, `/v1/scenarios/{name}/run`, identity and authorization **stubbed** as verified / no violations; fixture-vs-schema test | **the first judge-visible slice**: five scenarios decide over the API on tier 0 alone; the site can switch from fixtures to live |
| **Wed 13:00–15:30** | `identity/` (real signatures, replay, revocation), `authorization/` (real checks), `/v1/actions/propose_payment`; tests; `scenarios.py` signs with built-in agents; the ~14 identity and authorization cases | categories B and C pass end to end; scenarios 3 and 4 now fail for the right reason |
| **Wed 15:30–18:00** | `tiers.py`, `claude.py` (Opus, structured output), escalation rules; stubbed tests and the rule-7 property tests; first real model calls on the redirect scenario. Owner, in a break: write the `hard` set (~1.5 h) | the engineered cascade runs; scenario 5 blocks with a model signal; `hard` committed |
| **Wed evening** | `generate.py` and `dev`; owner reads ~20 `dev` cases and writes the labelling guide; `label.py` on `dev`; `run.py`, `stats.py`, `report.py`; runs on `dev` and failures by stage; tune on `dev` only; then generate and freeze `test`, run the AI labeller on it | `dev` report with real numbers; `test` frozen and AI-labelled; the site runs against the live engine |
| **Thu 08:00–09:30** | Owner labels 40 `test` risk cases and adjudicates (~1 h); κ; the scored run of every configuration on `test`, `hard` and the identity and authorization cases; replace the fixtures' numbers with this run | the final `report.md`, with intervals, agreement and limitations |
| **Thu 09:30–11:30** | README first (quick start, diagram, reproduction, provenance, limitations, next steps); then extensions in order below; fallback page only if the site isn't integrated by 10:00 | a stranger can run it; extensions in as time allows |
| **Thu 11:30** | hard stop on extensions; smoke-run the five scenarios and the eval | |
| **Thu 12:00–14:00** | Loom: problem (30 s), the site's scenario (1 min), the other four via API or fallback page (1 min), evaluation table (45 s), live Rho read if ext. 1 landed (30 s), limits and next steps (30 s) | video uploaded |
| **Thu 14:00–16:00** | write-up from [vision.md](vision.md); repo audit (no `.env`, no snapshots, no personal data); make public; submit | form submitted by 16:30 |
| **Thu 16:30–17:00** | buffer | |

## Extensions, Thursday morning, in order

Each is ≤ 1 hour and droppable on its own; stop wherever 11:30 lands.

1. **Live Rho read**: `live.py` reusing `staging_check.py`'s client (named user agent, token from
   `.env`) for `/v1/rho/health` and a counterparty read; backend name in the banner. The live
   backend cannot supply history or bill text, so it is a connection proof, not a `Store`.
2. **Repeat runs**: the model arms 3 times on the risk sets; decision changes and pass^3 in the
   report.
3. **Attacking model**: `eval/attack.py`, ~20 attempts per configuration to get a redirected
   payment allowed; the count and its interval in the report.
4. **`limits.rolling`**: a sum over executed and held payments in the window; closes the
   split-payment gap.
5. **Jev as the cheap tier**: `jev.py` adapter, its escalation rule, its raw probabilities in the
   report; the `jev` arm in the evaluation.
6. **Challenge types** `renew_authorization` (limit violations by a verified agent) and
   `verify_payee` (payee-side risk); friction score in the report (decision 0008).
7. **Grant-authorization opening beat**: `POST /v1/agents` and `POST /v1/authorizations` exposed
   for the site to show registration, grant, then scenario 1.
8. `duplicate_candidate` (incl. `Bill.status == paid`), `lookalike_counterparty`, `off_hours`.
9. The `notify` rung.
10. Observe mode: decide and record, execute regardless.
11. Open-weight comparison arm through `openai_compat.py` (decision 0009).
12. Expected cost in the report, and an evaluation chart.

## Cut list for the first version

If Wednesday slips, drop in this order: `GET /v1/eval/latest` (the site shows `report.md` as a
link) → the resolve endpoint (challenges stay held) → the `strong` arm of the evaluation (keep the
engineered cascade's model calls on the demo scenarios) → `test` down to ~60 cases → the owner's
sample down to 25 cases.

Never cut: the five scenario endpoints and `/v1/health` (the site's whole surface), signatures,
authorization checks, the policy table and merge rule, the rule-7 property tests, the evidence
record, the rules and engineered arms of the evaluation, the frozen `test` and the `hard` set, the
owner's check of the AI labels, intervals on every rate, the simulated label, the README.

## Risks

| Risk | Mitigation |
| --- | --- |
| Staging is nearly empty (confirmed) | The seed is shaped from assumptions and says so; the live read in extension 1 shows the connection, and the video says the data is synthetic |
| Jev's request shape differs from the guides, or no key arrives | One adapter file on Thursday; nothing on Wednesday's path uses it |
| The Wednesday-morning seed and cases eat the day | Two-hour box; the five demo cases only; filler later |
| The generator mirrors tier 0's features, so the rules look near-perfect by construction | Harmless look-alikes in the sets; the lexicon frozen before `test`; the `hard` set as the headline for risk; the limitation stated in the report |
| The owner's labelling time competes with the build | Guide from ~20 cases, 40 labelled cases, `hard` written in a break; ~3–4 h in all |
| Model tiers disagree with hand labels on D and E | Report it; those categories exist to show where the strong tier earns its cost |
| Time | The first version is scoped to Wednesday; everything on Thursday morning is droppable |
