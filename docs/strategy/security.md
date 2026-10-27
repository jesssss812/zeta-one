# Security: where Zeta One adds risk, and the guardrails

Written 2026-10-27, before any code. Zeta One is a security product, so the places where it adds
risk of its own matter as much as the risks it catches. This doc lists them, says which are fixed in
the first version, which come later and which are accepted limits, and describes the work for each.
The decisions behind the fixes are in
[../decisions/0010-gateway-guardrails.md](../decisions/0010-gateway-guardrails.md); what is not done
is tracked in [../roadmap.md](../roadmap.md).

## What is protected, and from whom

```
  untrusted                         │ the gateway (trusted)                 │ trusted, held only here
                                    │                                       │
  agent (customer's or 3rd party) ──┼─▶ identity ─▶ authorization ─▶ risk ──┼─▶ execute (simulated)
  invoice text, agent rationale,    │        │            │           │     │   Rho read token (.env)
  memo, payee names                 │        └──── policy ┴───────────┘     │   admin token (.env)
                                    │                │                      │
  strong model's answer ◀───────────┼── reads untrusted text                │
                                    │                ▼                      │
  person approving a challenge ◀────┼── evidence record ── resolve ─────────┤
```

- **Assets:** money (simulated here, real in production), the authority to execute, the Rho token,
  the integrity of evidence records, and the claim the product makes.
- **Attackers:** a compromised or manipulated agent; an outside party who controls documents the
  agent reads (invoice fraud, prompt injection); an insider who can shape vendor records; anyone who
  can reach the gateway's endpoints.
- **Trust boundary:** everything an agent sends, and every document it cites, is untrusted. So is
  the strong model's answer, because it read untrusted text. Only the gateway's own code, its data
  store and people holding the admin token are trusted.

## Threats and what answers them

First version means it ships for the submission. Later means after the hackathon. Accepted means a
known limit, stated in the README.

### From models and other non-deterministic parts

| # | Threat | Answer | When |
| --- | --- | --- | --- |
| S1 | The strong model reads attacker-written text and is talked into a lower risk level | Hard flags set a floor no model can lower (decision 0007). Soft signals may be lowered by the model; each lowering is recorded and is the main target of the attacking-model evaluation | First version |
| S2 | A model call fails, times out, returns malformed output or refuses, possibly because an attacker put refusal-triggering text in an invoice | Fail closed: any model error gives `challenge` | First version |
| S3 | Model answers vary, so a compromised agent resubmits until one run allows | The risk result for the same proposal is reused for 24 hours; a repeated blocked proposal counts toward agent velocity | First version |
| S4 | The agent learns from the response which signal fired, and adjusts | The agent receives only the decision and ids; reasons and evidence are for people | First version |
| S5 | The model's rationale, echoing the invoice, steers the person approving a challenge | Evidence first, rationale collapsed and labelled as untrusted text | First version (site) |

### From the design

| # | Threat | Answer | When |
| --- | --- | --- | --- |
| S6 | An agent approves its own challenge, registers itself, or grants itself authority: those endpoints are unauthenticated | Admin token on every endpoint that grants, revokes or resolves; agent-signed requests rejected there; bound to 127.0.0.1 | First version |
| S7 | The agent leaves out `bill_id`, so the bill check never fires | The gateway looks up open bills for the counterparty itself; a missing bill reference is a hard flag | First version |
| S8 | Payments split under the per-payment cap and the approval threshold | `limits.rolling` in the first version | First version |
| S9 | A held payment is approved after the authorization was revoked or the vendor's bank details changed again | Resolve reruns the deterministic checks and compares the payment method with the one decided on | First version |
| S10 | An insider grooms a lookalike vendor with small payments until it looks established; a bank-detail change made before Zeta One started watching is invisible, since Rho exposes no method timestamps | Snapshot comparison over time, and asking Rho to expose method history | Later; accepted for now |
| S11 | Authorizations are stored unsigned, so whoever can write the store grants authority | Signed authorizations (decision 0006) | Later; accepted for now |
| S12 | Evidence records can be edited after the fact | Hash-chained records | Later |
| S13 | Agents that don't route through the gateway aren't covered | Stated plainly (decision 0003); a Rho pre-execution hook is the real fix | Accepted |

### From the build

| # | Threat | Answer | When |
| --- | --- | --- | --- |
| S14 | Attacker text rendered as HTML on the site | The site renders untrusted text as text only | First version (site) |
| S15 | Replay after a restart, if nonces live only in memory | Nonces in SQLite | First version |
| S16 | Demo agents' private keys committed to a public repo | Keys generated at first start into gitignored `data/keys/` | First version |
| S17 | A generated-code bug makes a write call to Rho | The live Rho client implements GET only, and a test asserts it | First version (with the live read) |
| S18 | A Claude Code session reads `.env` through the shell; the deny rules cover only the Read tool | A `PreToolUse` hook refusing shell commands that touch `.env` or `*.ovpn` | First version (dev setup) |

### From the claim

| # | Threat | Answer | When |
| --- | --- | --- | --- |
| S19 | Calling the demo "secure" overclaims: open demo endpoints, simulated payments, synthetic data | The README's limits section names S10, S11, S12 and S13, and the evaluation states what the synthetic results do not show | First version |

## The work, in detail

Estimates are build time. Each fix comes with a test or an evaluation case, so a guardrail that
breaks shows up as a failing check.

### S1: recorded lowering of soft signals (30 min)

- **Soft signals** are the tier-0 features that don't set a floor: `counterparty_is_new`,
  `amount_ratio_to_vendor_median` outside 0.5–2, and `payment_method_changed_days_ago` beyond the
  hard-flag window. A later tier may lower the level they produce; it can never lower a floor.
