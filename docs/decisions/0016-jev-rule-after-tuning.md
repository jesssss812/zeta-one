# 0016: The rule after Jev skips the strong tier on a high floor and escalates when Jev contradicts itself

Date: 2026-10-28. Status: accepted. Supersedes the "After Jev" row of 0007's escalation table.

## Context

The baseline `jev` run on `dev` sent 40 of 43 cases on to the strong tier
([../reference/dev-baseline.md](../reference/dev-baseline.md)). Two causes:

- Jev's answers did not tell the cases apart, fixed by giving it the compact state 0007 describes
  ([../reference/dev-tuning.md](../reference/dev-tuning.md)).
- 14 of the cases had a high tier-0 floor. No tier can lower a floor and nothing is above high, so
  the strong tier could not change their level; on `dev` it changed none of their decisions, and 11
  of them still went to it.

With the new state, one case showed a third gap: Jev answered `low` and was sure the invoice
instructed the payer, so its own finding raised the level to high and the rule let that stand.

## Decision

After Jev, the strong tier runs when any of 0007's conditions holds (`risk_level` probability below
0.8, `risk_level` is `elevated`, Jev and tier 0 differ by more than one band, a finding with
probability below 0.9), or when a finding raised Jev's level above its own `risk_level` answer. It
never runs when tier 0's floor is already high.

The thresholds are unchanged.

## Consequences

- On a high floor, the decision rests on tier 0 and Jev. The strong tier's signals can turn a
  high-risk challenge into a block (a redirect pattern it reports), so a case whose floor is high
  for a reason other than a redirect pattern, and where only the strong tier would see the
  redirect, is held for a person rather than blocked. The money does not move either way.
- Such a case's record has no strong-tier rationale. A reviewer can still ask the review assistant.
- The engineered rule is unchanged: under `engineered` the strong tier still runs on a high floor.
