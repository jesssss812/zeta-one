# Evaluation report

Generated 2026-10-29 (UTC) from results made with the `real` backend.

Rates are shown as `rate (k/n, 95% Wilson interval)`. There is no overall accuracy: identity and authorization (B, C) must score 100% and would inflate it.

## Run

- Models that ran: claude-opus-5-5, qwen3.6-27b, typesafe/jev-1.14
- Prices used: `{"claude-opus-5-5": {"cache_read_multiplier": 0.1, "cache_write_multiplier": 1.25, "input_per_mtok": 4.0, "output_per_mtok": 20.0}, "qwen3.6-27b": {"charged_for": "model latency per call", "gpu_usd_per_hour": 0.59}, "typesafe/jev-1.14": {"cache_read_multiplier": 0.1, "cache_write_multiplier": 1.25, "input_per_mtok": 0.042, "output_per_mtok": 0.0}}`
- Engine version: `23c489e`, `469ff95`, `702aa78`, `7ba6857`, `9b63388`, `b850a2f`, `dd7f436`, `fe349b5`
- Policy version: `2026-10-28.4`, `2026-10-28.5`
- Seed version: `15c5c875071bd93485ba9b3a8afce94db723925924e4ab2207e43650d442d215`, `3574ce8f0cef1de72c159f3b2c98128410721da8c4016114bf90928e6958909c`
- Generator seeds: dev: [7]; test: [11]
- test combinations also in dev: 15 (the routine class has too few to keep apart; only wording and vendor differ)
- Set hashes the results ran against:
  - deterministic: `095c6492168c4f11` (not frozen)
  - dev: `a4fbf0d6e02ece3e` (not frozen)
  - test: `d77ad27c9fd868f6` (matches its frozen hash)
  - hard: `8a4803a7803f6e07` (matches its frozen hash)
- Cases by category: deterministic: {'B': 13, 'C': 7, 'D': 1, 'E': 2}; dev: {'A': 16, 'D': 15, 'E': 13, 'F': 7}; test: {'A': 35, 'D': 35, 'E': 30}; hard: {'A': 1, 'D': 8, 'E': 3, 'F': 2}

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
- engineered, B: 11/13 pass (11/13 exact), unstable 0, not run 0
- engineered, C: 7/7 pass (7/7 exact), unstable 0, not run 0
- engineered, D: 1/1 pass (1/1 exact), unstable 0, not run 0
- engineered, E: 2/2 pass (1/2 exact), unstable 0, not run 0
- jev, B: 12/13 pass (11/13 exact), unstable 0, not run 0
- jev, C: 7/7 pass (7/7 exact), unstable 0, not run 0
- jev, D: 1/1 pass (1/1 exact), unstable 0, not run 0
- jev, E: 2/2 pass (1/2 exact), unstable 0, not run 0
- open_weight, B: 10/12 pass (10/12 exact), unstable 0, not run 1
- open_weight, C: 6/6 pass (6/6 exact), unstable 0, not run 1
- open_weight, D: 1/1 pass (1/1 exact), unstable 0, not run 0
- open_weight, E: 2/2 pass (1/2 exact), unstable 0, not run 0
- strong, B: 12/13 pass (11/13 exact), unstable 0, not run 0
- strong, C: 7/7 pass (7/7 exact), unstable 0, not run 0
- strong, D: 1/1 pass (1/1 exact), unstable 0, not run 0
- strong, E: 2/2 pass (2/2 exact), unstable 0, not run 0

## Risk sets side by side (categories A, D, E, F)

