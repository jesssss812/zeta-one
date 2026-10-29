# Evaluation report

Generated 2026-10-29 (UTC) from results made with the `real` backend.

Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and authorization (B, C) must score 100% and would inflate it.

## Run

- Models that ran: claude-opus-5-5, qwen/qwen3-235b-a22b-2507, typesafe/jev-1.14
- Prices used: `{"claude-opus-5-5": {"cache_read_multiplier": 0.1, "cache_write_multiplier": 1.25, "input_per_mtok": 4.0, "output_per_mtok": 20.0}, "typesafe/jev-1.14": {"cache_read_multiplier": 0.1, "cache_write_multiplier": 1.25, "input_per_mtok": 0.042, "output_per_mtok": 0.0}}`
- Engine version: `7ba6857`, `8be8e8e`, `d40bade`, `e4a4e41`, `e853f63`
- Policy version: `2026-10-28.4`
- Seed version: `3574ce8f0cef1de72c159f3b2c98128410721da8c4016114bf90928e6958909c`
- Generator seeds: dev: [7]; test: [11]
- test combinations also in dev: 15 (the routine class has too few to keep apart; only wording and vendor differ)
- Set hashes the results ran against:
  - deterministic: `095c6492168c4f11` (not frozen)
  - dev: `a4fbf0d6e02ece3e` (not frozen)
- Cases by category: deterministic: {'B': 13, 'C': 7, 'D': 1, 'E': 2}; dev: {'A': 16, 'D': 15, 'E': 13, 'F': 7}

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
| always_allow | dev | 35% (18/51, 24%–49%) | 37% (19/51, 25%–51%) | 0% (0/22, 0%–15%) | 0% (0/29, 0%–12%) | 0% (0/29, 0%–12%) |
| always_challenge | dev | 41% (21/51, 29%–55%) | 71% (36/51, 57%–81%) | 100% (22/22, 85%–100%) | 100% (29/29, 88%–100%) | 0% (0/29, 0%–12%) |
| rules | dev | 75% (38/51, 61%–84%) | 84% (43/51, 72%–92%) | 100% (22/22, 85%–100%) | 72% (21/29, 54%–85%) | 0% (0/29, 0%–12%) |
| engineered | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |
| jev | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |
| open_weight | dev | 69% (35/51, 55%–80%) | 73% (37/51, 59%–83%) | 100% (22/22, 85%–100%) | 41% (12/29, 26%–59%) | 31% (9/29, 17%–49%) |
| strong | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |

A drop from dev to test or hard is overfitting to the generator or the tuning, and is reported as found.

## Cost

