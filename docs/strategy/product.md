# Product: what Zeta One is and why

Written 2026-10-27, before any code. This is intent: it says what should be true and why. How the
direction was reached is in [../decisions/0001-product-direction.md](../decisions/0001-product-direction.md).

## The problem

Businesses are starting to hand financial work to AI agents: their own agents, a vendor's agent, or
a third-party service acting on their behalf. A financial platform such as Rho that receives an
action from one of these agents needs to know:

1. **Identity:** who or what is acting, and who is accountable for it?
2. **Delegated authorization:** has the customer authorized this agent to take this action, under
   these conditions?
3. **Transaction risk:** even if the agent is legitimate and authorized, is this action fraudulent
   or unsafe? A verified, authorized agent can still be manipulated into paying an attacker.

API authentication alone answers little of this: a valid token says nothing about the limits of
what a business meant to delegate.

The goal is to prevent unauthorized and fraudulent financial activity initiated through AI agents.
Payment fraud (vendor impersonation, invoice fraud, business email compromise, changed bank
details, payment redirection) is the threat; Zeta One is the trust layer that stops it when an
agent is the one acting.

Keep claims about the size of the problem honest: published losses from business email compromise
and payment fraud show payment fraud is large, but they do not show that agent-initiated fraud is
already a measured loss category.

## Who acts

The agents belong to Rho's business customers, or to third parties acting for them. Do not assume
Rho operates its own agents. Zeta One protects the financial actions those agents initiate.

## What Zeta One does

For each proposed agent action, Zeta One answers the three questions and returns **allow**,
**challenge** (ask for more verification or human review) or **block**, with an evidence record
that explains the decision.

The lifecycle is **Assess → Decide → Review → Learn**. The hackathon build centers on Assess and
Decide; Review and Learn are designed for but come later.

Design philosophy, from control theory's critical damping: don't maximize friction or minimize it
blindly; apply the right amount of control for the risk. See [messaging.md](messaging.md).

## How a decision is made

### Identity

Possible inputs: agent registration, signed requests (for example RFC 9421 HTTP message
signatures), the business or person the agent is bound to, credential validity and revocation, and
automation signals. Verified identity rests on verifiable mechanisms such as signatures. A
classifier that says a request looks automated (Botscent is one open-source example) is a risk
signal, never proof of who the agent is or whom it represents.

### Delegated authorization

An authorization says what an agent may do: permitted actions, accounts, allowed or
blocked recipients, per-payment and cumulative limits, time windows, expiry, revocation, and which
actions need human approval. Every hard constraint is checked deterministically. No model can
override one.

### Transaction risk

Candidate signals, to be chosen by what the data supports:

- new or unusual payee
- recent change to a vendor's bank details
- amount outside the usual pattern for this vendor or business
- unusual timing
- possible duplicate payment
- invoice details that don't match vendor history
- a changed payment destination
- signs of manipulation or prompt injection in untrusted documents such as invoices

### Policy

Illustrative, not final:

| Scenario | Identity | Authorization | Risk | Outcome |
| --- | --- | --- | --- | --- |
| Unknown actor requests a payment | Unverified | None | Unknown | Block |
| Verified agent exceeds its spending limit | Verified | Invalid | Any | Block, or ask for renewed authorization |
| Verified agent pays a known vendor as usual | Verified | Valid | Low | Allow |
| Verified agent pays a bank account that just changed | Verified | Valid | Elevated | Challenge or review |
| Verified agent follows malicious invoice instructions | Verified | Possibly valid | High | Challenge or block |

A challenge is not one thing: it names a step-up (confirm, renew the authorization, verify the
payee) chosen by which question failed, so friction scales with risk and most legitimate activity
sees no prompt. See [../decisions/0008-friction-ladder.md](../decisions/0008-friction-ladder.md).

### Evidence record

Every decision records: the requested action, claimed and verified identity, delegation state,
risk signals, the decision, its reasons with references to evidence, timestamps, and the policy
version. It is what makes a decision explainable and auditable, and what a reviewer (human or AI)
works from later.

## Where it runs

Agents send proposed actions to Zeta One's gateway, which decides and alone holds the credentials to
execute. This works only if the agent can't bypass the gateway with its own unrestricted payment
credentials. A platform-side integration, where Rho calls Zeta One before executing, would protect
every agent, but Rho offers no such hook today. See
[../decisions/0003-customer-side-gateway.md](../decisions/0003-customer-side-gateway.md).

Don't present a gateway that agents use voluntarily as universal protection of Rho payments.

## Fast classification and escalation

Deterministic identity and authorization checks first, then a fast, cheap classifier for contextual
risk, and a stronger model only for the cases that need it. The cheap classifier is Jev, TypeSafe
AI's typed decision model ([../reference/jev.md](../reference/jev.md)); the strong tier is Claude.
How the tiers combine and when escalation happens is in
[../decisions/0007-risk-tiers.md](../decisions/0007-risk-tiers.md). A classifier never proves
identity or enforces authorization.

## Review and learning (stretch)

An AI review assistant would help human fraud and support staff with challenged, blocked or disputed
actions: gather evidence from structured sources (not browser automation), rebuild the timeline,
point out discrepancies and missing evidence, and recommend next steps. It separates verified facts,
inferences, open questions and missing information.

It never confirms fraud as a final ruling, revokes an agent, changes trusted labels, moves money or
makes irreversible account changes. Those stay with humans.

