# 0013: Verified outcomes change how risk is decided, through recorded, scoped adjustments

Date: 2026-10-28. Status: accepted for the first version. Builds on 0012; amends 0007's floor rule.

## Context

Decision 0012 records what turned out to be true after a decision, but nothing used it: a payee
confirmed as attacker-controlled could be paid again, and a bank change the business confirmed by
call-back stayed a floor no model could lower. On the generated `test` set the rules alone
challenge 39 of 51 legitimate payments, most of them for a recent bank change that was confirmed.
Outcomes should change risk. This is also the most dangerous place in the product to get wrong: an
input that lowers risk is exactly what an attacker wants to control.

## Decision

1. **An outcome changes risk only through a risk adjustment**, a row in an append-only table in the
   gateway's database (`risk_adjustments`), never by editing records, features or rules. Each row
   names the business, the subject, the effect, the outcome and decision it came from, who recorded
   it, when, and when it expires. Revoking one is a new row. Every decision that an adjustment
   affected cites its id in the evidence record (`risk.adjustments`), so any decision can be traced
   to the human finding behind it.
2. **Two adjustments in the first version**, both derived automatically from a *verified* outcome
   (0012; a customer report or no check never creates one):
   - **Blocked payment method**: a verified `payee_fraud` or `manipulated_agent` finding blocks the
     payment method the payment went to, for that business, with no expiry. Tier 0 raises the hard
     flag `payment_method_blocked` (floor `high`), and the policy blocks it as a redirect pattern.
   - **Confirmed bank change**: a verified `legitimate` finding on a decision whose floor came from a
     recent payment-method change trusts *that change*, identified by its change id, for 90 days.
     Tier 0 then reports `payment_method_change_confirmed`, and the change becomes a soft signal
     instead of a floor: it still escalates to a model, which may clear it, and any newer change to
     the method is not covered and floors again.
3. **What an adjustment can never do**: lower a bill mismatch, a missing bill reference,
   instruction text, a duplicate, an identity or authorization block; apply to another business;
   cover a change other than the one confirmed; be created by a model or an agent. Blocks only raise
   risk; trust only turns one floor into a soft signal.
4. **Rule changes are not adjustments.** A change to which flags set a floor, or to a threshold, is
   a code change with a policy-version bump and a decision record, as this one is.

## Downstream risks, and what limits each

| Risk | What could happen | What limits it now | What it still needs |
| --- | --- | --- | --- |
| Trust poisoning | Someone with the admin token marks an attacker's new bank details "legitimate, called back", and later payments to that account skip the floor | Only a verified method creates trust; trust covers one change id only and expires; the record names who; a model still reviews the soft signal; every decision cites the adjustment | Dual control (a second person) for trust, the person's identity beyond the shared admin token, and an alert when trust is created |
| A stolen admin token | The token holder can trust or unblock anything | Same as above; adjustments are append-only and cited, so the damage is traceable and revocable | Per-person credentials; out of scope for the first version (security.md, S6) |
| Wrong block | A mistaken fraud finding blocks a real vendor's account | Blocks are per payment method, not the whole vendor; an admin can revoke the block, recorded as a new row | A review queue for blocks, and a way for the vendor's confirmed details to replace a blocked method |
| Stale trust | A vendor's account is taken over months after the confirmation | Trust is for one change id and expires after 90 days; a new change is not covered | Shorter expiry for larger amounts, chosen from data |
| Less review, fewer outcomes | Lower friction means fewer challenges, so fewer outcomes, so the loop sees less of what it now lets through | Stats report missed fraud and unneeded challenges separately (0012) | Sampling a share of allowed payments for review, so the loop keeps seeing allows |
| Evaluation contamination | Outcomes that changed the rules also score the rules, and look better than they are | The feedback set is reported apart; frozen `test` and `hard` don't contain feedback cases | Holding out a share of outcomes from adjustments to measure them |
| Gaming the trigger | An attacker gets a payment held, then talks a person into "confirming" by phone on a number the attacker supplied | `callback_known_number` means a number already on file, stated in the guide and the API; the change itself is in the record for the reviewer | A required field for the number used, checked against the vendor record |
| Cross-business leakage | One business's finding changes another's risk | Every adjustment is scoped to one business id | Sharing confirmed-attacker accounts across businesses is valuable, and needs its own decision on consent and false positives |

## Consequences

- Policy version moves on. Fixtures keep the version that produced them.
- The demo can show the loop end to end: a held payment is confirmed by call-back, the same payee's
  next payment escalates instead of being floored, and a payment confirmed as fraud blocks that
  account from then on.
- The feedback evaluation set measures whether adjustments helped, beside the frozen sets.
