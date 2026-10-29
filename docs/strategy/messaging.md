# Messaging

How Zeta One describes itself in the README, write-up, video and pitch. Why the name was chosen,
and how to show it, is in [../decisions/0004-name-zeta-one.md](../decisions/0004-name-zeta-one.md).

## Tagline

> Autonomy without instability.

Alternative, for technical audiences: "tuned to ζ = 1".

## Project explanation

> In control theory, critical damping means reaching stability without oscillation. Zeta One applies
> that philosophy to agentic finance: enabling AI agents to act autonomously while keeping financial
> risk under control.

## Design philosophy

> Don't maximize friction or minimize it blindly; apply the right amount of control for the risk.

Use this to settle product decisions. In damping terms:

- **Underdamped:** too little control, so fraud gets through.
- **Overdamped:** too much control, so legitimate payments are challenged and slowed.
- **Critically damped:** allow low-risk actions without friction, challenge what is uncertain, block
  what is clearly unauthorized.

The challenge ladder ([../decisions/0008-friction-ladder.md](../decisions/0008-friction-ladder.md))
is the damping made concrete. Critical damping is the metaphor, not a measurement: nothing here
estimates ζ. The evaluation reports what the metaphor points at, detection next to unnecessary
challenges, and a friction score once there is more than one challenge type.

## What sets it apart

Four claims, each with where it is shown. Say only what the evidence column supports. The
measured figures are in [../../data/eval/report.md](../../data/eval/report.md), one run of each
configuration on synthetic cases.

| Claim | Why it matters | Where it is shown |
| --- | --- | --- |
| **No model can talk a payment past a hard check.** Identity, authorization and tier-0 hard flags are deterministic floors; a model may only lower soft signals, and every lowering is recorded | An agent's model, an invoice's injected text or our own model being fooled can't move money by itself | Property tests over every model answer ([../decisions/0007-risk-tiers.md](../decisions/0007-risk-tiers.md)); a model that clears everything lets no blocked or challenged case through in the evaluation |
| **Routine payments need no model at all.** Engineered escalation sends only what tier 0 finds uncertain to a model; Jev, a typed decision model, can take a cut of that before a frontier model reads anything. How large that fraction is depends on the payments: on `test`, built mostly from flagged cases, it was 59 of 100 | Cost scales with judgement, not with volume | The report's Cost table: the share of decisions that reached a model, dollars per 1,000 decisions and per fraud caught, rules against engineered, `jev`, open-weight and strong-on-everything ([evaluation.md](evaluation.md)) |
| **The loop closes, and it is audited.** A person records what turned out to be true and how they know; a verified fraud finding blocks the account, a confirmed bank change stops being a hard flag, a customer's report alone changes nothing. The gateway records the person's statement of how they checked; it does not perform the check | The system gets better at exactly the cases it got wrong, without a model writing its own labels | `scripts/demo_loop.py` runs it end to end; every change is an append-only adjustment cited by the decisions it affects ([../decisions/0012-verified-outcomes.md](../decisions/0012-verified-outcomes.md), [../decisions/0013-outcomes-change-risk.md](../decisions/0013-outcomes-change-risk.md)) |
| **Agents help people, not instead of them.** When a customer disputes a payment, an assistant assembles the evidence and researches the vendor; a person decides | Case work gets faster without handing a fraud ruling to a model | The case file has no verdict field; web research never sees the business's data ([../decisions/0015-case-review-assistant.md](../decisions/0015-case-review-assistant.md)) |

And one honest line to keep: the evaluation reports the friction the engine costs legitimate
payments next to the fraud it catches, so a reader can see the trade, not only the catch rate.

## One-line answers

- *How is this different from approvals?* Approvals are per bill and in the app, and know nothing
  of which agent proposed the bill or what it was allowed to do. An authorization is per agent,
  granted up front, bounded and revocable; the engine decides within it.
- *How is this different from "know your agent"?* Knowing the agent and checking its authorization
  are two of the three questions. The third is the one a trusted, authorized agent still fails:
  is this payment fraud anyway?
- *Why not a strong model on everything?* Because routine actions need no judgement at all, and the
  evaluation shows the fraction that reaches a model and what it costs. The trade runs both ways:
  on the `hard` set, Opus on every payment caught two frauds that tier 0 found clean and so never
  sent to a model.
- *Why not a cheaper model?* Savings should come from engineering, not from routing money decisions
  to a less capable model. The only cheap model in the loop is a typed decision model built for
  calibrated answers, and its calibration is never assumed: until our cases can measure it, its
  probabilities are reported as uncalibrated. An open-weight model in the frontier model's place is
  measured as a comparison arm, so the trade is shown rather than argued
  ([../decisions/0014-open-weight-arm.md](../decisions/0014-open-weight-arm.md)).
- *Can agents pay on Rho today?* No: Rho's API and MCP server are read-only by design. The spec
  names the payments-write scope as the next step, and that is the step Zeta One is built for.

## Visual identity

A logo of a decaying oscillation that settles flat, with "ζ=1".
