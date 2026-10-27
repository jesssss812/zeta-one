# Roadmap

What is not done, as of 2026-10-27. Remove a line when it is done.

## Before implementation

- Find out what Jev is, and whether it is available, before designing the classifier around it.
- Plan the implementation: language and stack, the mandate format, the identity mechanism, the risk
  signals the data supports, and the narrowest payment action to support first.
- Write the labelled evaluation scenarios before building the engine.

## Build (P0, P1)

- Local Rho stand-in with live and snapshot backends (decision 0002).
- Gateway: identity check, mandate check, risk scoring, allow/challenge/block, simulated execution.
- Evidence record for every decision.
- Evaluation run across the four comparisons in `docs/strategy/evaluation.md`.
- A UI that shows a decision and its evidence.

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
