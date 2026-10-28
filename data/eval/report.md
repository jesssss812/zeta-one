# Evaluation report

Generated 2026-10-28 (UTC) from results made with the `real` backend.

Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and authorization (B, C) must score 100% and would inflate it.

> **dev holds only the hand-built demo cases** the rules were written around; no generated dev cases are labelled yet, so its rates say nothing about cases the rules weren't built for.

## Run

- Models that ran: none
- Prices used: `{}`
- Engine version: `e853f63`
- Policy version: `2026-10-28.4`
- Seed version: `3574ce8f0cef1de72c159f3b2c98128410721da8c4016114bf90928e6958909c`
- Generator seeds: dev: [7]; test: [11]
- test combinations also in dev: 15 (the routine class has too few to keep apart; only wording and vendor differ)
- Set hashes the results ran against:
  - deterministic: `095c6492168c4f11` (not frozen)
  - dev: `d015f457ed5d92f7` (not frozen)
- Cases by category: deterministic: {'B': 13, 'C': 7, 'D': 1, 'E': 2}; dev: {'A': 1, 'D': 1, 'E': 1}

## Deterministic cases

Every case must pass; counts, not statistics. A case that repeats its request passes only if every send got the same decision.

- always_allow, B: 1/13 pass (1/13 exact), unstable 0, not run 0
- always_allow, C: 0/7 pass (0/7 exact), unstable 0, not run 0
- always_allow, D: 0/1 pass (0/1 exact), unstable 0, not run 0
- always_allow, E: 0/2 pass (0/2 exact), unstable 0, not run 0
- always_challenge, B: 2/13 pass (1/13 exact), unstable 0, not run 0
- always_challenge, C: 0/7 pass (0/7 exact), unstable 0, not run 0
- always_challenge, D: 1/1 pass (1/1 exact), unstable 0, not run 0
- always_challenge, E: 2/2 pass (0/2 exact), unstable 0, not run 0
- rules, B: 13/13 pass (12/13 exact), unstable 0, not run 0
- rules, C: 7/7 pass (7/7 exact), unstable 0, not run 0
- rules, D: – pass (– exact), unstable 0, not run 1
- rules, E: 1/1 pass (0/1 exact), unstable 0, not run 1

## Risk sets side by side (categories A, D, E, F)

| Configuration | Set | Accuracy | With acceptable | Detection | Legit challenged | Legit blocked |
| --- | --- | --- | --- | --- | --- | --- |
| always_allow | dev | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 0% (0/2, 0%–66%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) |
| always_challenge | dev | 33% (1/3, 6%–79%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 100% (1/1, 21%–100%) | 0% (0/1, 0%–79%) |
| rules | dev | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) |

A drop from dev to test or hard is overfitting to the generator or the tuning, and is reported as found.

## Cost

How many decisions reached any model, and what they cost. Tier 0 is free; dollars appear only for measured, priced model calls (a model's own price list, recorded in each decision).

| Configuration | Set | Reached a model | $ per 1,000 decisions | $ per fraud caught | Notes |
| --- | --- | --- | --- | --- | --- |
| rules | dev | 0% (0/3, 0%–56%) | 0.00 | 0.0000 |  |

## Per category

### always_allow on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | – | not measured |
| D | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 0 / 0 | – | not measured |
| E | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 0% (0/2, 0%–66%) | 0% (0/1, 0%–79%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 1 | 0 | 0 |
| challenge | 1 | 0 | 0 |
| block | 1 | 0 | 0 |

### always_challenge on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 100% (1/1, 21%–100%) | 0 / 0 | – | not measured |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | – | not measured |
| E | 1 | 0% (0/1, 0%–79%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 3 | 33% (1/3, 6%–79%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 0 | 1 | 0 |
| challenge | 0 | 1 | 0 |
| block | 0 | 1 | 0 |

### rules on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 14 / 14 |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | 0.0000 | 14 / 14 |
| E | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | 0.0000 | 18 / 18 |
| risk (A, D, E, F) | 3 | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 14 / 18 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 1 | 0 | 0 |
| challenge | 0 | 1 | 0 |
| block | 0 | 0 | 1 |

## Discordant cases

Cases where one configuration is right and the other wrong. A McNemar p-value is given only pooled across the risk categories.

- **always_allow vs always_challenge on dev**: pooled risk: only first right 1, only second right 1, exact p = 1.000
  - A: both 0, only first 1, only second 0, neither 0
  - D: both 0, only first 0, only second 1, neither 0
  - E: both 0, only first 0, only second 0, neither 1
- **always_allow vs rules on dev**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 0, only first 0, only second 1, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **always_challenge vs rules on dev**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 0, only first 0, only second 1, neither 0

## Failures by first stage that went wrong

Automatic first guess from the evidence record unless the owner tagged the case.

- rules on dev: none

## Label agreement

Not yet measured.

## Not run

- rules on deterministic: 2

## Cases marked undetectable

Kept few and left out of accuracy and detection: what is observable depends on which features exist today, so each is listed here rather than excused.

- none

## Limitations

- The data is synthetic; no rate here is a production rate, and the sets say nothing about how often each case occurs.
- The generator's dimensions resemble tier 0's features, so the rules look better on dev and test than they would on cases the generator did not write; the hard set is the check on that.
- The plan has Claude Haiku 5.5 write the case wording, Claude Sonnet 5.5 label, and Claude Opus 5.5 serve as the strong tier: all three from one family. The Run section lists the models that actually ran.
- With about 30 cases in a class a rate near 85% has a 95% interval of roughly ±12 points: enough to tell configurations apart in aggregate, not to rank them within a category.
- Latency, where shown, is a single run on one machine, including network time when a model ran. A repeated proposal reuses its earlier risk result (decision 0010), and the strong tier's fixed system prompt is prompt-cached; nothing else is cached.
- Payments are simulated.
