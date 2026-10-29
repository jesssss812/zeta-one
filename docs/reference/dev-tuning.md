# Tuning on dev

Each change made on the labelled `dev` set after the [baseline](dev-baseline.md), what was measured,
and what it changed. `dev` is the tuning set: these are not scores. The score comes from the frozen
`test` and `hard` sets, which no change here was looked at against. One change outside this page
was: the new-payee approval rule (policy 2026-10-28.5) was brought in line with decision 0006 after
the first `hard` run showed it challenging a young payee that had been paid; it changed no `dev`
decision.

## Where `dev` stands

The latest run of each arm on the 51 `dev` cases, one run each. 22 cases are fraud or a manipulated
agent, all of it detectable; 29 are legitimate.

| Arm | Acceptable | Fraud stopped | Legitimate challenged / blocked | Reached the large model | $ per 1,000 decisions | Latency p50 / p95 | Engine, policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Always allow | 19/51 | 0/22 | 0 / 0 | – | 0 | – | – |
| Always challenge | 36/51 | 22/22 | 29 / 0 | – | 0 | – | – |
| `rules` (tier 0 alone) | 43/51 | 22/22 | 21 / 0 | – | 0 | under 0.1 s | `b850a2f`, .5 |
| `jev` (tier 0, Jev, then Opus) | 49/51 | 22/22 | 9 / 0 | 23 | 12.04 | 0.9 s / 10.9 s | `23c489e`, .4 |
| `engineered` (tier 0, then Opus) | 49/51 | 22/22 | 9 / 0 | 29 | 15.26 | 5.5 s / 9.2 s | `23c489e`, .4 |
| `open_weight` (tier 0, then Qwen 3.6 27B on our GPU) | 50/51 | 22/22 | 12 / 0 | 29 | 1.76, GPU time | 10.1 s / 28.5 s | `fe349b5`, .5 |
| `strong` (Opus on every case) | 49/51 | 22/22 | 9 / 0 | 51 | 23.96 | 6.4 s / 9.5 s | `7ba6857`, .4 |

"Stopped" is challenged or blocked. Policy 2026-10-28.4 and .5 make the same decision on every `dev`
case. Latency is the whole decision; the open-weight model's is longer because it runs on one rented
GPU. `strong` was last run before sections 3 to 5, which change what Opus sees only in confirmed
changes and Jev's wording.

What it shows on `dev`: every arm with a model stops the same fraud tier 0 alone stops; the models'
work is clearing legitimate payments tier 0 flagged. Jev sends 6 fewer cases to Opus than
`engineered` for the same decisions, and the self-hosted 27B matches Opus at about a ninth of the
model cost per decision, after a prompt section written from these cases (section 6).

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

## 2. When the strong tier runs after Jev

Decision [0016](../decisions/0016-jev-rule-after-tuning.md) changes the rule:

- **No strong tier on a high floor.** 14 `dev` cases have a tier-0 floor of high. No tier can lower
  a floor or go above high, so the strong tier can't change their level; in the baseline it changed
  none of their decisions, and under `jev` 11 of them still went to it.
- **Escalate when Jev contradicts itself.** On one case Jev answered `low` while being sure the
  invoice instructed the payer, and that finding alone raised its level to high. Its answers now
  send such a case on.

Thresholds are unchanged (0.8 and 0.9).

## 3. The rerun

`jev` on `dev` with both changes, one run, compared with the baseline by
`python -m eval.baseline compare dev 2026-10-28`. The per-case record is
[data/eval/baselines/dev-2026-10-28-jev-tuned/](../../data/eval/baselines/dev-2026-10-28-jev-tuned/).

| `jev` on `dev` | Baseline | Tuned |
| --- | --- | --- |
| Acceptable | 49/51 | 49/51 |
| Fraud caught | 22/22 | 22/22 |
| Legitimate challenged | 10/29 | 9/29 |
| Legitimate blocked | 0/29 | 0/29 |
| Cases that reached Claude Opus 5.5 | 40 | 22 |
| Settled without Opus, of the 43 Jev saw | 3 | 21: 14 on a high floor, 7 on Jev's answer |
| $ per 1,000 decisions | 19.98 | 12.14 |
| Run cost | $1.02 | $0.62 |
| Latency p50 / p95 | 7.2 s / 10.6 s | 0.4 s / 9.9 s |

For comparison, unchanged since the baseline: `engineered` $21.76 and `strong` $23.96 per 1,000
decisions, both 49/51 acceptable with the same fraud caught and friction.

- **One decision changed.** `dev_029` (label challenge, allow also acceptable) was allowed: Opus
  rated it low this time and elevated in the baseline. Opus varies between runs; the change is not
  Jev's.
- **The two misses are the same cases** as every Claude configuration's. `demo_method_changed` is
  now settled by Jev rather than Opus, with the same block: tier 0 already finds instruction text
  on the vendor's other open bill, so a high level blocks it either way.
- **On this set, `jev` now matches `engineered` and `strong` on acceptable decisions, fraud caught
  and friction, for 44% and 49% less.** The gap would differ on a mix with fewer risky payments,
  where fewer cases reach any model.

## 4. No model on a high floor under `engineered`

Decision [0017](../decisions/0017-no-model-on-a-high-floor.md) applies section 2's first change to
the engineered rule, which `engineered` and the open-weight arm use. `engineered` rerun on `dev`,
one run, per-case record in
[data/eval/baselines/dev-2026-10-28-engineered-tuned/](../../data/eval/baselines/dev-2026-10-28-engineered-tuned/):

