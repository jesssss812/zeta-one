# Evaluation: how Zeta One is measured

Written 2026-10-27, before any code. A change to how something is measured updates this doc in the
same change.

## Principle

Show more than a polished happy path. A credible evaluation runs a labelled set of proposed agent
actions through the system and reports where it is right, where it is wrong and what it costs. Use
synthetic examples openly, and never claim production fraud-detection accuracy without real labelled
data.

## Case categories

Every scenario set covers:

- known authorization violations
- legitimate, authorized payments
- authorized but suspicious payments
- unknown or unverifiable agents
- ambiguous cases that need human verification
- manipulated or adversarial inputs, such as prompt injection in invoices

Each case carries its expected decision (allow, challenge or block) and where its data came from
(Rho staging snapshot, or synthetic and how it was generated).

## What to check

- Hard permissions are enforced correctly, every time.
- Legitimate actions are not challenged unnecessarily. Unnecessary challenges are a cost, as missed
  fraud is: this is the critical-damping trade-off.
- Meaningful risk signals are detected.
- Explanations are actionable.
- Evidence keeps its provenance.
- Latency and cost stay acceptable.

## Comparisons

Run the same cases through:

1. deterministic rules only
2. rules plus a fast, cheap classifier
3. a stronger LLM on every request
4. selective escalation: the cheap classifier first, the stronger model only when needed

## Metrics

Detection recall, false-positive rate, challenge or review rate, accuracy on known authorization
violations, performance on adversarial cases, cost per evaluated action, and latency.

The judges score "performance: did they optimize for speed or scale?"
([../reference/hackathon.md](../reference/hackathon.md)), so cost and latency are worth reporting
next to accuracy.
