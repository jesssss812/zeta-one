# Vision: the story for judges and for Rho

Written 2026-10-27. The internal specification is [product.md](product.md); this is how it is
told. The last section is the draft of the 150–300 word submission write-up.

## The one-paragraph version

Businesses are starting to let AI agents pay their bills. When one of those agents calls a financial
platform, a valid token proves the request reached the API and nothing more: not which agent acted,
not what the business meant to allow, not whether the invoice the agent just read was written by an
attacker for an AI reader. Zeta One is the trust layer a platform runs before executing an agent's
action. For each proposed payment it answers three separate questions: is this agent known and
accountable (identity), did the business authorize this action under these conditions (delegated
authorization), and does the action look like fraud anyway (risk)? It returns allow, challenge or
block with an evidence record a person can audit.

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
and copied into every decision. Approvals in a finance platform are per bill, by a person, after
the fact; an authorization is per agent and up front, and the engine decides within it. Every
hard limit in it is enforced in code; no model can argue one away.

## Claim against ground truth

The agent's proposal, payee, method, amount and its stated reason, is a *claim*. The bill, the
vendor's history and the vendor's payment-method history are *ground truth*. The gap between them is
where manipulation shows: a proposal that follows an invoice's "remit to new account" line diverges
from the vendor's own record, and that divergence is a fact the engine can check, not a hunch about
the document.

## Friction scales with risk

A challenge is not one thing. Above the confirmation threshold, the owner taps approve. An agent
that outgrew its limit gets its authorization renewed, not cut off. A payee whose bank details just
changed gets verified out of band. Only identity failures, scope violations and clear redirect
patterns are blocked outright. Most legitimate agent activity never sees a prompt, and the
evaluation measures that next to detection. Zeta One applies this ladder to business payables, where
the step-up proves the payee or the authorization rather than the human behind the agent.

## Deterministic first, calibrated second

Promises are enforced in code. Judgement is tiered: a typed decision model (Jev) returns calibrated
probabilities in around a hundred milliseconds for a fraction of a cent; a frontier model reads the
documents only when confidence is low. Two thresholds on a calibrated probability are the allow /
challenge / block band, and the evaluation compares rules alone, the cheap model, a strong model on
everything and the cascade, with accuracy, friction, cost and latency side by side. That is
critical damping made measurable: enough control, no oscillation.

## Why it matters to Rho

Rho's customers will run agents whether or not anyone plans for it. Today the API is read-only for
third parties and approvals live in the app, which keeps money safe but means agent-initiated
activity will arrive as ordinary API calls under a person's token. Zeta One shows what a trust
layer in front of those calls looks like, built on Rho's own data shapes (counterparties, bills,
transactions, payment methods), and what Rho would need to expose, a pre-execution hook or an
approval API, for the layer to protect every agent rather than only those routed through a gateway.
The evidence record is also what an approver inside Rho would want to see next to a pending bill.

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
> **Problem.** Businesses are handing accounts-payable work to AI agents. An agent with a valid API
> token can pay anyone, and the token says nothing about what the business meant to allow or whether
> the invoice the agent just read was written by an attacker for an AI reader. Vendor impersonation,
> changed bank details and malicious invoices are old fraud; agents are a new, fast way to fall for
> them.
>
> **Who it helps.** Platforms like Rho that will receive these actions, the finance teams that want
> agents to pay routine bills without friction, and the people who review what goes wrong.
>
> **Solution.** Zeta One is the layer a platform runs before executing an agent's action, shown here
> as a gateway in front of simulated payments on Rho's data shapes. Every proposal is signed by a
> registered agent and checked against the authorization the business granted (actions, payees,
> limits, expiry). Then it is assessed for risk against ground truth: vendor history, recent
> payment-method changes, disagreement with the bill, and invoice text aimed at an automated reader.
> Hard limits are enforced in code; risk uses a cheap typed decision model first and Claude only
> when confidence is low. The result is allow, challenge or block, with the step-up matched to the
> risk and an evidence record a person can audit.
>
> **Impact.** On labelled scenarios across five categories, the evaluation compares rules only, a
> cheap classifier, a strong model everywhere and the cascade, reporting accuracy, unnecessary
> challenges, cost per action and latency. It shows how much control is enough: critical damping for
> agentic finance. ζ = 1.

(Fill in the measured numbers on Thursday; keep the counts honest.)
