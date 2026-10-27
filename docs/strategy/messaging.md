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
is the damping made concrete, and the evaluation's friction score is how ζ is measured.

## One-line answers

- *How is this different from approvals?* Approvals are per bill and in the app, and know nothing
  of which agent proposed the bill or what it was allowed to do. An authorization is per agent,
  granted up front, bounded and revocable; the engine decides within it.
- *How is this different from "know your agent"?* Knowing the agent and checking its authorization
  are two of the three questions. The third is the one a trusted, authorized agent still fails:
  is this payment fraud anyway?
- *Why not a strong model on everything?* Because most legitimate actions need no judgement at all,
  and the ones that do are a small, measurable fraction. The evaluation shows the fraction.
- *Why not a cheaper model?* Savings should come from engineering, not from routing money decisions
  to a less capable model. The only cheap model in the loop is a typed decision model built for
  calibrated answers, and its calibration is measured, not assumed.
- *Can agents pay on Rho today?* No: Rho's API and MCP server are read-only by design. The spec
  names the payments-write scope as the next step, and that is the step Zeta One is built for.

## Visual identity

A logo of a decaying oscillation that settles flat, with "ζ=1".
