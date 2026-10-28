# Dev baseline, 2026-10-28

The first runs of every configuration on the labelled `dev` set, before any tuning. Later changes to
thresholds, prompts or rules are measured against this. `dev` is the tuning set, so these numbers
are not a score of the system: the score comes from the frozen `test` and `hard` sets
([evaluation-system.md](evaluation-system.md)).

The per-case record is [data/eval/baselines/dev-2026-10-28/](../../data/eval/baselines/dev-2026-10-28/):
`decisions.jsonl` has one row per case and configuration (label, decision, reasons, tiers run, cost,
versions), and `report.md` is the full report as it stood.

## What ran

| | |
| --- | --- |
| Cases | 51: the 48 generated `dev` cases and 3 hand-built demo cases. 22 fraud, 29 legitimate. Categories A 16, D 15, E 13, F 7 |
| Labels | Claude Sonnet 5.5, blind, through the Anthropic API with no tools, under the labelling guide of commit `64ae584`. No human labels on `dev` |
| Set hash | `a4fbf0d6e02ece3e` |
| Engine | commits `d40bade` to `7ba6857`, with no engine change between them; policy version `2026-10-28.4` |
| Backend | the real gateway stages, each case in a fresh sandbox; one run per configuration |
| Prices | Claude Opus 5.5 $4 in and $20 out per million tokens; Jev $0.042 in per million, output free; Qwen3 235B unpriced |

The configurations are described in [evaluation-system.md](evaluation-system.md#what-the-comparison-measures).
In short: `rules` never calls a model; `engineered` calls Claude Opus 5.5 only when the rules flag
something; `jev` puts Jev before Opus; `open_weight` puts Qwen3 235B in Opus's place; `strong` calls
Opus on every case.

## Results

Rates with their counts; the report gives the 95% Wilson intervals.

| Configuration | Acceptable | Fraud caught | Legitimate challenged | Legitimate blocked | Reached a model | $ per 1,000 decisions | Run cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `always_allow` | 19/51 | 0/22 | 0/29 | 0/29 | 0% | 0 | $0 |
| `always_challenge` | 36/51 | 22/22 | 29/29 | 0/29 | 0% | 0 | $0 |
| `rules` | 43/51 | 22/22 | 21/29 | 0/29 | 0% | 0 | $0 |
| `engineered` | 49/51 | 22/22 | 9/29 | 0/29 | 84% | 21.76 | $1.11 |
| `jev` | 49/51 | 22/22 | 10/29 | 0/29 | 84% | 19.98 | $1.02 |
| `open_weight` | 37/51 | 22/22 | 12/29 | 9/29 | 84% | unpriced | – |
| `strong` | 49/51 | 22/22 | 9/29 | 0/29 | 100% | 23.96 | $1.22 |

"Legitimate challenged" counts every legitimate case held for a person, including those whose label
is challenge. Every configuration that runs the rules catches all 22 fraud cases; they differ in
how much friction they cost.

## What it shows

- **A model in the loop cuts friction without missing fraud.** Rules alone hold 21 of 29 legitimate
  payments; with Claude Opus 5.5 reviewing what the rules flag, 9.
- **`engineered` matches `strong`** on every case (exact McNemar p = 1.0), for 9% less. The saving
  is small because `dev` is risk-heavy by design: 43 of 51 cases trip a rule. On a mix where most
  payments are routine, far fewer would reach a model; these numbers don't measure that.
- **Jev rarely settles a case on its own as tuned.** Of the 43 cases it saw, it settled 3; 40 went
  on to Opus. The rule after Jev sends on any answer that is elevated, unsure, or far from the rules'
  level, so loosening it is the first thing to tune.
- **The open-weight model over-blocks.** It blocked 9 legitimate payments the Claude configurations
  allowed or challenged, and challenged confirmed bank changes the labels allow.

## The misses

| Configuration | Missed | What went wrong |
| --- | --- | --- |
| `rules` | 8 legitimate payments to a vendor whose bank change a reviewer had confirmed | A confirmed change is a soft signal for a model to clear (decision 0013); with no model, the payment is held |
| `engineered`, `jev`, `strong` | `dev_043`: labelled challenge, allowed | The bank change is 90 days old and unconfirmed. The label holds to the guide: the case doesn't show which account the three later payments went to. The model inferred from the dates that they went to the new one |
| `engineered`, `jev`, `strong` | `demo_method_changed`: labelled challenge, blocked | The payment's own bill is clean, but another open bill from the same vendor addresses automated payers; with a recent unconfirmed bank change, the model raised it to high |
| `open_weight` | 14: 4 allow cases blocked, 5 challenge cases blocked, 5 allow cases challenged | The model raised risk on recent or confirmed bank changes that the labels and the Claude tiers treat as a hold or an allow |

## Limits

- One run per configuration: run-to-run variation is not measured yet.
- Labels on `dev` are the AI labeller's alone.
- The first `strong` run failed when the Anthropic account ran out of credit, and every call
  failed closed (held for a person). It was discarded and rerun; the row above is the rerun.
- All cases are synthetic, and payments are simulated.

## Compare a later run

```bash
.venv/bin/python -m eval.run --set dev --config engineered --backend real --live --max-usd 3
.venv/bin/python -m eval.baseline compare dev 2026-10-28   # every case whose decision changed
```
