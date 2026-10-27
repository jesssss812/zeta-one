# 0008: A challenge is a typed step-up; friction scales with risk

Date: 2026-10-27. Status: accepted. Refines 0001 and 0003.

## Context

An unnecessary challenge is a cost, as missed fraud is (AGENTS.md rule 10). A single flat
"challenge" treats every uncertain case the same, so the only lever is how often to challenge. A
sales sheet from Vouched for its "Know Your Agent" product (the proposal mentioned in decision 0001)
lays out a ladder for consumer wallets: allow silently, verify once and issue a delegation, allow
repeats passively, re-consent when the agent steps outside its delegation, prove identity on high
risk, block at the edge on critical. Most legitimate agent activity never sees a prompt. The
framework is sound and we adopt its shape; the sheet's figures and claims are the vendor's and
unverified.

## Decision

A **challenge carries a type**, chosen by which question failed, and each type names the step-up
and who answers it. In business payables the threat is on the payee side (vendor impersonation,
changed bank details), so the step-ups prove the **authorization** or the **payee**, not the human
behind the agent as in a consumer wallet.

| Rung | Trigger | Challenge type | The business sees |
| --- | --- | --- | --- |
| 0 | verified, inside authorization, risk low | *(allow)* | nothing |
| 1 | as 0, with a soft signal | *(allow)* + `notify` | a line in a digest |
| 2 | amount above `human_approval_above`; new counterparty where approval is required | `confirm` | one approve / reject |
| 3 | verified agent exceeds a **limit** (per-payment, rolling, expiry) | `renew_authorization` | a consent prompt showing the old and proposed bounds; acceptance writes a new authorization version |
| 4 | elevated or high risk from payee-side signals (method changed recently, lookalike vendor, proposal disagrees with the bill) | `verify_payee` | a review task: confirm with the vendor on a known contact, or AP review |
| 5 | identity not verified; **scope** violation (action, counterparty list, revoked); high risk with a redirect pattern | *(block)* | nothing, or an alert |

The decision stays `allow` / `challenge` / `block`. A challenge holds the simulated payment until a
human resolves it; the resolution is recorded with its outcome and provenance. Rules 7 and 12 hold:
the rung for an identity or authorization failure is fixed by code, and no model picks it.

**First version:** rungs 0, 2 and 5, with `confirm` the only challenge type, and limit violations at
rung 5. Rungs 1, 3 and 4 are extensions in the order given in
[../strategy/implementation-plan.md](../strategy/implementation-plan.md); the enums and the
evidence-record fields exist from the start so adding a rung adds a policy row, not a schema change.

**Measurement:** each rung has a friction weight; the evaluation reports the friction score on
legitimate cases next to detection on suspicious ones, and the share of legitimate actions that saw
no prompt ([../strategy/evaluation.md](../strategy/evaluation.md)).

## Alternatives

- **Flat challenge:** simplest; makes the critical-damping claim unmeasurable beyond a challenge
  rate.
- **Vouched's rungs as they are:** their step-ups (OTP, ID document, selfie) prove the human. For
  an agent paying a supplier, proving the human doesn't address a changed bank account.
- **Model-chosen rung:** rejected; it would let a model soften an authorization failure.

## Consequences

- "Critical damping" has a concrete object: the ladder is the damping, and the friction score is
  how ζ is measured.
- The pitch can say what Zeta One asks beyond "know your agent": authorized, but is it fraud anyway?
- An authorization that is exceeded can be renewed instead of the agent being cut off, which is
  the day-to-day case for a legitimate agent whose workload grew.
