# Evaluation report

Generated 2026-10-27 with the `replay` backend.

Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and authorization (B, C) must score 100% and would inflate it.

> **Plumbing run.** The replay backend replays recorded fixtures for the five demo cases only; nothing here measures the real engine.

## Run

- Models that ran: illustrative
- Prices used: `{}`
- Set hashes:
  - deterministic: `9baf38d4d3a503ed`
  - dev: `9d15ddd937b02c14`
- Cases by category: deterministic: {'B': 13, 'C': 7, 'D': 1, 'E': 2}; dev: {'A': 1, 'D': 1, 'E': 1}

## Deterministic cases

- always_allow, B: 8% (1/13, 1%–33%), not run 0
- always_allow, C: 0% (0/7, 0%–35%), not run 0
- always_allow, D: 0% (0/1, 0%–79%), not run 0
- always_allow, E: 0% (0/2, 0%–66%), not run 0
- always_allow, risk (A, D, E, F): 0% (0/3, 0%–56%), not run 0
- always_challenge, B: 8% (1/13, 1%–33%), not run 0
- always_challenge, C: 0% (0/7, 0%–35%), not run 0
- always_challenge, D: 100% (1/1, 21%–100%), not run 0
- always_challenge, E: 0% (0/2, 0%–66%), not run 0
- always_challenge, risk (A, D, E, F): 33% (1/3, 6%–79%), not run 0
- rules, B: 100% (1/1, 21%–100%), not run 12
- rules, C: 100% (1/1, 21%–100%), not run 6
- rules, D: –, not run 1
- rules, E: –, not run 2
- rules, risk (A, D, E, F): –, not run 3
- engineered, B: 100% (1/1, 21%–100%), not run 12
- engineered, C: 100% (1/1, 21%–100%), not run 6
- engineered, D: –, not run 1
- engineered, E: –, not run 2
- engineered, risk (A, D, E, F): –, not run 3
- strong, B: 100% (1/1, 21%–100%), not run 12
- strong, C: 100% (1/1, 21%–100%), not run 6
- strong, D: –, not run 1
- strong, E: –, not run 2
- strong, risk (A, D, E, F): –, not run 3

## Risk sets side by side (categories A, D, E, F)