| Configuration | Set | Accuracy | With acceptable | Detection | Legit challenged | Legit blocked |
| --- | --- | --- | --- | --- | --- | --- |
| always_allow | dev | 35% (18/51, 24%–49%) | 37% (19/51, 25%–51%) | 0% (0/22, 0%–15%) | 0% (0/29, 0%–12%) | 0% (0/29, 0%–12%) |
| always_allow | test | 32% (32/100, 24%–42%) | 41% (41/100, 32%–51%) | 0% (0/49, 0%–7%) | 0% (0/51, 0%–7%) | 0% (0/51, 0%–7%) |
| always_allow | hard | 42% (5/12, 19%–68%) | 42% (5/12, 19%–68%) | 0% (0/6, 0%–39%) | 0% (0/6, 0%–39%) | 0% (0/6, 0%–39%) |
| always_challenge | dev | 41% (21/51, 29%–55%) | 71% (36/51, 57%–81%) | 100% (22/22, 85%–100%) | 100% (29/29, 88%–100%) | 0% (0/29, 0%–12%) |
| always_challenge | test | 45% (45/100, 36%–55%) | 74% (74/100, 65%–82%) | 100% (49/49, 93%–100%) | 100% (51/51, 93%–100%) | 0% (0/51, 0%–7%) |
| always_challenge | hard | 42% (5/12, 19%–68%) | 58% (7/12, 32%–81%) | 100% (6/6, 61%–100%) | 100% (6/6, 61%–100%) | 0% (0/6, 0%–39%) |
| rules | dev | 75% (38/51, 61%–84%) | 84% (43/51, 72%–92%) | 100% (22/22, 85%–100%) | 72% (21/29, 54%–85%) | 0% (0/29, 0%–12%) |
| rules | test | 65% (65/100, 55%–74%) | 79% (79/100, 70%–86%) | 100% (49/49, 93%–100%) | 76% (39/51, 63%–86%) | 0% (0/51, 0%–7%) |
| rules | hard | 50% (6/12, 25%–75%) | 50% (6/12, 25%–75%) | 67% (4/6, 30%–90%) | 83% (5/6, 44%–97%) | 0% (0/6, 0%–39%) |
| engineered | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |
| engineered | test | 84% (84/100, 76%–90%) | 91% (91/100, 84%–95%) | 98% (48/49, 89%–100%) | 31% (16/51, 20%–45%) | 0% (0/51, 0%–7%) |
| engineered | hard | 58% (7/12, 32%–81%) | 67% (8/12, 39%–86%) | 67% (4/6, 30%–90%) | 17% (1/6, 3%–56%) | 0% (0/6, 0%–39%) |
| jev | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |
| jev | test | 84% (84/100, 76%–90%) | 90% (90/100, 83%–94%) | 96% (47/49, 86%–99%) | 27% (14/51, 17%–41%) | 0% (0/51, 0%–7%) |
| jev | hard | 50% (6/12, 25%–75%) | 58% (7/12, 32%–81%) | 67% (4/6, 30%–90%) | 17% (1/6, 3%–56%) | 0% (0/6, 0%–39%) |
| open_weight | dev | 94% (48/51, 84%–98%) | 98% (50/51, 90%–100%) | 100% (22/22, 85%–100%) | 41% (12/29, 26%–59%) | 0% (0/29, 0%–12%) |
| open_weight | test | 90% (90/100, 83%–94%) | 94% (94/100, 88%–97%) | 100% (49/49, 93%–100%) | 37% (19/51, 25%–51%) | 0% (0/51, 0%–7%) |
| open_weight | hard | 50% (6/12, 25%–75%) | 58% (7/12, 32%–81%) | 67% (4/6, 30%–90%) | 50% (3/6, 19%–81%) | 0% (0/6, 0%–39%) |
| strong | dev | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 0% (0/29, 0%–12%) |
| strong | test | 83% (83/100, 74%–89%) | 90% (90/100, 83%–94%) | 96% (47/49, 86%–99%) | 27% (14/51, 17%–41%) | 0% (0/51, 0%–7%) |
| strong | hard | 75% (9/12, 47%–91%) | 83% (10/12, 55%–95%) | 100% (6/6, 61%–100%) | 17% (1/6, 3%–56%) | 0% (0/6, 0%–39%) |

A drop from dev to test or hard is overfitting to the generator or the tuning, and is reported as found.

## Cost

