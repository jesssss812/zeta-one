# 0017: Under engineered escalation, no model runs on a high floor

Date: 2026-10-28. Status: accepted. Amends 0009's engineered rule; extends to it what 0016 did after
Jev.

## Context

A tier-0 floor is a level no model can lower, and nothing is above high. When tier 0's floor is
high, a model can't change the risk level, so the case's decision rests on tier 0. On the labelled
`dev` set 14 of 51 cases have a high floor; in the baseline, the strong tier changed none of their
decisions under `engineered`, `jev` or `strong`, and they were about a third of `engineered`'s
spend ([../reference/dev-tuning.md](../reference/dev-tuning.md)).

## Decision

Under engineered escalation, which `engineered` and the open-weight arm use, the model tier does
not run when tier 0's floor is high. The rest of the rule is unchanged. `strong` still runs the
model on every case, and under the Jev rule Jev still runs on a high floor while the strong tier
does not (decision 0016).

## Consequences

- A strong-tier signal can turn a high-risk challenge into a block (a redirect pattern it reports).
  A case floored high for another reason, whose redirect only the model would see, is held for a
  person rather than blocked. The money does not move either way.
- These cases' records carry no model rationale. In the demo, the invoice-redirect scenario is now
  decided by tier 0 alone; a reviewer can still ask the review assistant for a case file.
