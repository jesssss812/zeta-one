# Vision: the story for judges and for Rho

Written 2026-10-27. The internal specification is [product.md](product.md); this is how it is
told. The last section is the draft of the 150–300 word submission write-up.

## The one-paragraph version

Businesses are starting to let AI agents pay their bills. An agent with a valid API token can move
money, and the token says nothing about what the business actually meant to allow, or whether the
invoice the agent just read was written by an attacker for an AI reader. Zeta One sits between the
agent and the money. For each proposed payment it answers three separate questions: is this agent
known and accountable (identity), did the business authorize this action under these conditions
(delegation), and does the action look like fraud anyway (risk)? It returns allow, challenge or
block with an evidence record a human can audit, and it alone holds the credentials that execute.

## Why three questions and not one score

Fraud systems score transactions. Access systems check permissions. Neither was built for an
actor that is software acting for a customer under instructions it may have been tricked into
following. A verified agent can be unauthorized (it exceeded its limit). An authorized agent can be
manipulated (the vendor's bank details changed yesterday and the invoice says "remit to the new
account"). Collapsing these into one number hides which control failed and what to do about it.
Keeping them separate makes the decision explainable: *blocked because the mandate caps payments at
$5,000* is a different conversation from *challenged because this vendor's payment method changed
three days ago*.

## Why deterministic first, models second

Scope, limits, expiry and revocation are promises the business made; they are enforced in code and
no model can argue them away. Models are for the part that needs judgement: does this look like
vendor impersonation, does this document target an automated reader. Even there, Zeta One uses a
typed decision model first (Jev, around 100 ms and a fraction of a cent) and a frontier model only
when confidence is low. The evaluation shows the trade-off directly: rules alone, a cheap
classifier, a strong model on everything, and the cascade, with accuracy, challenge rate, cost and
latency side by side. That is the critical-damping idea made measurable: enough control, no
oscillation.

## Why it matters to Rho

Rho's customers will run agents whether or not anyone plans for it. Today Rho's API is read-only
for third parties and approvals live in the app, which keeps money safe but means agent-initiated
activity will arrive as ordinary API calls under a human's token. Zeta One shows what a trust layer
in front of those calls looks like, built on Rho's own data shapes (counterparties, bills,
transactions, payment methods), and what Rho would need to expose, a pre-execution hook or an
approval API, for the layer to protect every agent rather than only those routed through a gateway.
The evidence record is also what an approver inside Rho would want to see next to a pending bill.

## What it is not

Not a Rho product. Not a general agent guardrail library. Not a claim that agent-driven fraud is
already a measured loss category; payment fraud is, and agents are a new path into it. Not
production accuracy: the evaluation runs on labelled synthetic cases shaped like staging data, and
says so.

## Submission write-up (draft, 150–300 words)

> **Zeta One: trust and risk checks for AI agents that move money.**
>
> **Problem.** Businesses are handing accounts-payable work to AI agents. An agent with a valid API
> token can pay anyone, and the token says nothing about what the business meant to allow or whether
> the invoice the agent just read was written by an attacker for an AI reader. Vendor impersonation,
> changed bank details and malicious invoices are old fraud; agents are a new, fast way to fall for
> them.
>
> **Who it helps.** Finance teams that want agents to pay routine bills without friction, the fraud
> and support staff who review what goes wrong, and platforms like Rho that will receive these
> actions.
>
> **Solution.** Zeta One is a gateway between agents and money. Every proposed payment is signed by a
> registered agent, checked against a mandate the business granted (actions, accounts, payees, limits,
> expiry), then assessed for risk using Rho's own data: vendor history, recent payment-method changes,
> duplicates, mismatches against the bill, and instructions in the invoice aimed at an automated
> reader. Hard limits are enforced in code; risk uses a cheap typed decision model (Jev) first and
> Claude only when confidence is low. The result is allow, challenge or block, with an evidence record
> a human can audit. Execution is simulated; the Rho connection is live and read-only.
>
> **Impact.** On ~60 labelled scenarios across six categories, the evaluation compares rules only, a
> cheap classifier, a strong model everywhere and the cascade, reporting accuracy, unnecessary
> challenges, cost per action and latency. It shows how much control is enough: critical damping for
> agentic finance. ζ = 1.

(Fill in the measured numbers on Thursday; keep the count honest.)