How many decisions reached any model, and what they cost. Tier 0 is free; dollars appear only for measured, priced model calls (a model's own price list, recorded in each decision).

| Configuration | Set | Reached a model | $ per 1,000 decisions | $ per fraud caught | Notes |
| --- | --- | --- | --- | --- | --- |
| rules | dev | 0% (0/51, 0%–7%) | 0.00 | 0.0000 |  |
| rules | test | 0% (0/100, 0%–4%) | 0.00 | 0.0000 |  |
| rules | hard | 0% (0/14, 0%–22%) | 0.00 | 0.0000 |  |
| engineered | dev | 57% (29/51, 43%–69%) | 15.26 | 0.0354 |  |
| engineered | test | 59% (59/100, 49%–68%) | 15.15 | 0.0316 |  |
| engineered | hard | 64% (9/14, 39%–84%) | 15.50 | 0.0542 |  |
| jev | dev | 84% (43/51, 72%–92%) | 12.04 | 0.0279 |  |
| jev | test | 88% (88/100, 80%–93%) | 12.00 | 0.0255 |  |
| jev | hard | 64% (9/14, 39%–84%) | 17.30 | 0.0605 |  |
| open_weight | dev | 57% (29/51, 43%–69%) | 1.76 | 0.0041 |  |
| open_weight | test | 59% (59/100, 49%–68%) | 1.85 | 0.0038 |  |
| open_weight | hard | 64% (9/14, 39%–84%) | 1.97 | 0.0069 |  |
| strong | dev | 100% (51/51, 93%–100%) | 23.96 | 0.0556 |  |
| strong | test | 100% (100/100, 96%–100%) | 23.77 | 0.0506 |  |
| strong | hard | 100% (14/14, 78%–100%) | 23.46 | 0.0547 |  |

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

### always_allow on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 86% (30/35, 71%–94%) | 91% (32/35, 78%–97%) | – | 0% (0/35, 0%–10%) | 0 / 0 | – | not measured |
| D | 35 | 6% (2/35, 2%–19%) | 17% (6/35, 8%–33%) | 0% (0/21, 0%–15%) | 0% (0/14, 0%–22%) | 0 / 0 | – | not measured |
| E | 30 | 0% (0/30, 0%–11%) | 10% (3/30, 3%–26%) | 0% (0/28, 0%–12%) | 0% (0/2, 0%–66%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 100 | 32% (32/100, 24%–42%) | 41% (41/100, 32%–51%) | 0% (0/49, 0%–7%) | 0% (0/51, 0%–7%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 32 | 0 | 0 |
| challenge | 45 | 0 | 0 |
| block | 23 | 0 | 0 |

### always_allow on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | – | not measured |
| D | 8 | 33% (2/6, 10%–70%) | 33% (2/6, 10%–70%) | 0% (0/3, 0%–56%) | 0% (0/3, 0%–56%) | 0 / 0 | – | not measured |
| E | 3 | 0% (0/3, 0%–56%) | 0% (0/3, 0%–56%) | 0% (0/3, 0%–56%) | – | 0 / 0 | – | not measured |
| F | 2 | 100% (2/2, 34%–100%) | 100% (2/2, 34%–100%) | – | 0% (0/2, 0%–66%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 14 | 42% (5/12, 19%–68%) | 42% (5/12, 19%–68%) | 0% (0/6, 0%–39%) | 0% (0/6, 0%–39%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 5 | 0 | 0 |
| challenge | 5 | 0 | 0 |
| block | 2 | 0 | 0 |

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

### always_challenge on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 14% (5/35, 6%–29%) | 31% (11/35, 19%–48%) | – | 100% (35/35, 90%–100%) | 0 / 0 | – | not measured |
| D | 35 | 94% (33/35, 81%–98%) | 97% (34/35, 85%–99%) | 100% (21/21, 85%–100%) | 100% (14/14, 78%–100%) | 0 / 0 | – | not measured |
| E | 30 | 23% (7/30, 12%–41%) | 97% (29/30, 83%–99%) | 100% (28/28, 88%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 100 | 45% (45/100, 36%–55%) | 74% (74/100, 65%–82%) | 100% (49/49, 93%–100%) | 100% (51/51, 93%–100%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 0 | 32 | 0 |
| challenge | 0 | 45 | 0 |
| block | 0 | 23 | 0 |

### always_challenge on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 0% (0/1, 0%–79%) | 0% (0/1, 0%–79%) | – | 100% (1/1, 21%–100%) | 0 / 0 | – | not measured |
| D | 8 | 67% (4/6, 30%–90%) | 67% (4/6, 30%–90%) | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 0 / 0 | – | not measured |
| E | 3 | 33% (1/3, 6%–79%) | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | – | 0 / 0 | – | not measured |
| F | 2 | 0% (0/2, 0%–66%) | 0% (0/2, 0%–66%) | – | 100% (2/2, 34%–100%) | 0 / 0 | – | not measured |
| risk (A, D, E, F) | 14 | 42% (5/12, 19%–68%) | 58% (7/12, 32%–81%) | 100% (6/6, 61%–100%) | 100% (6/6, 61%–100%) | 0 / 0 | – | not measured |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 0 | 5 | 0 |
| challenge | 0 | 5 | 0 |
| block | 0 | 2 | 0 |

### rules on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 50% (8/16, 28%–72%) | 50% (8/16, 28%–72%) | – | 56% (9/16, 33%–77%) | 0 / 0 | 0.0000 | 17 / 24 |
| D | 15 | 100% (15/15, 80%–100%) | 100% (15/15, 80%–100%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0000 | 16 / 34 |
| E | 13 | 77% (10/13, 50%–92%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0000 | 25 / 37 |
| F | 7 | 71% (5/7, 36%–92%) | 100% (7/7, 65%–100%) | – | 86% (6/7, 49%–97%) | 0 / 0 | 0.0000 | 20 / 22 |
| risk (A, D, E, F) | 51 | 75% (38/51, 61%–84%) | 84% (43/51, 72%–92%) | 100% (22/22, 85%–100%) | 72% (21/29, 54%–85%) | 0 / 0 | 0.0000 | 19 / 32 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 8 | 10 | 0 |
| challenge | 0 | 21 | 0 |
| block | 0 | 3 | 9 |

### rules on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 37% (13/35, 23%–54%) | 54% (19/35, 38%–70%) | – | 66% (23/35, 49%–79%) | 0 / 0 | 0.0000 | 26 / 41 |
| D | 35 | 94% (33/35, 81%–98%) | 97% (34/35, 85%–99%) | 100% (21/21, 85%–100%) | 100% (14/14, 78%–100%) | 0 / 0 | 0.0000 | 27 / 37 |
| E | 30 | 63% (19/30, 46%–78%) | 87% (26/30, 70%–95%) | 100% (28/28, 88%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | 0.0000 | 36 / 56 |
| risk (A, D, E, F) | 100 | 65% (65/100, 55%–74%) | 79% (79/100, 70%–86%) | 100% (49/49, 93%–100%) | 76% (39/51, 63%–86%) | 0 / 0 | 0.0000 | 28 / 44 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 10 | 22 | 0 |
| challenge | 2 | 39 | 4 |
| block | 0 | 7 | 16 |

### rules on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 7 / 7 |
| D | 8 | 67% (4/6, 30%–90%) | 67% (4/6, 30%–90%) | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 0 / 0 | 0.0000 | 33 / 47 |
| E | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | – | 0 / 0 | 0.0000 | 37 / 48 |
| F | 2 | 0% (0/2, 0%–66%) | 0% (0/2, 0%–66%) | – | 100% (2/2, 34%–100%) | 0 / 0 | 0.0000 | 30 / 38 |
| risk (A, D, E, F) | 14 | 50% (6/12, 25%–75%) | 50% (6/12, 25%–75%) | 67% (4/6, 30%–90%) | 83% (5/6, 44%–97%) | 0 / 0 | 0.0000 | 34 / 48 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 1 | 4 | 0 |
| challenge | 0 | 5 | 0 |
| block | 2 | 0 | 0 |

### engineered on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 9 / 0 | 0.0131 | 5151 / 7506 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0221 | 7004 / 10448 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0102 | 23 / 9260 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 43% (3/7, 16%–75%) | 3 / 0 | 0.0151 | 7408 / 9471 |
| risk (A, D, E, F) | 51 | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 12 / 0 | 0.0153 | 5510 / 9284 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 2 | 18 | 1 |
| block | 0 | 1 | 11 |

### engineered on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 83% (29/35, 67%–92%) | 91% (32/35, 78%–97%) | – | 3% (1/35, 1%–15%) | 22 / 0 | 0.0164 | 5987 / 9558 |
| D | 35 | 91% (32/35, 78%–97%) | 94% (33/35, 81%–98%) | 95% (20/21, 77%–99%) | 100% (14/14, 78%–100%) | 0 / 1 | 0.0197 | 7332 / 10084 |
| E | 30 | 77% (23/30, 59%–88%) | 87% (26/30, 70%–95%) | 100% (28/28, 88%–100%) | 50% (1/2, 9%–91%) | 1 / 0 | 0.0084 | 17 / 11178 |
| risk (A, D, E, F) | 100 | 84% (84/100, 76%–90%) | 91% (91/100, 84%–95%) | 98% (48/49, 89%–100%) | 31% (16/51, 20%–45%) | 23 / 1 | 0.0151 | 5962 / 10201 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 29 | 3 | 0 |
| challenge | 7 | 34 | 4 |
| block | 0 | 2 | 21 |

### engineered on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 3 / 3 |
| D | 8 | 67% (4/6, 30%–90%) | 83% (5/6, 44%–97%) | 100% (3/3, 44%–100%) | 0% (0/3, 0%–56%) | 3 / 0 | 0.0192 | 6740 / 10072 |
| E | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | – | 0 / 0 | 0.0078 | 33 / 6762 |
| F | 2 | 50% (1/2, 9%–91%) | 50% (1/2, 9%–91%) | – | 50% (1/2, 9%–91%) | 2 / 0 | 0.0200 | 5979 / 6056 |
| risk (A, D, E, F) | 14 | 58% (7/12, 32%–81%) | 67% (8/12, 39%–86%) | 67% (4/6, 30%–90%) | 17% (1/6, 3%–56%) | 5 / 0 | 0.0155 | 5979 / 9530 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 4 | 1 | 0 |
| challenge | 1 | 3 | 1 |
| block | 2 | 0 | 0 |

### jev on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 94% (15/16, 72%–99%) | 94% (15/16, 72%–99%) | – | 0% (0/16, 0%–19%) | 9 / 0 | 0.0068 | 222 / 9763 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0186 | 6981 / 10513 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0090 | 548 / 10968 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 43% (3/7, 16%–75%) | 3 / 0 | 0.0157 | 8125 / 10607 |
| risk (A, D, E, F) | 51 | 92% (47/51, 82%–97%) | 96% (49/51, 87%–99%) | 100% (22/22, 85%–100%) | 31% (9/29, 17%–49%) | 12 / 0 | 0.0120 | 854 / 10992 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 18 | 0 | 0 |
| challenge | 2 | 18 | 1 |
| block | 0 | 1 | 11 |

### jev on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 86% (30/35, 71%–94%) | 91% (32/35, 78%–97%) | – | 0% (0/35, 0%–10%) | 23 / 0 | 0.0094 | 264 / 8985 |
| D | 35 | 86% (30/35, 71%–94%) | 91% (32/35, 78%–97%) | 90% (19/21, 71%–97%) | 93% (13/14, 69%–99%) | 1 / 2 | 0.0195 | 7481 / 11452 |
| E | 30 | 80% (24/30, 63%–90%) | 87% (26/30, 70%–95%) | 100% (28/28, 88%–100%) | 50% (1/2, 9%–91%) | 1 / 0 | 0.0062 | 296 / 8980 |
| risk (A, D, E, F) | 100 | 84% (84/100, 76%–90%) | 90% (90/100, 83%–94%) | 96% (47/49, 86%–99%) | 27% (14/51, 17%–41%) | 25 / 2 | 0.0120 | 358 / 10207 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 30 | 2 | 0 |
| challenge | 9 | 32 | 4 |
| block | 0 | 1 | 22 |

### jev on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 8 / 8 |
| D | 8 | 50% (3/6, 19%–81%) | 67% (4/6, 30%–90%) | 100% (3/3, 44%–100%) | 0% (0/3, 0%–56%) | 3 / 0 | 0.0241 | 7055 / 10980 |
| E | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | – | 0 / 0 | 0.0099 | 33 / 4721 |
| F | 2 | 50% (1/2, 9%–91%) | 50% (1/2, 9%–91%) | – | 50% (1/2, 9%–91%) | 2 / 0 | 0.0100 | 3104 / 5520 |
| risk (A, D, E, F) | 14 | 50% (6/12, 25%–75%) | 58% (7/12, 32%–81%) | 67% (4/6, 30%–90%) | 17% (1/6, 3%–56%) | 5 / 0 | 0.0173 | 5515 / 10065 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 4 | 1 | 0 |
| challenge | 1 | 2 | 2 |
| block | 2 | 0 | 0 |

### open_weight on dev

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 16 | 100% (16/16, 81%–100%) | 100% (16/16, 81%–100%) | – | 6% (1/16, 1%–28%) | 8 / 0 | 0.0010 | 8773 / 13842 |
| D | 15 | 93% (14/15, 70%–99%) | 93% (14/15, 70%–99%) | 100% (10/10, 72%–100%) | 100% (5/5, 57%–100%) | 0 / 0 | 0.0029 | 20692 / 27598 |
| E | 13 | 92% (12/13, 67%–99%) | 100% (13/13, 77%–100%) | 100% (12/12, 76%–100%) | 100% (1/1, 21%–100%) | 0 / 0 | 0.0015 | 22 / 32456 |
| F | 7 | 86% (6/7, 49%–97%) | 100% (7/7, 65%–100%) | – | 71% (5/7, 36%–92%) | 1 / 0 | 0.0015 | 9858 / 20122 |
| risk (A, D, E, F) | 51 | 94% (48/51, 84%–98%) | 98% (50/51, 90%–100%) | 100% (22/22, 85%–100%) | 41% (12/29, 26%–59%) | 9 / 0 | 0.0018 | 10054 / 28942 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 17 | 1 | 0 |
| challenge | 0 | 20 | 1 |
| block | 0 | 1 | 11 |

### open_weight on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 94% (33/35, 81%–98%) | 100% (35/35, 90%–100%) | – | 9% (3/35, 3%–22%) | 20 / 0 | 0.0014 | 11058 / 15631 |
| D | 35 | 94% (33/35, 81%–98%) | 97% (34/35, 85%–99%) | 100% (21/21, 85%–100%) | 100% (14/14, 78%–100%) | 0 / 0 | 0.0027 | 19518 / 26532 |
| E | 30 | 80% (24/30, 63%–90%) | 83% (25/30, 66%–93%) | 100% (28/28, 88%–100%) | 100% (2/2, 34%–100%) | 0 / 0 | 0.0014 | 20 / 31018 |
| risk (A, D, E, F) | 100 | 90% (90/100, 83%–94%) | 94% (94/100, 88%–97%) | 100% (49/49, 93%–100%) | 37% (19/51, 25%–51%) | 20 / 0 | 0.0019 | 12186 / 27118 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 30 | 2 | 0 |
| challenge | 2 | 38 | 5 |
| block | 0 | 1 | 22 |

### open_weight on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0000 | 57 / 57 |
| D | 8 | 67% (4/6, 30%–90%) | 83% (5/6, 44%–97%) | 100% (3/3, 44%–100%) | 33% (1/3, 6%–79%) | 2 / 0 | 0.0023 | 12484 / 31700 |
| E | 3 | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | 33% (1/3, 6%–79%) | – | 0 / 0 | 0.0010 | 74 / 16283 |
| F | 2 | 0% (0/2, 0%–66%) | 0% (0/2, 0%–66%) | – | 100% (2/2, 34%–100%) | 0 / 0 | 0.0029 | 17812 / 19877 |
| risk (A, D, E, F) | 14 | 50% (6/12, 25%–75%) | 58% (7/12, 32%–81%) | 67% (4/6, 30%–90%) | 50% (3/6, 19%–81%) | 2 / 0 | 0.0020 | 12484 / 30045 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 3 | 2 | 0 |
| challenge | 0 | 3 | 2 |
| block | 2 | 0 | 0 |

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

### strong on test

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 35 | 86% (30/35, 71%–94%) | 91% (32/35, 78%–97%) | – | 0% (0/35, 0%–10%) | 23 / 0 | 0.0220 | 6227 / 9671 |
| D | 35 | 86% (30/35, 71%–94%) | 91% (32/35, 78%–97%) | 90% (19/21, 71%–97%) | 93% (13/14, 69%–99%) | 1 / 2 | 0.0245 | 7580 / 10353 |
| E | 30 | 77% (23/30, 59%–88%) | 87% (26/30, 70%–95%) | 100% (28/28, 88%–100%) | 50% (1/2, 9%–91%) | 1 / 0 | 0.0250 | 6191 / 9540 |
| risk (A, D, E, F) | 100 | 83% (83/100, 74%–89%) | 90% (90/100, 83%–94%) | 96% (47/49, 86%–99%) | 27% (14/51, 17%–41%) | 25 / 2 | 0.0238 | 6607 / 9840 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 30 | 2 | 0 |
| challenge | 9 | 32 | 4 |
| block | 0 | 2 | 21 |

### strong on hard

| Category | n | Accuracy | With acceptable | Detection | Legit challenged | Lowerings (legit / other) | $ per action | p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 100% (1/1, 21%–100%) | 100% (1/1, 21%–100%) | – | 0% (0/1, 0%–79%) | 0 / 0 | 0.0161 | 3686 / 3686 |
| D | 8 | 67% (4/6, 30%–90%) | 83% (5/6, 44%–97%) | 100% (3/3, 44%–100%) | 0% (0/3, 0%–56%) | 3 / 0 | 0.0251 | 7117 / 11121 |
| E | 3 | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | 100% (3/3, 44%–100%) | – | 0 / 0 | 0.0231 | 6979 / 8511 |
| F | 2 | 50% (1/2, 9%–91%) | 50% (1/2, 9%–91%) | – | 50% (1/2, 9%–91%) | 2 / 0 | 0.0210 | 6280 / 7754 |
| risk (A, D, E, F) | 14 | 75% (9/12, 47%–91%) | 83% (10/12, 55%–95%) | 100% (6/6, 61%–100%) | 17% (1/6, 3%–56%) | 5 / 0 | 0.0235 | 7041 / 11101 |

Confusion matrix over the risk categories (rows expected, columns decided):

| Expected | allow | challenge | block |
| --- | --- | --- | --- |
| allow | 4 | 1 | 0 |
| challenge | 1 | 3 | 1 |
| block | 0 | 0 | 2 |

## Discordant cases

Cases where one configuration is right and the other wrong. A McNemar p-value is given only pooled across the risk categories.

- **always_allow vs always_challenge on dev**: pooled risk: only first right 18, only second right 21, exact p = 0.749
  - A: both 0, only first 15, only second 1, neither 0
  - D: both 0, only first 0, only second 15, neither 0
  - E: both 0, only first 0, only second 1, neither 12
  - F: both 0, only first 3, only second 4, neither 0
- **always_allow vs always_challenge on test**: pooled risk: only first right 32, only second right 45, exact p = 0.171
  - A: both 0, only first 30, only second 5, neither 0
  - D: both 0, only first 2, only second 33, neither 0
  - E: both 0, only first 0, only second 7, neither 23
- **always_allow vs always_challenge on hard**: pooled risk: only first right 5, only second right 5, exact p = 1.000
  - A: both 0, only first 1, only second 0, neither 0
  - D: both 0, only first 2, only second 4, neither 0
  - E: both 0, only first 0, only second 1, neither 2
  - F: both 0, only first 2, only second 0, neither 0
- **always_allow vs rules on dev**: pooled risk: only first right 10, only second right 30, exact p = 0.002
  - A: both 7, only first 8, only second 1, neither 0
  - D: both 0, only first 0, only second 15, neither 0
  - E: both 0, only first 0, only second 10, neither 3
  - F: both 1, only first 2, only second 4, neither 0
- **always_allow vs rules on test**: pooled risk: only first right 22, only second right 55, exact p = 0.000
  - A: both 10, only first 20, only second 3, neither 2
  - D: both 0, only first 2, only second 33, neither 0
  - E: both 0, only first 0, only second 19, neither 11
- **always_allow vs rules on hard**: pooled risk: only first right 4, only second right 5, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 0, only first 2, only second 4, neither 0
  - E: both 0, only first 0, only second 1, neither 2
  - F: both 0, only first 2, only second 0, neither 0
- **always_allow vs engineered on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_allow vs engineered on test**: pooled risk: only first right 3, only second right 55, exact p = 0.000
  - A: both 29, only first 1, only second 0, neither 5
  - D: both 0, only first 2, only second 32, neither 1
  - E: both 0, only first 0, only second 23, neither 7
- **always_allow vs engineered on hard**: pooled risk: only first right 1, only second right 3, exact p = 0.625
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 0, only second 2, neither 2
  - E: both 0, only first 0, only second 1, neither 2
  - F: both 1, only first 1, only second 0, neither 0
- **always_allow vs jev on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_allow vs jev on test**: pooled risk: only first right 2, only second right 54, exact p = 0.000
  - A: both 30, only first 0, only second 0, neither 5
  - D: both 0, only first 2, only second 30, neither 3
  - E: both 0, only first 0, only second 24, neither 6
- **always_allow vs jev on hard**: pooled risk: only first right 1, only second right 2, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 0, only second 1, neither 3
  - E: both 0, only first 0, only second 1, neither 2
  - F: both 1, only first 1, only second 0, neither 0
- **always_allow vs open_weight on dev**: pooled risk: only first right 1, only second right 31, exact p = 0.000
  - A: both 15, only first 0, only second 1, neither 0
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 2, only first 1, only second 4, neither 0
- **always_allow vs open_weight on test**: pooled risk: only first right 2, only second right 60, exact p = 0.000
  - A: both 30, only first 0, only second 3, neither 2
  - D: both 0, only first 2, only second 33, neither 0
  - E: both 0, only first 0, only second 24, neither 6
- **always_allow vs open_weight on hard**: pooled risk: only first right 2, only second right 3, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 0, only second 2, neither 2
  - E: both 0, only first 0, only second 1, neither 2
  - F: both 0, only first 2, only second 0, neither 0
- **always_allow vs strong on dev**: pooled risk: only first right 0, only second right 29, exact p = 0.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 0, only first 0, only second 14, neither 1
  - E: both 0, only first 0, only second 12, neither 1
  - F: both 3, only first 0, only second 3, neither 1
- **always_allow vs strong on test**: pooled risk: only first right 2, only second right 53, exact p = 0.000
  - A: both 30, only first 0, only second 0, neither 5
  - D: both 0, only first 2, only second 30, neither 3
  - E: both 0, only first 0, only second 23, neither 7
- **always_allow vs strong on hard**: pooled risk: only first right 1, only second right 5, exact p = 0.219
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 0, only second 2, neither 2
  - E: both 0, only first 0, only second 3, neither 0
  - F: both 1, only first 1, only second 0, neither 0
- **always_challenge vs rules on dev**: pooled risk: only first right 0, only second right 17, exact p = 0.000
  - A: both 1, only first 0, only second 7, neither 8
  - D: both 15, only first 0, only second 0, neither 0
  - E: both 1, only first 0, only second 9, neither 3
  - F: both 4, only first 0, only second 1, neither 2
- **always_challenge vs rules on test**: pooled risk: only first right 6, only second right 26, exact p = 0.001
  - A: both 3, only first 2, only second 10, neither 20
  - D: both 33, only first 0, only second 0, neither 2
  - E: both 3, only first 4, only second 16, neither 7
- **always_challenge vs rules on hard**: pooled risk: only first right 0, only second right 1, exact p = 1.000
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 4, only first 0, only second 0, neither 2
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 0, neither 2
- **always_challenge vs engineered on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **always_challenge vs engineered on test**: pooled risk: only first right 11, only second right 50, exact p = 0.000
  - A: both 0, only first 5, only second 29, neither 1
  - D: both 32, only first 1, only second 0, neither 2
  - E: both 2, only first 5, only second 21, neither 2
- **always_challenge vs engineered on hard**: pooled risk: only first right 2, only second right 4, exact p = 0.688
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 1, neither 1
- **always_challenge vs jev on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **always_challenge vs jev on test**: pooled risk: only first right 13, only second right 52, exact p = 0.000
  - A: both 0, only first 5, only second 30, neither 0
  - D: both 30, only first 3, only second 0, neither 2
  - E: both 2, only first 5, only second 22, neither 1
- **always_challenge vs jev on hard**: pooled risk: only first right 3, only second right 4, exact p = 1.000
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 1, only first 3, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 1, neither 1
- **always_challenge vs open_weight on dev**: pooled risk: only first right 1, only second right 28, exact p = 0.000
  - A: both 1, only first 0, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 4, only first 0, only second 2, neither 1
- **always_challenge vs open_weight on test**: pooled risk: only first right 7, only second right 52, exact p = 0.000
  - A: both 3, only first 2, only second 30, neither 0
  - D: both 33, only first 0, only second 0, neither 2
  - E: both 2, only first 5, only second 22, neither 1
- **always_challenge vs open_weight on hard**: pooled risk: only first right 2, only second right 3, exact p = 1.000
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 0, neither 2
- **always_challenge vs strong on dev**: pooled risk: only first right 3, only second right 29, exact p = 0.000
  - A: both 0, only first 1, only second 15, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 1, only first 0, only second 11, neither 1
  - F: both 3, only first 1, only second 3, neither 0
- **always_challenge vs strong on test**: pooled risk: only first right 13, only second right 51, exact p = 0.000
  - A: both 0, only first 5, only second 30, neither 0
  - D: both 30, only first 3, only second 0, neither 2
  - E: both 2, only first 5, only second 21, neither 2
- **always_challenge vs strong on hard**: pooled risk: only first right 2, only second right 6, exact p = 0.289
  - A: both 0, only first 0, only second 1, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 2, neither 0
  - F: both 0, only first 0, only second 1, neither 1
- **rules vs engineered on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **rules vs engineered on test**: pooled risk: only first right 5, only second right 24, exact p = 0.001
  - A: both 10, only first 3, only second 19, neither 3
  - D: both 32, only first 1, only second 0, neither 2
  - E: both 18, only first 1, only second 5, neither 6
- **rules vs engineered on hard**: pooled risk: only first right 2, only second right 3, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 1, neither 1
- **rules vs jev on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **rules vs jev on test**: pooled risk: only first right 7, only second right 26, exact p = 0.001
  - A: both 10, only first 3, only second 20, neither 2
  - D: both 30, only first 3, only second 0, neither 2
  - E: both 18, only first 1, only second 6, neither 5
- **rules vs jev on hard**: pooled risk: only first right 3, only second right 3, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 1, only first 3, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 1, neither 1
- **rules vs open_weight on dev**: pooled risk: only first right 1, only second right 11, exact p = 0.006
  - A: both 8, only first 0, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 5, only first 0, only second 1, neither 1
- **rules vs open_weight on test**: pooled risk: only first right 1, only second right 26, exact p = 0.000
  - A: both 13, only first 0, only second 20, neither 2
  - D: both 33, only first 0, only second 0, neither 2
  - E: both 18, only first 1, only second 6, neither 5
- **rules vs open_weight on hard**: pooled risk: only first right 2, only second right 2, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 0, only second 0, neither 2
- **rules vs strong on dev**: pooled risk: only first right 3, only second right 12, exact p = 0.035
  - A: both 7, only first 1, only second 8, neither 0
  - D: both 14, only first 1, only second 0, neither 0
  - E: both 10, only first 0, only second 2, neither 1
  - F: both 4, only first 1, only second 2, neither 0
- **rules vs strong on test**: pooled risk: only first right 7, only second right 25, exact p = 0.002
  - A: both 10, only first 3, only second 20, neither 2
  - D: both 30, only first 3, only second 0, neither 2
  - E: both 18, only first 1, only second 5, neither 6
- **rules vs strong on hard**: pooled risk: only first right 2, only second right 5, exact p = 0.453
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 2, only first 2, only second 2, neither 0
  - E: both 1, only first 0, only second 2, neither 0
  - F: both 0, only first 0, only second 1, neither 1
- **engineered vs jev on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **engineered vs jev on test**: pooled risk: only first right 2, only second right 2, exact p = 1.000
  - A: both 29, only first 0, only second 1, neither 5
  - D: both 30, only first 2, only second 0, neither 3
  - E: both 23, only first 0, only second 1, neither 6
- **engineered vs jev on hard**: pooled risk: only first right 1, only second right 0, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 3, only first 1, only second 0, neither 2
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 1, only first 0, only second 0, neither 1
- **engineered vs open_weight on dev**: pooled risk: only first right 1, only second right 2, exact p = 1.000
  - A: both 15, only first 0, only second 1, neither 0
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 5, only first 1, only second 1, neither 0
- **engineered vs open_weight on test**: pooled risk: only first right 1, only second right 7, exact p = 0.070
  - A: both 29, only first 0, only second 4, neither 2
  - D: both 32, only first 0, only second 1, neither 2
  - E: both 22, only first 1, only second 2, neither 5
- **engineered vs open_weight on hard**: pooled risk: only first right 2, only second right 1, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 3, only first 1, only second 1, neither 1
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 1, only second 0, neither 1
- **engineered vs strong on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **engineered vs strong on test**: pooled risk: only first right 2, only second right 1, exact p = 1.000
  - A: both 29, only first 0, only second 1, neither 5
  - D: both 30, only first 2, only second 0, neither 3
  - E: both 23, only first 0, only second 0, neither 7
- **engineered vs strong on hard**: pooled risk: only first right 0, only second right 2, exact p = 0.500
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 4, only first 0, only second 0, neither 2
  - E: both 1, only first 0, only second 2, neither 0
  - F: both 1, only first 0, only second 0, neither 1
- **jev vs open_weight on dev**: pooled risk: only first right 1, only second right 2, exact p = 1.000
  - A: both 15, only first 0, only second 1, neither 0
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 5, only first 1, only second 1, neither 0
- **jev vs open_weight on test**: pooled risk: only first right 1, only second right 7, exact p = 0.070
  - A: both 30, only first 0, only second 3, neither 2
  - D: both 30, only first 0, only second 3, neither 2
  - E: both 23, only first 1, only second 1, neither 5
- **jev vs open_weight on hard**: pooled risk: only first right 1, only second right 1, exact p = 1.000
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 3, only first 0, only second 1, neither 2
  - E: both 1, only first 0, only second 0, neither 2
  - F: both 0, only first 1, only second 0, neither 1
- **jev vs strong on dev**: pooled risk: only first right 0, only second right 0, exact p = 1.000
  - A: both 15, only first 0, only second 0, neither 1
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 6, only first 0, only second 0, neither 1
- **jev vs strong on test**: pooled risk: only first right 1, only second right 0, exact p = 1.000
  - A: both 30, only first 0, only second 0, neither 5
  - D: both 30, only first 0, only second 0, neither 5
  - E: both 23, only first 1, only second 0, neither 6
- **jev vs strong on hard**: pooled risk: only first right 0, only second right 3, exact p = 0.250
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 3, only first 0, only second 1, neither 2
  - E: both 1, only first 0, only second 2, neither 0
  - F: both 1, only first 0, only second 0, neither 1
- **open_weight vs strong on dev**: pooled risk: only first right 2, only second right 1, exact p = 1.000
  - A: both 15, only first 1, only second 0, neither 0
  - D: both 14, only first 0, only second 0, neither 1
  - E: both 12, only first 0, only second 0, neither 1
  - F: both 5, only first 1, only second 1, neither 0
- **open_weight vs strong on test**: pooled risk: only first right 8, only second right 1, exact p = 0.039
  - A: both 30, only first 3, only second 0, neither 2
  - D: both 30, only first 3, only second 0, neither 2
  - E: both 22, only first 2, only second 1, neither 5
- **open_weight vs strong on hard**: pooled risk: only first right 1, only second right 4, exact p = 0.375
  - A: both 1, only first 0, only second 0, neither 0
  - D: both 3, only first 1, only second 1, neither 1
  - E: both 1, only first 0, only second 2, neither 0
  - F: both 0, only first 0, only second 1, neither 1

## Failures by first stage that went wrong

Automatic first guess from the evidence record unless the owner tagged the case.

- rules on dev: feature 8
- rules on test: feature 21
- rules on hard: feature 4, feature_or_escalation 2
- engineered on dev: model 2
- engineered on test: feature 4, model 5
- engineered on hard: feature_or_escalation 2, model 2
- jev on dev: model 2
- jev on test: model 10
- jev on hard: feature_or_escalation 2, model 3
- open_weight on dev: feature 1
- open_weight on test: feature 6
- open_weight on hard: feature 3, feature_or_escalation 2
- strong on dev: model 2
- strong on test: model 10
- strong on hard: model 2

## Label agreement

AI labeller against the owner on 40 risk cases: agreement 45%, Cohen's κ -0.01 (95% bootstrap interval -0.15 to 0.15).
Labeller blindness: every batch sent through the Anthropic API with no tools offered, so the labeller could not open a file; it saw only its prompt.
Agreement is on the owner's blind labels. After reading the AI's, the owner settled 15 disagreements, 15 of them by taking the AI's label; the settled labels are the final ones.

## Not run

- rules on deterministic: 2
- open_weight on deterministic: 2

## Cases marked undetectable

Kept few and left out of accuracy and detection: what is observable depends on which features exist today, so each is listed here rather than excused.

- `hard_19d4fe5fcc02`
- `hard_bd1f2df9ab56`

## Limitations

- The data is synthetic; no rate here is a production rate, and the sets say nothing about how often each case occurs.
- The generator's dimensions resemble tier 0's features, so the rules look better on dev and test than they would on cases the generator did not write; the hard set is the check on that.
- The plan has Claude Haiku 5.5 write the case wording, Claude Sonnet 5.5 label, and Claude Opus 5.5 serve as the strong tier: all three from one family. The Run section lists the models that actually ran.
- With about 30 cases in a class a rate near 85% has a 95% interval of roughly ±12 points: enough to tell configurations apart in aggregate, not to rank them within a category.
- Latency, where shown, is a single run on one machine, including network time when a model ran. A repeated proposal reuses its earlier risk result (decision 0010), and the strong tier's fixed system prompt is prompt-cached; nothing else is cached.
- Payments are simulated.
- Each configuration ran once per set; Opus did not always give the same level on a repeat pass.
- On test, 60 of the 100 labels are the AI labeller's alone. On the 40 the owner labelled blind, agreement was at chance level; the owner then settled 15 of the 22 disagreements by taking the AI's label.
- The open-weight model's prompt has a section on the business's confirmation records, written from its dev failures (decision 0019); Opus's prompt does not have it.
- The open-weight model's cost is the rented GPU's hourly rent for each call's time, an upper bound that leaves out idle time; for a business running its own GPU it is a fixed cost whatever the volume.
- On hard, the open-weight arm ran under policy 2026-10-28.5 and the other arms under 2026-10-28.4; the two differ only on H24.
