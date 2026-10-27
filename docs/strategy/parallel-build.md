# Parallel build: workstreams, seams and how agents work together

Written 2026-10-27, after the engine's kernel landed. Hand one workstream brief below to each coding
agent. The decisions are in [../decisions/](../decisions/), the behaviour in
[implementation-plan.md](implementation-plan.md), the guardrails in [security.md](security.md) and
the measurement in [evaluation.md](evaluation.md); this doc says who builds what and where the
pieces meet.

## The kernel everyone builds on

The kernel exists and is tested. It is the one piece the others depend on: the shared types, the
rules that decide, and an engine that already runs end to end on stand-in stages.

| File | What it fixes |
| --- | --- |
| `zeta_one/contracts.py` | Every type that crosses a module boundary: `Proposal`, `SignedRequest`, `Context`, the evidence record and its parts, `Authorization`, `Case`, `SetupOp`, and the stage protocols `IdentityVerifier`, `AuthorizationSource`, `AuthorizationChecker`, `ContextSource`, `Tier0`, `RiskTier`, `SpendSource` |
| `zeta_one/rho/models.py` | `Money` (Rho's shape); the data workstream adds the rest |
| `zeta_one/risk/escalation.py` | The floor, soft signals, the engineered escalation rule and `merge`, the only place a risk level is combined |
| `zeta_one/risk/assess.py` | Runs tier 0, then the model tiers the configuration and escalation call for; a tier that raises counts as failed |
| `zeta_one/decide/policy.py` | Identity, then authorization, then the ordered policy rows, including fail closed and `risk:lowered_by_model` |
| `zeta_one/decide/evidence.py` | Builds the evidence record, cost included |
| `zeta_one/gateway/pipeline.py` | `Engine.evaluate(request) -> (record, proposal)`: the stages in order, by protocol only |
| `zeta_one/testing/replay.py` | Stand-in stages that replay a fixture's recorded results |
| `zeta_one/gateway/app.py`, `scenarios.py` | The demo API, serving the five scenarios by replay |
| `zeta_one/db.py` | One SQLite file, `data/zeta.db`; each module owns its own tables |
| `tests/` | The fixture contract, replay of all five scenarios, rule-7 property tests, policy rows, the API |

```
                      contracts.py  (types and protocols: the seams)
                            │
   ┌──────────────┬─────────┼───────────┬──────────────┬──────────────┐
   ▼              ▼         ▼           ▼              ▼              ▼
 W1 data      W2 identity  W3 tier 0   W4 strong     W5 gateway     W6 evaluation
 Store,       + authori-   features    model tier    wiring, API,   cases, runner,
 seed,        zation       and level   (Claude)      ledger, guard- stats, report
 ContextSource                                       rails
   │              │         │           │              ▲              │
   └──────────────┴─────────┴───────────┴──── plug into Engine ───────┘
                                                (W5 wires them)
```

## Rules for every agent

1. **Own your files, and only those.** The table in each brief lists them. Read anything; edit
   only what you own. Tests go in `tests/<your area>/`.
2. **The kernel is frozen.** Don't edit `contracts.py`, `escalation.py`, `assess.py`,
   `policy.py`, `evidence.py`, `pipeline.py` or `replay.py`. If a seam doesn't fit, stop and write
   the change you need (type, field, why) to the integrator; the integrator changes the kernel and
   tells everyone. Adding an optional field is cheap; changing a required one isn't.
3. **Keep the replay tests green.** `tests/test_contract.py` replays the five fixtures through the
   real merge and policy. If your change breaks it, your change is wrong or the contract needs the
   integrator.
4. **Work in your own git worktree, and land on `main`.** Several agents can't share one working
   tree. Commit small, logical changes (AGENTS.md rule 18); to land:
   `git pull --rebase origin main && python3 scripts/check.py && git push origin HEAD:main`. No pull
   requests until the hackathon ends (rule 19).
5. **Program to the protocol, test with fakes.** Each stage is a function or object matching a
   protocol in `contracts.py`. Test yours against fakes of the others; don't wait for them.
6. **AGENTS.md applies in full**: Rho is read-only; no credentials outside `.env`; simulated
   execution says so; no model can lift a deterministic block.

Setup in a fresh worktree (the pre-push hook setting is shared by all worktrees and already on;
don't set it again):

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
```

Start as soon as you have your brief; the times below are when the pieces must meet, not when work
may begin.

## Order and handoffs

All six start at once against the kernel. The integration points, in order:

| When | Handoff | Proves |
| --- | --- | --- |
| Wed late morning | W1's `ContextSource` over the seed + W3's `tier0` | The five scenarios decide on the seed with real tier 0; W5 switches `scenarios.py` from replay |
| Wed early afternoon | W2's `verify_identity`, `load_authorization`, `check_authorization` | Categories B and C fail for the right reason on real signatures and checks |
| Wed late afternoon | W4's `StrongTier` | The engineered cascade calls Claude on escalation; scenario 5 blocks with a model signal |
| Wed evening | W5's full wiring + W6's runner on the real engine | The first real evaluation report; the site runs against the live engine |

The **integrator** is the owner's main session. It owns the kernel, `AGENTS.md`, `README.md` and
the docs, merges contract changes, and runs the integration checks at each handoff.

## Workstream briefs

Each brief can be pasted to an agent as it stands.

### W1: data (Rho stand-in, seed, context)

**Owns:** `zeta_one/rho/` except `__init__.py` (extend `models.py`; add `store.py`, `snapshot.py`,
`seed.py`, `view.py`, `mutations.py`), `scripts/make_seed.py`, `data/seed/`, `tests/rho/`.

**Builds:**
- Rho-shaped models for what the engine reads (businesses, accounts, counterparties and payment
  methods, bills, transactions), from `docs/reference/rho-openapi.json`.
- A `Store` over SQLite loaded from `data/seed/`, plus the stand-in tables Rho lacks:
  payment-method history, bill document text.
- `make_seed.py`: deterministic from a fixed random seed, two-hour box; the shape in
  [implementation-plan.md](implementation-plan.md#seed-data-and-scenarios). The five demo
  scenarios' entities are **written by hand with the fixtures' ids and values** (`cp_0007`,
  `cp_0051`, `bill_0194`, `pm_0007_03`, `acct_seed_checking_01`, the payment counts, medians and
  transaction ids); only the filler is generated.
- **The seed's clock:** `SEED_NOW = 2026-10-27T22:00:00Z` (the fixtures' `created_at`), a constant
  in `zeta_one/rho/seed.py`. Every seed date is relative to it; W5's scenarios and W6's runner pass
  it as `now`.
- **Storage:** the seed is JSON files in `data/seed/`. A `Store` loads them into its own in-memory
  SQLite database (tables prefixed `rho_`), so each evaluation case gets a fresh copy cheaply.
  `snapshot.py` is that `Store`; it never reads `data/snapshots/`, and nothing in W1 needs the VPN
  or `.env`.
- `view.context_for(store)`: a `ContextSource`. Builds `Context` for a proposal, including
  `open_bills` for the proposed counterparty, payment history joined through paid bills, and
  `bill_counterparty` when the bill's payee differs. Raises `InvalidProposal` for an unknown
  counterparty, a payment method not on it, or a source account outside the business.
- `mutations.apply(store, op: SetupOp)`: the setup ops evaluation cases use. At least
  `change_payment_method`, `set_bill_text`, `add_counterparty`, `add_bill`, `add_payments`. Document
  each op's args in the module docstring; that is W6's reference.

**Done when:** for each fixture, `context_for(store)(fixture.proposal, ...)` at `SEED_NOW` matches
the fixture's `context` (ids, amounts, counts, methods; timestamps may differ in seconds), leaving
out `open_bills`, which the fixtures don't carry and which has its own tests; `Store.seed_version`
is a hash of `data/seed/`, which W5 passes to the `Engine`; tests cover each mutation and each
`InvalidProposal` case.

### W2: identity and authorization

**Owns:** `zeta_one/identity/`, `zeta_one/authorization/`, `scripts/keygen.py`, `tests/identity/`,
`tests/authorization/`.

**Builds** (decision 0006, security.md S8, S15, S16):
- `identity/registry.py`: agents (`agent_id`, `business_id`, owner, Ed25519 public key, status) and
  nonces in SQLite tables of their own; `register`, `revoke`, `get`.
- `identity/signing.py`: `sign(private_key, agent_id, method, path, body, now)` for built-in agents
  and tests, and `verifier(registry)` returning an `IdentityVerifier`: headers present → known →
  active → timestamp within ±300 s → nonce unseen → signature over the raw bytes; the nonce is
  recorded only after the signature verifies. Each outcome maps to its `IdentityStatus`.
- `scripts/keygen.py`: writes demo agents' keys to `data/keys/` (gitignored) and
  `ZETA_ADMIN_TOKEN` to `.env` if absent; never prints a secret.
- `authorization/store.py`: authorizations by `(business_id, agent_id)`, versioned; `grant`,
  `revoke`, and a loader that is an `AuthorizationSource`.
- `authorization/check.py`: `checker(spend: SpendSource)` returning an `AuthorizationChecker`: an
  ordered list of `check_<field>` functions, every violation listed, `Money` currency-strict,
  limits inclusive, `scope` or `limit` kind, `limits.rolling` summed through `SpendSource`. A missing
  or revoked authorization is a `scope` violation.

**Done when:** tests cover good, bad, replayed, stale, revoked and unsigned requests, a nonce
surviving a restart, one violation per check, equal-to-cap and wrong-currency cases, and split
payments hitting the rolling limit with a fake `SpendSource`.

### W3: tier 0 (deterministic risk)

**Owns:** `zeta_one/risk/features.py`, `zeta_one/risk/tier0.py`, `tests/risk/test_features.py`,
`tests/risk/test_tier0.py`.

**Builds** (decision 0007, security.md S7):
- `features.py`: pure functions of `(proposal, context, now)`, each returning a `Feature` with its
  value and the ids it came from: `counterparty_is_new`, `payment_method_changed_days_ago`,
  `amount_ratio_to_vendor_median`, `bill_mismatch`, `document_instruction_patterns`,
  `bill_not_referenced`. The instruction-pattern lexicon is a module constant and is frozen before
  the evaluation's `test` set is generated.
- `tier0.py`: a `Tier0` that computes the features, bands them to `low` / `elevated` / `high`, and
  returns `Tier0Output` with signals (`source: "tier0"`). The floor is not yours: `escalation.floor`
  computes it from your features.

**Done when:** on each fixture's context and proposal, the features equal the fixture's
`risk.features` and the level equals its tier-0 result; property tests show features never read
anything but their arguments.

### W4: the strong model tier

**Owns:** `zeta_one/risk/claude.py`, `zeta_one/risk/prompts/`, `tests/risk/test_claude.py`.

**Builds** (decisions 0007, 0009, 0010; security.md S1, S2):
- `StrongTier`, a `RiskTier` named `strong`, calling `claude-opus-5-5` with structured output
  (`messages.parse` into a Pydantic model: `risk_level`, `signals[] {name, severity, evidence}`,
  `injection_detected`, `recommended_decision`, `rationale`). Read the `claude-api` skill before
  writing the call.
- The fixed system prompt, cached, in `prompts/strong.md`. Untrusted text (invoice, agent
  rationale, memo, payee names) goes in clearly delimited blocks, after the fixed instructions,
  labelled as data an attacker may have written.
- It **never raises**: timeout, API error, refusal (`stop_reason == "refusal"`) or invalid output
  returns a `TierOutput` with `result.error` set. `injection_detected` becomes a signal named
  `injection_detected`. Usage and latency go into `TierResult`; `confidence` stays `null`.
- Prices per model as a constant the engine passes to `evidence.build`.

**Done when:** tests with a stubbed client cover a normal answer, each failure kind, and a
response that tries to escape the schema; one test behind `--live-models` makes a real call. Run
the redirect fixture's input live once and record what came back.

### W5: gateway (wiring, API, ledger, guardrails)

**Owns:** `zeta_one/gateway/` except `pipeline.py` (`app.py`, `scenarios.py`, and new
`wiring.py`, `ledger.py`, `admin.py`, `reuse.py`), `tests/gateway/`.

**Builds** (implementation-plan.md API and flow; security.md S3, S4, S6, S9):
- `wiring.py`: `build_engine(store, ...)` with the real stages as they land, falling back to the
  replay stand-ins per stage until then.
- `ledger.py`: decisions and simulated payments in SQLite; `executed`, `held`, `blocked`; a
  `SpendSource` over executed and held payments for W2.
- `app.py`: `POST /v1/actions/propose_payment` (signed; returns only `decision`, `decision_id`,
  `challenge_id`; malformed body is a 400); admin endpoints (`/v1/agents`, `/v1/authorizations`,
  revoke, `/v1/challenges/{id}/resolve`) behind `ZETA_ADMIN_TOKEN`, refusing agent-signed requests;
  resolve reruns identity-free deterministic checks and compares the payment method before
  executing; the demo endpoints as they are; bind to 127.0.0.1.
- `reuse.py`: the same proposal fingerprint within 24 hours reuses the earlier risk result,
  recorded as `risk.reused_from`. Plug it in through `Engine.assess_risk`, which receives the
  engine, proposal, context, time and identity, and can call `engine.run_tiers` on a miss.
- `scenarios.py`: run the five scenarios on the seed with built-in signed agents once W1–W3 land;
  drop `illustrative` then.

**Done when:** the security.md tests for S3, S4, S6 and S9 pass; the five scenarios decide on the
real engine as their fixtures say; the site's calls in `docs/reference/demo-api.md` all work.

### W6: evaluation

**Owns:** `eval/`, `data/eval/`, `tests/eval/`.

**Builds** ([evaluation.md](evaluation.md), "For the submission"):
- `eval/cases.py`: the ~20 deterministic cases as `Case` objects, labels by construction.
- `eval/generate.py`: `combos` and `assemble` around the wording subagent; `eval/prompts/wording.md`.
- `eval/label.py`: `export` (blind view) and `merge`; `eval/prompts/label.md`.
- `eval/run.py`: applies each case's `setup` through W1's `mutations.apply` to a fresh store,
  signs with the case's agent, runs `Engine.evaluate`, writes results; configurations
  `always_allow`, `always_challenge`, `rules`, `engineered`, `strong`.
- `eval/stats.py`: Wilson intervals, the discordant table and pooled McNemar, κ with a bootstrap.
- `eval/report.py`: `report.json` and `report.md` with everything evaluation.md lists.

**Done when:** the runner, stats and report work end to end against the replay engine and fake
cases before the real engine lands, and then against it; stats are tested against known values.
The owner runs the wording and labelling subagents and writes the `hard` set; W6 prepares the
inputs and merges the outputs.

## What the integrator checks at each handoff

- `python3 scripts/check.py` passes on `main`.
- The five scenarios still decide as their fixtures say, now with more real stages.
- No file outside a workstream's list changed in its commits.
- Any contract change is reflected in `docs/reference/demo-api.md` in the same commit.
