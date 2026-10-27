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
2. rules, then the strong model only on engineered escalation (decision 0009)
3. rules, then Jev, then the strong model only when Jev's probability is low
4. the strong model on every request
5. optionally: rules, then an open-weight model of Opus/Sonnet class, then the strong model

The report names the models and prices that actually ran. The language-model tiers see only the
proposal and its context, never a case's category, setup or name.

## Metrics

Reported **per category**, never as one headline number: the identity and authorization categories
are deterministic and must score 100%, so an overall accuracy would be inflated by them. Per
configuration and category: accuracy against the expected decision, and separately accuracy
counting also-acceptable decisions; detection (share of suspicious and adversarial cases not
allowed); challenge rate on legitimate cases; cost per evaluated action from reported token usage;
p50/p95 latency. Every rate states its n (a category of 10 moves 10 points per case). Latency is a
single run on one machine including network time, and is labelled so; model calls are never cached
across runs.

**Calibration of Jev** is measured, not assumed: its `risk_level` probability against the expected
decision across all cases, as a reliability table with the sample size, so the escalation threshold
can be judged.

**Friction score** (once challenge types exist, decision 0008): each rung carries a weight (allow 0,
notify 0.1, confirm 1, renew authorization 2, verify payee 3; chosen, not derived); the score is the
mean weight over legitimate cases, reported with the share of legitimate actions that saw no prompt. Detection and
friction together are the critical-damping trade-off; a configuration that lowers one by raising
the other hasn't improved.

The judges score "performance: did they optimize for speed or scale?"
([../reference/hackathon.md](../reference/hackathon.md)), so cost and latency are worth reporting
next to accuracy.