Verified outcomes (a customer confirms or revokes an agent, a reviewer confirms or clears a payment,
a payee is confirmed as attacker-controlled) feed back into delegation and revocation state, trusted
entities, evaluation data, risk rules and, eventually, trained or adapted risk models. A complaint alone is never a confirmed fraud label; every
piece of feedback carries its provenance and verification status.

The core works without the assistant.

## Scope

| Priority | What |
| --- | --- |
| P0 | Trust and risk decision engine: identity, delegated authorization, transaction risk, deterministic enforcement, allow/challenge/block |
| P1 | Explainable decision and evidence records |
| P2 (stretch) | AI-assisted case review with human-confirmed outcomes |

Out of scope: computer use and browser-based investigation; P2P lending; assuming Rho owns the
agents; building an autonomous payment agent as the product; treating generic agent guardrails as
the differentiator; replacing human fraud analysts or support staff.

## Demo scenarios (candidates)

1. **Unauthorized agent:** an unknown agent tries a payment. Block or require identity
   verification.
2. **Delegation violation:** a verified agent exceeds its limit or pays a blocked recipient. Block or
   ask for new authorization.
3. **Legitimate payment:** a verified agent pays an established vendor within scope. Allow, with no
   friction.
4. **Authorized but suspicious:** a verified agent pays a vendor whose bank details just changed; its
   authorization technically allows it. Challenge. Shows why identity and authorization aren't enough.
5. **Prompt injection:** a legitimate agent picks up malicious payment instructions from an invoice.
   Detect the risk instead of trusting the document.
6. **Human-assisted review (stretch):** a customer reports an unfamiliar payment; the assistant
   assembles identity, authorization, risk assessment and evidence; a human decides.

## Open questions

- **Product:** who is the first buyer (Rho, another platform, or a business)? What sets this apart
  from Rho's existing approvals and fraud controls? What is the narrowest compelling action to
  support first?
- **Identity:** what counts as a verified agent identity, who issues credentials, how is an agent
  bound to a business, and how is a credential revoked?
- **Delegation:** who grants authority, how is consent recorded, how granular must it be, and what
  happens when one agent delegates to another?
- **Risk:** which signals does the staging data support, what are the thresholds, and how are false
  positives measured?
- **Challenge flow:** for an authorized but suspicious action, challenge the customer immediately,
  gather more evidence first, or escalate to a human? Likely depends on severity and latency.
- **Review and feedback:** which cases reach human review, what evidence is enough for a reviewer,
  how a customer complaint enters the workflow, how outcomes are verified, what changes immediately
  after confirmed fraud, and which outcomes should improve the classifier.
- **Execution:** which sponsor track fits best, what to simulate versus integrate, and what minimal
  benchmark makes the demo technically credible.

## Decided since (2026-10-27, evening)

| Question | Decision | Where |
| --- | --- | --- |
| Framing | Authorization-first: identity and risk are inputs to one enforceable decision | this doc |
| Buyer and story | Platform-first: the layer a platform runs before executing an agent's action; the customer-side gateway is the demonstration, a pre-execution hook is the ask to Rho | [vision.md](vision.md), [0003](../decisions/0003-customer-side-gateway.md) |
| Challenge flow | A typed step-up ladder; first version has `confirm` only | [0008](../decisions/0008-friction-ladder.md) |
| First domain and action | Accounts payable; one action, `propose_payment`, with the agent stating counterparty, method and amount explicitly | [0005](../decisions/0005-stack-and-first-action.md) |
| Stack | Python, FastAPI, SQLite, static HTML page | [0005](../decisions/0005-stack-and-first-action.md) |
| Data | Local stand-in seeded from a staging snapshot when present, else a committed synthetic seed shaped like it | [0002](../decisions/0002-local-rho-stand-in.md), [0005](../decisions/0005-stack-and-first-action.md) |
| Identity | Registered agents with Ed25519-signed requests; replay protection; revocation | [0006](../decisions/0006-identity-and-authorization.md) |
| Authorization | JSON per (business, agent): actions, counterparty list, per-payment limit, expiry, human-approval threshold in the first version; accounts, method types and rolling limits later; checked in code | [0006](../decisions/0006-identity-and-authorization.md) |
| Risk | Tier 0 deterministic features, tier 1 Jev, tier 2 Claude on escalation; no smaller model stands in for Jev, so until it runs tier 0 escalates straight to Claude | [0007](../decisions/0007-risk-tiers.md), [0009](../decisions/0009-engineered-escalation.md) |
| Scenarios and dataset | Hand-written identity and authorization cases; generated risk sets (`dev`, frozen `test`) and a hand-written `hard` set, labelled with AI help and checked by the owner | [implementation-plan.md](implementation-plan.md) |
| Build order | A thin end-to-end first version with every principle in it, seven extension seams, then ordered extensions | [implementation-plan.md](implementation-plan.md) |
| Review assistant | Designed for, not built; the evidence record is its input | this doc |

Still open: the exact Jev request shape (verify on first call), and whether the staging snapshot is
rich enough to shape the seed from, or the seed has to be shaped from assumptions and say so.

## Goals of this build

A solo build, mainly to learn by building, explore emerging agent capabilities and meet people.
Winning isn't the main aim. The bar is something technically credible and intellectually honest,
balanced against a three-day timeline.
