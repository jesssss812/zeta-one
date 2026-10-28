# Roadmap

What is not done, as of 2026-10-27. Remove a line when it is done.

## Before implementation

- Create a TypeSafe key, make one Jev call, and correct `docs/reference/jev.md`.
- Confirm the Console key, the Claude model ids and the `messages.parse` call with one request.
- Test Rho's MCP connector in claude.ai (Connectors → Rho): does it connect, and what tools does
  it list? Record the answer in `docs/reference/rho-api.md`.

The build order, schedule and cut list are in
[strategy/implementation-plan.md](strategy/implementation-plan.md).

## First version (Wednesday)

- The demo API in `docs/reference/demo-api.md` serving the site; no UI of its own.

## Security guardrails (Wednesday, with the module each protects)

Detail, tests and estimates are in [strategy/security.md](strategy/security.md); the decisions in
[decisions/0010-gateway-guardrails.md](decisions/0010-gateway-guardrails.md).

- Live Rho client GET only; site renders untrusted text as text.
- A Claude Code hook refusing shell commands that touch `.env` or `*.ovpn`.

## Evaluation

The plan is in [strategy/evaluation.md](strategy/evaluation.md); the times are in the schedule in
[strategy/implementation-plan.md](strategy/implementation-plan.md#schedule). Items marked
**owner** need the owner's own time.

Wednesday:

- **Owner:** write the `hard` set, 15–20 risk cases outside the generator's templates (~1.5 h).
- Run `scripts/keygen.py` once, so the default gateway registers the demo agent.
- Use the case generator and wording prompt to assemble `dev` ~50 with independently generated
  wording and harmless look-alikes.
- **Owner:** read ~20 `dev` cases and write the one-page labelling guide (~30 min).
- Use the implemented blind export/merge workflow to label `dev`.
- Runs on `dev` with the real backend (`--backend real --live --max-usd` for the model
  configurations); failures-by-stage table; tune on `dev` only.
- Generate `test` ~100 with a new seed and wording against the frozen tier-0 lexicon;
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