- When the final level is below tier 0's own level, the evidence record carries
  `risk.lowered: {from, to, by, signals}` and the reasons gain `risk:lowered_by_model`, so an
  allow that a model cleared is never shown as plain `clean`.
- **Test:** a stub model answering `low` lowers a soft-signal case and the record says so; the same
  stub on a hard-flag case changes nothing.
- **Evaluation:** the report counts lowerings on legitimate cases (the friction a model saves) and
  on fraudulent ones (the risk it adds), and the attacking model targets this path
  ([evaluation.md](evaluation.md#if-time-allows-in-order)).

### S2: fail closed on model failure (30 min)

- A tier that the escalation rule required and that errors, times out, returns output failing its
  schema, or stops with `refusal` leaves the level at tier 0's and adds a `tier_results` entry with
  `error`. A policy row sends it to `challenge` (`confirm`) with reason `risk:model_unavailable`.
- No retry loop beyond the SDK's own retries.
- **Test:** stubs for each failure kind give `challenge`. **Evaluation case:** an invoice containing
  text that triggers a refusal.

### S3: no re-rolling a decision (30 min)

- **Fingerprint:** a hash of agent, counterparty, payment method, amount, currency and bill.
- Within 24 hours, a proposal with a known fingerprint reruns identity and authorization (they are
  cheap and deterministic, and state may have changed) and reuses the earlier risk result, provided
  the counterparty's payment methods haven't changed since. The record carries
  `risk.reused_from: <decision_id>`.
- A repeated proposal whose earlier decision was `block` counts toward `agent_velocity` once that
  feature exists.
- **Test and evaluation case:** the same adversarial proposal sent five times gets the same decision
  each time, with one model call.

### S4: a minimal response to the agent (10 min)

- `POST /v1/actions/propose_payment` returns `{decision, decision_id, challenge_id}` and nothing
  else. Reasons and evidence are served by `GET /v1/decisions/{id}` to people.
- **Test:** the response has exactly those keys.

### S5 and S14: the site shows untrusted text safely (site work, 20 min)

- Untrusted fields are `proposal.agent_rationale`, `proposal.memo`, invoice text, payee names and
  `risk.model_rationale`. They are set as text, never as HTML.
- On a challenge, the cited evidence comes first; the model's rationale is collapsed and labelled
  as text an attacker can influence.

### S6: an admin token for granting and approving (45 min)

- `ZETA_ADMIN_TOKEN` in `.env`, written by `scripts/keygen.py` if absent and never printed.
- Required as a bearer token on `POST /v1/agents`, `POST /v1/agents/{id}/revoke`,
  `POST /v1/authorizations`, `POST /v1/authorizations/{id}/revoke` and
  `POST /v1/challenges/{id}/resolve`. A request to these carrying `Zeta-Agent-*` signature headers
  is rejected outright.
- The server binds to 127.0.0.1. Read endpoints and the scenario endpoints stay open, as the demo
  surface the site uses.
- **Test and evaluation case:** an agent-signed resolve of its own challenge is refused, and the
  payment stays held.

### S7: the gateway finds the bill itself (45 min)

- Tier 0 looks up open bills for the proposal's counterparty in the store, whatever the agent
  cites.
- **New hard flag `bill_not_referenced`:** the proposal names no bill while the counterparty has an
  open bill, or the payee is new or its method changed within 30 days and no bill is named. Floor
  `elevated`; `high` when the payee is new or its method changed.
- A named bill that belongs to another counterparty is already `bill_mismatch`.
- **Test and evaluation case:** the redirect scenario sent without `bill_id` is still caught.

### S8: rolling limit in the first version (1 h)

- `limits.rolling: {window_days, amount}`, summed over executed and held payments by the agent in
  the window, currency-strict, a `limit` violation.
- **Test and evaluation case:** two payments of $4,999 under a $5,000 cap and a $6,000 rolling
  limit: the second is blocked.

### S9: recheck on resolve (30 min)

- The held payment records the authorization version and the payment-method state it was decided
  on.
- On resolve with `approve`, the gateway reruns agent status, authorization status, expiry, limits
  including rolling, and compares the payment method. Any difference gives `block` with reason
  `resolve:state_changed`, recorded in `review`.
- **Test and evaluation case:** revoke the authorization while a payment is held, then approve:
  blocked.

### S15, S16, S17, S18: build hygiene (40 min in all)

- **S15:** nonces are rows in SQLite with an expiry at the edge of the timestamp window.
- **S16:** `scripts/keygen.py` writes the demo agents' keys to `data/keys/` (gitignored) on first
  start; `scripts/check.py` refuses tracked files there.
- **S17:** `rho/live.py` exposes only GET; a test inspects the client and fails on any other
  method.
- **S18:** a `PreToolUse` hook in `.claude/settings.json` refuses Bash commands that mention `.env`
  or `.ovpn`.

### S19: the README's limits (15 min, part of the README)

- Name what isn't covered: agents that bypass the gateway, groomed payee history, bank-detail
  changes made before watching began, unsigned authorizations, editable evidence, simulated
  payments, synthetic data.

## Later

- S10: snapshot comparison of counterparty payment methods over time; ask Rho to expose method
  history and a pre-execution hook.
- S11: authorizations signed with the grantor's key.
- S12: hash-chained evidence records, each holding the hash of the one before.
- Per-agent rate limits on the gateway, and key rotation.
- An attacking-model run against the deterministic stages too (malformed amounts, currency tricks,
  id confusion), beyond the property tests.