| `engineered` on `dev` | Baseline | Tuned |
| --- | --- | --- |
| Acceptable | 49/51 | 49/51 |
| Fraud caught | 22/22 | 22/22 |
| Legitimate challenged / blocked | 9/29 / 0 | 9/29 / 0 |
| Cases that reached Claude Opus 5.5 | 43 | 29 |
| $ per 1,000 decisions | 21.76 | 15.53 |
| Run cost | $1.11 | $0.79 |
| Latency p50 / p95 | 6.5 s / 10.3 s | 5.5 s / 9.6 s |

No decision changed against the baseline; the two misses are the same. `jev`, at $12.14, stays the
cheapest configuration with a model. The open-weight arm follows the same rule but was not rerun:
its `dev` results are from before the change.

## 5. Payment destinations, method details and scoped confirmations

The context can now say which bank account each past payment went to and which bill it paid, a
payment method's account ending and beneficiary, the payee's email, and which bank change a
confirmation covers ([demo-api.md](demo-api.md#scenario-result) lists the fields). They were added
so the hand-written `hard` cases can be represented. `dev`'s setup records none of the first three,
so on `dev` two things changed in what the models see; every other input is byte-identical:

- The strong tier sees a confirmation's id on the change it covers, in the 11 cases with a
  confirmed change. Before, it saw the confirmation only as a tier-0 flag.
- Jev's state words the new-payee check as "added in the last 30 days or has never been paid",
  in 4 cases, all for payees never paid. It used to say "has never been paid before", which is
  wrong for a young payee that has been paid.

`jev` and `engineered` rerun on `dev`, one run each, per-case record in
[data/eval/baselines/dev-2026-10-28-supports/](../../data/eval/baselines/dev-2026-10-28-supports/):

| On `dev` | `jev` before | `jev` after | `engineered` before | `engineered` after |
| --- | --- | --- | --- | --- |
| Acceptable | 49/51 | 49/51 | 49/51 | 49/51 |
| Fraud caught | 22/22 | 22/22 | 22/22 | 22/22 |
| Legitimate challenged / blocked | 9/29 / 0 | 9/29 / 0 | 9/29 / 0 | 9/29 / 0 |
| Cases that reached Claude Opus 5.5 | 22 | 23 | 29 | 29 |
| $ per 1,000 decisions | 12.14 | 12.04 | 15.53 | 15.26 |
| Latency p50 / p95 | 0.4 s / 9.9 s | 0.9 s / 11.0 s | 5.5 s / 9.6 s | 5.5 s / 9.3 s |

No decision changed in either arm. Of the cases whose input changed, 6 reached Opus under `jev`
and all 11 under `engineered`; the 4 with the new wording all reached Jev. The level or tier
differences there were are on cases whose input did not change, so they are run-to-run variance:
under `jev`, Jev sent `dev_016` on to Opus this time and Opus rated `dev_032` high rather than
elevated; under `engineered`, Opus rated `dev_035` elevated rather than high.

## 6. The open-weight model on a GPU we control

`open_weight` with Qwen 3.6 27B (FP8) on a rented A40 through vLLM (decision 0018), beside tier 0
alone and Opus under the same escalation. First with the strong tier's prompt, per-case record in
[data/eval/baselines/dev-2026-10-29-self-hosted/](../../data/eval/baselines/dev-2026-10-29-self-hosted/);
then with the section on confirmation records added to its prompt (decision 0019), per-case record in
[data/eval/baselines/dev-2026-10-29-records/](../../data/eval/baselines/dev-2026-10-29-records/):

| On `dev` | `rules` | Qwen 3.6 27B, strong tier's prompt | Qwen 3.6 27B, with the section | `engineered` (Opus) |
| --- | --- | --- | --- | --- |
| Acceptable | 43/51 | 39/51 | 50/51 | 49/51 |
| Fraud caught | 22/22 | 22/22 | 22/22 | 22/22 |
| Legitimate challenged / blocked | 21/29 / 0 | 14/29 / 7 | 12/29 / 0 | 9/29 / 0 |
| Cases that reached the model | – | 29 | 29 | 29 |
| Cases where the model lowered tier 0's level | – | 0 | 9 | 12 |
| $ per 1,000 decisions | 0 | 1.98 | 1.76 | 15.26 |
| Model latency p50 / p95 | – | 21.2 s / 26.0 s | 18.4 s / 29.4 s | 7.4 s / 9.4 s |

The 27B's cost is GPU time at $0.59 an hour, an upper bound.

With the strong tier's prompt it never cleared a payment tier 0 had flagged, and blocked 7
legitimate ones that tier 0 alone only challenged; it reported an injection in all 7. In the 4 that
are bank changes the business had confirmed, it read the vendor's ordinary note ("we confirmed the
new details by phone with your team") as social engineering, and set aside the business's own
confirmation record, which Opus cites to clear them.

With the section it blocked none and cleared 9. Its one miss is the demo bank-change fraud, which
it blocked where a challenge is expected. A trial run before the recorded one gave the same
decisions except `dev_022`, challenged there and allowed here. The section was written from these
`dev` failures, so `test` and `hard` decide whether the gain holds; Opus's prompt does not have it.

The earlier run of Qwen3 235B through OpenRouter (37/51, the same fraud caught and legitimate
payments challenged or blocked as the 27B's first run) predates sections 3 to 5: it reached the
model in 43 cases, so it is not a like-for-like comparison.

## Limits

- `jev` and `engineered` have two runs each with the tuned rule (sections 3 to 5), with no decision
  changed between them; the other arms have one. Jev answered almost identically on repeat passes;
  Opus did not always.
- The wording and the state were chosen by looking at `dev` labels. A gain that holds on `dev` only
  is overfitting; `test` and `hard` decide.
