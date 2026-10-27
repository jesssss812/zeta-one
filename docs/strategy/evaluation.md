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
2. rules plus a fast, cheap classifier (Jev; Claude Haiku stands in until Jev runs)
3. a stronger LLM on every request
4. selective escalation: the cheap classifier first, the stronger model only when needed

The report names the models and prices that actually ran.

## Metrics

Per configuration: accuracy against the expected decision (and counting also-acceptable
decisions), accuracy on known authorization violations and identity failures (must be 100%),
detection (share of suspicious and adversarial cases not allowed), challenge rate on legitimate
cases, cost per evaluated action from reported token usage, and p50/p95 latency.

**Friction score** (once challenge types exist, decision 0008): each rung carries a weight (allow 0,
notify 0.1, confirm 1, renew authorization 2, verify payee 3); the score is the mean weight over
legitimate cases, reported with the share of legitimate actions that saw no prompt. Detection and
friction together are the critical-damping trade-off; a configuration that lowers one by raising
the other hasn't improved.

The judges score "performance: did they optimize for speed or scale?"
([../reference/hackathon.md](../reference/hackathon.md)), so cost and latency are worth reporting
next to accuracy.