How many decisions reached any model, and what they cost. Tier 0 is free; dollars appear only for measured, priced model calls (a model's own price list, recorded in each decision).

| Configuration | Set | Reached a model | $ per 1,000 decisions | $ per fraud caught | Notes |
| --- | --- | --- | --- | --- | --- |
| rules | dev | 0% (0/51, 0%–7%) | 0.00 | 0.0000 |  |
| engineered | dev | 57% (29/51, 43%–69%) | 15.53 | 0.0360 |  |
| jev | dev | 84% (43/51, 72%–92%) | 12.14 | 0.0281 |  |
| open_weight | dev | 84% (43/51, 72%–92%) | 0.00 | 0.0000 | unpriced: qwen/qwen3-235b-a22b-2507 |
| strong | dev | 100% (51/51, 93%–100%) | 23.96 | 0.0556 |  |

## Per category

### always_allow on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 0 / 0 | – | not measured |
| D | 15 | 0% (0/15, 0%–20%) | 0% (0/15, 0%–20%) | 0% (0/10, 0%–28%) | 0% (0/5, 0%–43%) | 0 / 0 | – | not measured |
| E | 13 | 0% (0/13, 0%–23%) | 0% (0/13, 0%–23%) | 0% (0/12, 0%–24%) | 0% (0/1, 0%–79%) | 0 / 0 | – | not measured |
| F | 7 | 43% (3/7, 16%–75%) | 57% (4/7, 25%–84%) | – | 0% (0/7, 0%–35%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 51 | 35% (18/51, 24%–49%) | 37% (19/51, 25%–51%) | 0% (0/22, 0%–15%) | 0% (0/29, 0%–12%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 21 | 0 | 0 |
| block | 12 | 0 | 0 |

### always_challenge on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 6% (1/16, 1%–28%) | 6% (1/16, 1%–28%) | – | 100% (16/16, 81%–100%) | 0 / 0 | – | not measured |
| D | 15 | 100% (15/15, 80%–100%) | 100% (15/15, 80%–100%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | – | not measured |
| E | 13 | 8% (1/13, 1%–33%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | – | not measured |
| F | 7 | 57% (4/7, 25%–84%) | 100% (7/7, 65%–100%) | – | 100% (7/7, 65%–100%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 51 | 41% (21/51, 29%–55%) | 71% (36/51, 57%–81%) | 100% (22/22, 85%–100%) | 100% (29/29, 88%–100%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 0 | 18 | 0 |
| challenge | 0 | 21 | 0 |
| block | 0 | 12 | 0 |

### rules on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 50% (8/16, 28%–72%) | 50% (8/16, 28%–72%) | – | 56% (9/16, 33%–77%) | 0 / 0 | 0.0000 | 13 / 20 |
| D | 15 | 100% (15/15, 80%–100%) | 100% (15/15, 80%–100%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0000 | 13 / 18 |
| E | 13 | 77% (10/13, 50%–92%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 16 / 23 |
| F | 7 | 71% (5/7, 36%–92%) | 100% (7/7, 65%–100%) | – | 86% (6/7, 49%–97%) | 0 / 0 | 0.0000 | 14 / 21 |
| risk (A, D, E, F) | 51 | 75% (38/51, 61%–84%) | 84% (43/51, 72%–92%) | 100% (22/22, 85%–100%) | 72% (21/29, 54%–85%) | 0 / 0 | 0.0000 | 13 / 21 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 8 | 10 | 0 |
| challenge | 0 | 21 | 0 |
| block | 0 | 3 | 9 |

### engineered on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 9 / 0 | 0.0132 | 5182 / 8739 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0224 | 7540 / 10079 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0105 | 9 / 9383 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 43% (3/7, 16%–75%) | 3 / 0 | 0.0153 | 7118 / 9676 |
| risk (A, D, E, F) | 51 | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 12 / 0 | 0.0155 | 5529 / 9568 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 2 | 18 | 1 |
| block | 0 | 1 | 11 |

### jev on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 9 / 0 | 0.0064 | 211 / 7752 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0192 | 7341 / 9870 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0097 | 327 / 10166 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 43% (3/7, 16%–75%) | 3 / 0 | 0.0147 | 7056 / 8437 |
| risk (A, D, E, F) | 51 | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 12 / 0 | 0.0121 | 371 / 9920 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 2 | 18 | 1 |
| block | 0 | 1 | 11 |

### open_weight on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 50% (8/16, 28%–72%) | 50% (8/16, 28%–72%) | – | 38% (6/16, 18%–61%) | 0 / 0 | 0.0000 | 6878 / 29148 |
| D | 15 | 67% (10/15, 42%–85%) | 67% (10/15, 42%–85%) | 100% (10/10, 72%–100%) | 20% (1/5, 4%–62%) | 0 / 0 | 0.0000 | 22090 / 34951 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 9894 / 51571 |
| F | 7 | 71% (5/7, 36%–92%) | 86% (6/7, 49%–97%) | – | 71% (5/7, 36%–92%) | 0 / 0 | 0.0000 | 10827 / 26863 |
| risk (A, D, E, F) | 51 | 69% (35/51, 55%–80%) | 73% (37/51, 59%–83%) | 100% (22/22, 85%–100%) | 41% (12/29, 26%–59%) | 0 / 0 | 0.0000 | 10489 / 40768 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 8 | 6 | 4 |
| challenge | 0 | 15 | 6 |
| block | 0 | 0 | 12 |

### strong on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 9 / 0 | 0.0210 | 5026 / 8218 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0244 | 6655 / 9556 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0283 | 8407 / 9565 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 43% (3/7, 16%–75%) | 3 / 0 | 0.0217 | 6664 / 9477 |
| risk (A, D, E, F) | 51 | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 12 / 0 | 0.0240 | 6360 / 9514 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 2 | 18 | 1 |
| block | 0 | 1 | 11 |

## Discordant cases

Cases where one configuration is right and the other wrong. A McNemar p-value is given only pooled across the risk categories.

- **always_allow vs always_challenge on dev**: pooled risk: only first right 18, only second right 21, exact p = 0.749
  - A: both 0, only first 15, only second 1, neither 0
  - D: both 0, only first 0, only second 15, neither 0
  - E: both 0, only first 0, only second 1, neither 12
  - F: both 0, only first 3, only second 4, neither 0
- **always_allow vs rules on dev**: pooled risk: only first right 10, only second right 30, exact p = 0.002
  - A: both 7, only first 8, only second 1, neither 0
  - D: both 0, only first 0, only second 15, neither 0
  - E: both 0, only first 0, only second 10, neither 3
  - F: both 1, only first 2, only second 4, neither 0
- **always_allow vs engineered on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_allow vs jev on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_allow vs open_weight on dev**: pooled risk: only first right 10, only second right 27, exact p = 0.008
  - A: both 7, only first 8, only second 1, neither 0
  - D: both 0, only first 0, only second 10, neither 5
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 1, only first 2, only second 4, neither 0
- **always_allow vs strong on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_challenge vs rules on dev**: pooled risk: only first right 0, only second right 17, exact p = 0.000
  - A: both 1, only first 0, only second 7, neither 8
  - D: both 15, only first 0, only second 0, neither 0
  - E: both 1, only first 0, only second 9, neither 3
  - F: both 4, only first 0, only second 1, neither 2
- **always_challenge vs engineered on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **always_challenge vs jev on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **always_challenge vs open_weight on dev**: pooled risk: only first right 6, only second right 20, exact p = 0.009
  - A: both 1, only first 0, only second 7, neither 8
  - D: both 10, only first 5, only second 0, neither 0
  - E: both 0, only first 1, only second 12, neither 0
  - F: both 4, only first 0, only second 1, neither 2
- **always_challenge vs strong on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **rules vs engineered on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **rules vs jev on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **rules vs open_weight on dev**: pooled risk: only first right 6, only second right 3, exact p = 0.508
  - A: both 8, only first 0, only second 0, neither 8
  - D: both 10, only first 5, only second 0, neither 0
  - E: both 9, only first 1, only second 3, neither 0
  - F: both 5, only first 0, only second 0, neither 2
- **rules vs strong on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **engineered vs jev on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **engineered vs open_weight on dev**: pooled risk: only first right 15, only second right 3, exact p = 0.008
  - A: both 7, only first 8, only second 1, neither 0
  - D: both 10, only first 4, only second 0, neither 1
  - E: both 11, only first 1, only second 1, neither 0
  - F: both 4, only first 2, only second 1, neither 0
- **engineered vs strong on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **jev vs open_weight on dev**: pooled risk: only first right 15, only second right 3, exact p = 0.008
  - A: both 7, only first 8, only second 1, neither 0
  - D: both 10, only first 4, only second 0, neither 1
  - E: both 11, only first 1, only second 1, neither 0
  - F: both 4, only first 2, only second 1, neither 0
- **jev vs strong on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **open_weight vs strong on dev**: pooled risk: only first right 3, only second right 15, exact p = 0.008
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 10, only first 0, only second 4, neither 1
  - E: both 11, only first 1, only second 1, neither 0
  - F: both 4, only first 1, only second 2, neither 0

## Failures by first stage that went wrong

Automatic first guess from the evidence record unless the owner tagged the case.

- rules on dev: feature 8
- engineered on dev: model 2
- jev on dev: model 2
- open_weight on dev: feature 14
- strong on dev: model 2

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
