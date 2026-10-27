# Roadmap

What is not done, as of 2026-10-27. Remove a line when it is done.

## Before implementation

- Get a Jev (or OpenRouter) key, make one call, and correct `docs/reference/jev.md`.
- Write the labelled evaluation scenarios before building the engine (`eval/cases.py`).

The build order, schedule and cut list are in
[strategy/implementation-plan.md](strategy/implementation-plan.md).

## Build (P0, P1)

- Local Rho stand-in with snapshot and live backends, and the committed synthetic seed
  (decisions 0002, 0005).
- Gateway: signed-request identity, mandate checks, three-tier risk, policy table, simulated
  execution (decisions 0006, 0007).
- Evidence record for every decision.
- Evaluation run across the four configurations in `docs/strategy/evaluation.md`.
- A UI that shows the scenarios, a decision, its evidence and the evaluation table.

## Stretch

- Approval side panel: poll Rho items waiting for approval and score them (decision 0003).
- AI-assisted case review (P2).

## Submission (by Thu Oct 29, 5:00 PM CT)

- Confirm the track (aimed at Rho fintech).
- README sections the checklist requires; see `docs/reference/hackathon.md`.
- Loom video, 2–5 minutes.
- 150–300 word write-up.
- Make the repo public, after checking it holds no personal details, raw staging data or
  credentials.
