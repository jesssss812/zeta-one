# Roadmap

What is not done, as of 2026-10-27. Remove a line when it is done.

## Before implementation

- Create a TypeSafe key, make one Jev call, and correct `docs/reference/jev.md`.
- Confirm the Console key, the Claude model ids and the `messages.parse` call with one request.
- Test Rho's MCP connector in claude.ai (Connectors → Rho): does it connect, and what tools does
  it list? Record the answer in `docs/reference/rho-api.md`.
- Write the five demo scenario cases before building the engine (`eval/cases.py`); the generated
  and hand-written evaluation sets follow once the engine runs.

The build order, schedule and cut list are in
[strategy/implementation-plan.md](strategy/implementation-plan.md).

## First version (Wednesday)

- Local Rho stand-in on the committed synthetic seed (decisions 0002, 0005).
- Gateway: tier-0 risk, policy table with `confirm` challenges, evidence record and the scenario
  endpoints first; then signed-request identity and authorization checks; then the strong-model
  adapter with engineered escalation; simulated execution throughout (decisions 0006–0009).
- The demo API in `docs/reference/demo-api.md` serving the site; no UI of its own.

## Security guardrails (Wednesday, with the module each protects)

Detail, tests and estimates are in [strategy/security.md](strategy/security.md); the decisions in
[decisions/0010-gateway-guardrails.md](decisions/0010-gateway-guardrails.md).

- Model failure, timeout, invalid output or refusal gives `challenge` (fail closed).
- A model's lowering of soft-signal risk is recorded in the evidence and the reasons.
- The same proposal within 24 hours reuses its risk result: no re-rolling.
- The agent gets back only the decision and ids.
- Admin token on granting, revoking and resolving; agent-signed requests refused; bound to
  127.0.0.1.
- The gateway looks up open bills itself; `bill_not_referenced` is a hard flag.
- `limits.rolling` checked in the first version.
- Approving a held payment rechecks authorization and the payment method first.
- Nonces in SQLite; demo agent keys generated into gitignored `data/keys/`; live Rho client GET
  only; site renders untrusted text as text.
- A Claude Code hook refusing shell commands that touch `.env` or `*.ovpn`.
- The README's limits section: what Zeta One doesn't cover.

## Evaluation

The plan is in [strategy/evaluation.md](strategy/evaluation.md); the times are in the schedule in
[strategy/implementation-plan.md](strategy/implementation-plan.md#schedule). Items marked
**owner** need the owner's own time.

Wednesday:

- ~20 deterministic cases in `eval/cases.py`: one per identity, authorization and guardrail
  check, labels by construction.
- Rule-7 property tests: a hostile model stub never lowers the tier-0 floor or lifts a block.
- **Owner:** write the `hard` set, 15–20 risk cases outside the generator's templates (~1.5 h).
- `eval/generate.py` and `eval/prompts/wording.md`: dimensions, combinations, harmless
  look-alikes; wording by a Claude Haiku 5.5 subagent; `dev` ~50.
- **Owner:** read ~20 `dev` cases and write the one-page labelling guide (~30 min).
- `eval/label.py` and `eval/prompts/label.md`: a blind Claude Sonnet 5.5 subagent labels `dev`.
- `eval/run.py` with the trivial baselines, rules, engineered and strong; `eval/stats.py` (Wilson
  intervals, discordant table, pooled McNemar, κ with bootstrap); `eval/report.py`.
- Runs on `dev`; failures-by-stage table; tune on `dev` only.
- Freeze the tier-0 instruction lexicon, then generate `test` ~100 with a new seed and wording;
  hash it; AI-label it.

Thursday 08:00–09:30:

- **Owner:** label 40 stratified suspicious, adversarial and ambiguous `test` cases blind, then
  adjudicate disagreements (~1 h).
- Scored run of every configuration on `test`, `hard` and the identity and authorization cases.
- Final `report.md`: per-category rates with intervals, confusion matrices, `dev` / `test` /
  `hard` side by side, agreement, cost and latency, limitations.
- Replace the fixtures' numbers with this run.

If time allows (extensions 2 and 3 below, then 11):

- Repeat runs (3×, through the Batches API) with pass^3.
- Attacking model, ~20 attempts per configuration, aimed first at model lowering of soft
  signals.
- Expected cost with the halved and doubled missed-fraud weight.

## Extensions (Thursday morning, in the plan's order)

Live Rho read; repeat runs with pass^3; attacking model; Jev as the cheap tier;
`renew_authorization` and `verify_payee` challenge types with the friction score;
grant-authorization beat; extra tier-0 features; `notify`; observe mode; open-weight comparison
arm; expected cost and an evaluation chart.

## Stretch (after the hackathon)

- Evaluation follow-ups listed in [strategy/evaluation.md](strategy/evaluation.md#after-the-hackathon).
- Security follow-ups listed in [strategy/security.md](strategy/security.md#later): snapshot
  comparison of payment methods, signed authorizations, hash-chained evidence, rate limits, key
  rotation.
- Approval side panel: poll Rho items waiting for approval and score them (decision 0003).
- AI-assisted case review (P2).

## Submission (by Thu Oct 29, 5:00 PM CT)

- **Owner:** connect the repo to Vercel, serving `site/` as a static site (decision 0011).
- A script that records the real engine's five scenario results and the evaluation report into
  `site/data/`, dated and labelled as recorded; run it after the final evaluation.

- Confirm the track (aimed at Rho fintech).
- README sections the checklist requires; see `docs/reference/hackathon.md`.
- Loom video, 2–5 minutes.
- 150–300 word write-up.
- Make the repo public, after checking it holds no personal details, raw staging data or
  credentials.
