# 0010: Guardrails on the gateway's own weak points

Date: 2026-10-27. Status: accepted. Amends 0006 (rolling limit), 0007 (merge rule, features) and
0008 (resolve).

## Context

Zeta One adds risk of its own: a model that reads attacker-written text, model calls that can fail,
model answers that vary between runs, and demo endpoints with no authentication. The review is in
[../strategy/security.md](../strategy/security.md). The fixes below change decisions already made, so
they are recorded here.

## Decision

1. **The model may lower soft signals, and every lowering is recorded.** Hard flags stay a floor
   (0007). Below that floor, a later tier may lower the level, because clearing false alarms is
   half of critical damping. The record carries `risk.lowered` and the reason
   `risk:lowered_by_model`, and the evaluation measures lowerings on legitimate and fraudulent cases
   and attacks this path directly.
2. **Model failure fails closed.** An error, timeout, invalid output or refusal from a required tier
   gives `challenge`, reason `risk:model_unavailable`.
3. **A decision is not re-rolled.** The same proposal within 24 hours reuses the earlier risk result;
   identity and authorization still rerun.
4. **The agent gets the decision, not the reasons.** Evidence is for people.
5. **Granting, revoking and resolving need an admin token**, and agent-signed requests are refused
   on those endpoints. An agent can't approve its own challenge.
6. **The gateway finds the bill itself.** A missing bill reference is the hard flag
   `bill_not_referenced`.
7. **`limits.rolling` is checked in the first version**, not as an extension.
8. **Resolve rechecks state.** Approving a held payment reruns the deterministic checks and compares
   the payment method with the one decided on; a change blocks.

## Alternatives

- **Escalate-only model:** tier 0's level becomes a floor for everything, so a model can only raise
  risk. Safer against injection, but every soft signal would end in a challenge, and the model
  could never clear a false alarm. Rejected for now; the lowering rate on fraudulent cases in the
  evaluation is the evidence for revisiting it.
- **Fail open on model failure** (keep tier 0's decision): smoother, but it lets an attacker who can
  trigger a refusal choose the cheaper path.
- **Retry the model on disagreement and take a majority:** more calls and still re-rollable.

## Consequences

- Six more guardrail cases join the deterministic evaluation set, each held at 100%.
- The demo API's evidence record gains `risk.lowered`, `risk.reused_from` and
  `tier_results[].error`, all optional.
- Most of the work lands on Wednesday; Thursday's extensions shrink to make room.
