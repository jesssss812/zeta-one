# Vision: the story for judges and for Rho

Written 2026-10-27. The internal specification is [product.md](product.md); this is how it is
told. The last section is the draft of the 150–300 word submission write-up.

## The one-paragraph version

Businesses are starting to let AI agents into their finances. On Rho that already happens: agents
read accounts, transactions and bills through Rho's MCP server, read-only by design, and Rho's API
spec already names the next scope, `accounts_payable:payments:write`, "initiate accounts payable
payments". The day that scope ships, a valid token will prove that a request reached the API and
nothing more: not which agent acted, not what the business meant to allow, not whether the invoice
the agent just read was written by an attacker for an AI reader. Zeta One is the trust layer a
platform runs before executing an agent's action. For each proposed payment it answers three
separate questions: is this agent known and accountable (identity), did the business authorize
this action under these conditions (delegated authorization), and does the action look like fraud
anyway (risk)? It returns allow, challenge or block with an evidence record a person can audit.

## What is new here

Three things, in the order a risk operator would weigh them. First, **the proposal is signed and
explicit**: the agent states payee, method, amount and its reason, under a key bound to a business
and an accountable person, so every action has an author. Second, **the claim is checked against
ground truth**: the bill, the vendor's history and the vendor's payment-method history are facts;
a proposal that follows an invoice's "remit to new account" line diverges from the vendor's own
record, and that divergence is something the engine measures, not a hunch about the document.
Third, **every decision leaves an evidence record** that separates what was verified, what was
authorized and what was judged. Spending limits and bank-change checks exist elsewhere; what they
lack is an actor they can hold to account and a record of why.

## Why three questions and not one score

Fraud systems score transactions. Access systems check permissions. Neither was built for an actor
that is software acting for a customer under instructions it may have been tricked into following.
A verified agent can be unauthorized (it exceeded its limit). An authorized agent can be manipulated
(the vendor's bank details changed yesterday and the invoice says "remit to the new account"). A
suspicious-looking payment can be entirely legitimate. One number hides which control failed and
what to do about it. Three answers tell the reviewer: *blocked because the authorization caps
payments at $5,000* is a different conversation from *challenged because this vendor's payment
method changed three days ago*.

## The authorization

A business grants each agent an authorization: which actions, which payees, how much per payment,
until when, and above what amount a person must confirm. It is granted once, bounded, revocable
and copied into every decision. A platform's bill approvals are per bill and in the app, and know
nothing of which agent proposed the bill or what it was allowed to do; an authorization is per
agent and up front, and the engine decides within it. Every hard limit in it is enforced in code;
no model can argue one away.

## Friction scales with risk

A challenge is not one thing. Above the confirmation threshold, the owner taps approve. An agent
that outgrew its limit gets its authorization renewed, not cut off. A payee whose bank details just
changed gets verified out of band. Only identity failures, scope violations and clear redirect
patterns are blocked outright. Most legitimate agent activity never sees a prompt, and the
evaluation measures that next to detection. Zeta One applies this ladder to business payables, where
the step-up proves the payee or the authorization rather than the human behind the agent.

## Deterministic first, calibrated second

Promises are enforced in code. Judgement is tiered, and the savings come from engineering: most
legitimate actions are decided by deterministic checks and never reach a model; a frontier model
reads the documents only where judgement is needed, and a typed decision model (Jev, which its
maker says returns calibrated probabilities at low cost) can sit between them, with its calibration
measured on our own cases rather than assumed. No decision is routed to a weaker general-purpose
model to save money. The evaluation compares rules alone, engineered escalation, the Jev cascade
and a strong model on everything, with accuracy, friction, cost and latency side by side, per
category. That is critical damping made measurable: enough control, no oscillation.

## Why it matters to Rho

Rho's customers already run agents against Rho: read-only, through Rho's MCP server, with Claude
as the native client. Rho's API is read-only by design today, approvals live in the app, and the
spec names the scope that comes next, `accounts_payable:payments:write`. Zeta One is what has to
sit in front of that scope before it ships. The spec already carries an `x-mcp-requires-approval`
annotation on its operations: the shape of the place where a trust layer's decision would plug in,
deciding when approval is needed and showing the approver the evidence. The build demonstrates
this as a customer-side gateway on Rho's own data shapes (counterparties, bills, transactions,
payment methods) with simulated execution, because no write exists yet; it protects agents routed
through it, not every Rho payment. What Rho would need to expose for it to protect every agent is
exactly that annotation's semantics: a pre-execution decision point, or an approval API. The
evidence record is also what an approver inside Rho would want to see next to a pending bill.
Everything in this paragraph beyond the spec and Rho's public API page is a proposal, not a
confirmed roadmap ([../reference/rho-api.md](../reference/rho-api.md)).

## Review and learning

Every decision leaves an evidence record built for what comes after it. A review assistant can
gather and structure the evidence for a challenged, blocked or disputed action: rebuild the
timeline, point out discrepancies, separate verified facts from inferences and open questions. A
person decides. Verified outcomes, a confirmed or cleared payment, a renewed or revoked
authorization, a payee confirmed as attacker-controlled, feed back into authorizations, trusted
entities, evaluation data and risk rules, each carrying its provenance. The assistant is designed
for and not yet built; the core works without it.

## What it is not

Not a Rho product. Not a general agent guardrail library. Not a claim that agent-driven fraud is
already a measured loss category; payment fraud is, and agents are a new path into it. Not
production accuracy: the evaluation runs on labelled synthetic cases shaped like staging data, and
says so.

## Submission write-up (draft, 150–300 words)

> **Zeta One: trust and risk checks for AI agents that move money.**
>
> **Problem.** AI agents already read business finances on Rho through its MCP server, read-only by
> design, and Rho's API spec names the next scope: initiating accounts-payable payments. When an
> agent can pay, a valid token says nothing about which agent acted, what the business meant to
> allow, or whether the invoice it just read was written by an attacker for an AI reader. Vendor
> impersonation, changed bank details and malicious invoices are old fraud; agents are a new, fast
> way to fall for them.
>
> **Who it helps.** Platforms like Rho that will receive these actions, the finance teams that want
> agents to pay routine bills without friction, and the people who review what goes wrong.
>
> **Solution.** Zeta One is the layer a platform runs before executing an agent's action, shown here
> as a gateway in front of simulated payments on Rho's data shapes. Every proposal is signed by a
> registered agent and checked against the authorization the business granted (actions, payees,
> limits, expiry). Then it is assessed against ground truth: vendor history, recent payment-method
> changes, disagreement with the bill, and invoice text aimed at an automated reader. Hard limits are
> enforced in code; most routine actions never reach a model, and a frontier model reads documents
> only where judgement is needed. The result is allow, challenge or block, with the step-up matched
> to the risk and an evidence record a person can audit.
>
> **Impact.** On labelled synthetic scenarios across five categories, the evaluation compares rules
> only, engineered escalation, a typed decision model in the loop, and a strong model everywhere,
> reporting per category: accuracy, unnecessary challenges, cost per action and latency. It shows
> how much control is enough: critical damping for agentic finance. ζ = 1.

(Fill in the measured numbers on Thursday; keep the counts honest.)