| Configuration | Set | Accuracy | With acceptable | Detection | Legit challenged | Legit blocked |
| --- | --- | --- | --- | --- | --- | --- |
| always_allow | dev | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 0% (0/2, 0%–66%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) |
| always_challenge | dev | 33% (1/3, 6%–79%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 100% (1/1, 21%–100%) | 0% (0/1, 0%–79%) |
| rules | dev | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) |
| engineered | dev | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) |
| strong | dev | 67% (2/3, 21%–94%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 100% (1/1, 21%–100%) | 0% (0/1, 0%–79%) |

A drop from dev to test or hard is overfitting to the generator or the tuning, and is reported as found.

## Per category

### always_allow on deterministic

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 13 | 8% (1/13, 1%–33%) | 8% (1/13, 1%–33%) | 0% (0/11, 0%–26%) | 0 / 0 | – | – |
| C | 7 | 0% (0/7, 0%–35%) | 0% (0/7, 0%–35%) | 0% (0/7, 0%–35%) | 0 / 0 | – | – |
| D | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 0 / 0 | – | – |
| E | 2 | 0% (0/2, 0%–66%) | 0% (0/2, 0%–66%) | 0% (0/2, 0%–66%) | 0 / 0 | – | – |
| risk (A, D, E, F) | 3 | 0% (0/3, 0%–56%) | 0% (0/3, 0%–56%) | 0% (0/2, 0%–66%) | 0 / 0 | – | – |

### always_allow on dev

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | – | – |
| D | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0 / 0 | – | – |
| E | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | 0 / 0 | – | – |
| risk (A, D, E, F) | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 0% (0/2, 0%–66%) | 0 / 0 | – | – |

### always_challenge on deterministic

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 13 | 8% (1/13, 1%–33%) | 8% (1/13, 1%–33%) | 100% (11/11, 74%–100%) | 0 / 0 | – | – |
| C | 7 | 0% (0/7, 0%–35%) | 0% (0/7, 0%–35%) | 100% (7/7, 65%–100%) | 0 / 0 | – | – |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | – | – |
| E | 2 | 0% (0/2, 0%–66%) | 100% (2/2, 34%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | – | – |
| risk (A, D, E, F) | 3 | 33% (1/3, 6%–79%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | – | – |

### always_challenge on dev

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 0 / 0 | – | – |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | – | – |
| E | 1 | 0% (0/1, 0%–79%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | – | – |
| risk (A, D, E, F) | 3 | 33% (1/3, 6%–79%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 0 / 0 | – | – |

### rules on deterministic

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| C | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| D | 0 | – | – | – | 0 / 0 | – | – |
| E | 0 | – | – | – | 0 / 0 | – | – |
| risk (A, D, E, F) | 0 | – | – | – | 0 / 0 | – | – |

### rules on dev

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | 0.0000 | 0 / 0 |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| E | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| risk (A, D, E, F) | 3 | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | 0.0000 | 0 / 0 |

### engineered on deterministic

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| C | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| D | 0 | – | – | – | 0 / 0 | – | – |
| E | 0 | – | – | – | 0 / 0 | – | – |
| risk (A, D, E, F) | 0 | – | – | – | 0 / 0 | – | – |

### engineered on dev

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0 / 0 | 0.0000 | 0 / 0 |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| E | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| risk (A, D, E, F) | 3 | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | 0.0000 | 0 / 0 |

### strong on deterministic

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| C | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| D | 0 | – | – | – | 0 / 0 | – | – |
| E | 0 | – | – | – | 0 / 0 | – | – |
| risk (A, D, E, F) | 0 | – | – | – | 0 / 0 | – | – |

### strong on dev

| Category | n | Accuracy | With acceptable | Detection | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 0 / 0 | 0.0000 | 0 / 0 |
| D | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| E | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 0 / 0 |
| risk (A, D, E, F) | 3 | 67% (2/3, 21%–94%) | 67% (2/3, 21%–94%) | 100% (2/2, 34%–100%) | 0 / 0 | 0.0000 | 0 / 0 |

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
- **always_allow vs engineered on dev**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 0, only first 0, only second 1, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **always_allow vs strong on dev**: pooled risk: only first right 1, only second right 2, exact p = 1.000
  - A: both 0, only first 1, only second 0, neither 0
  - D: both 0, only first 0, only second 1, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **always_challenge vs rules on dev**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **always_challenge vs engineered on dev**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **always_challenge vs strong on dev**: pooled risk: only first right 0, only second right 1, exact p = 1.000
  - A: both 0, only first 0, only second 0, neither 1
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 0, only first 0, only second 1, neither 0
- **rules vs engineered on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 1, only first 0, only second 0, neither 0
- **rules vs strong on dev**: pooled risk: only first right 1, only second right 0, exact p = 1.000
  - A: both 0, only first 1, only second 0, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 1, only first 0, only second 0, neither 0
- **engineered vs strong on dev**: pooled risk: only first right 1, only second right 0, exact p = 1.000
  - A: both 0, only first 1, only second 0, neither 0
  - D: both 1, only first 0, only second 0, neither 0
  - E: both 1, only first 0, only second 0, neither 0

## Failures by first stage that went wrong

Automatic first guess from the evidence record unless the owner tagged the case.

- rules on dev: none
- engineered on dev: none
- strong on dev: model 1

## Label agreement

Not yet measured.

## Not run

- rules on deterministic: 21
- engineered on deterministic: 21
- strong on deterministic: 21

## Cases marked undetectable

Kept few and counted apart from accuracy: what is observable depends on which features exist today.

- none

## Limitations

- The data is synthetic; no rate here is a production rate, and the sets say nothing about how often each case occurs.
- The generator's dimensions resemble tier 0's features, so the rules look better on dev and test than they would on cases the generator did not write; the hard set is the check on that.
- Claude Haiku 5.5 wrote the case wording, Claude Sonnet 5.5 labelled, and Claude Opus 5.5 is the strong tier: all three are from one family.
- With about 30 cases in a class a rate near 85% has a 95% interval of roughly ±12 points: enough to tell configurations apart in aggregate, not to rank them within a category.
- Latency is a single run on one machine including network time; no responses are cached, though the fixed system prompt is prompt-cached.
- Payments are simulated.
