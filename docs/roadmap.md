# Roadmap

What is not done, as of 2026-10-27. Remove a line when it is done.

## Before implementation

- Create a TypeSafe key, make one Jev call, and correct `docs/reference/jev.md`.
- Confirm the Console key, the Claude model ids and the `messages.parse` call with one request.
- Test Rho's MCP connector in claude.ai (Connectors → Rho): does it connect, and what tools does
  it list? Record the answer in `docs/reference/rho-api.md`.
- Write the five demo scenario cases before building the engine (`eval/cases.py`); the rest of the
  ~40 follow once the engine runs.

The build order, schedule and cut list are in
[strategy/implementation-plan.md](strategy/implementation-plan.md).

## First version (Wednesday)

- Local Rho stand-in on the committed synthetic seed (decisions 0002, 0005).
- Gateway: tier-0 risk, policy table with `confirm` challenges, evidence record and the scenario
  endpoints first; then signed-request identity and authorization checks; then the strong-model
  adapter with engineered escalation; simulated execution throughout (decisions 0006–0009).
- Evaluation run across the configurations in `docs/strategy/evaluation.md`.
- The demo API in `docs/reference/demo-api.md` serving the site; no UI of its own.

## Extensions (Thursday morning, in the plan's order)

Live Rho read; rolling limit; Jev as the cheap tier; `renew_authorization` and `verify_payee`
challenge types with the friction score; grant-authorization beat; extra tier-0 features; category
F and `notify`; observe mode; open-weight comparison arm; evaluation chart.

## Stretch (after the hackathon)

- Approval side panel: poll Rho items waiting for approval and score them (decision 0003).
- AI-assisted case review (P2).

## Submission (by Thu Oct 29, 5:00 PM CT)

- Confirm the track (aimed at Rho fintech).
- README sections the checklist requires; see `docs/reference/hackathon.md`.
- Loom video, 2–5 minutes.
- 150–300 word write-up.
- Make the repo public, after checking it holds no personal details, raw staging data or
  credentials.
