# Tuning on dev

Each change made on the labelled `dev` set after the [baseline](dev-baseline.md), what was measured,
and what it changed. `dev` is the tuning set: these are not scores. The score comes from the frozen
`test` and `hard` sets, which no change here was looked at against.

## 1. What Jev is asked, and how

**Finding.** In the baseline `jev` run, Jev answered `high` on 41 of the 43 cases it saw, the 10
allow cases among them, and said the proposal did not match the documents on nearly all of them.
Its answers did not tell the cases apart, so the rule after Jev sent 40 of 43 on to Claude Opus 5.5.

**Change.** Jev now gets a compact state, as decision 0007 describes, instead of the strong tier's
full JSON: the gateway facts and the tier-0 checks that came out true as short sentences, then the
untrusted text in blocks with a per-request boundary. The questions' wording is more concrete
(what counts as low, elevated and high; ordinary payment terms are not an instruction).
[jev.md](jev.md#how-zeta-one-calls-it) describes the state.

**Measured** by calling Jev alone on the 43 `dev` inputs the real stages build, with no Opus call;
each pass cost under a cent. Repeat passes answered almost identically.

Jev's own `risk_level` answer, by label:

| Label | Before: full JSON, first wording | After: compact state, new wording |
| --- | --- | --- |
| allow (10) | high 10 | low 8, elevated 2 |
| challenge (21) | elevated 2, high 19 | elevated 15, high 6 |
| block (12) | high 12 | elevated 1, high 11 |

| | Before | After |
| --- | --- | --- |
| Jev's level equals the level Opus reached | 18 of 43 | 32 of 43 |
| How well each yes/no separates fraud from legitimate cases (AUC; 0.5 is chance) | targets agent 0.57, mismatch 0.72, impersonation 0.68 | 0.62, 0.87, 0.79 |
| Input tokens per call, mean | 2,630 | 1,150 |

The question whether the text instructs the payer stays weak (0.62). Floors and the strong tier
carry that check; a yes from Jev raises its level and never lowers anything.
