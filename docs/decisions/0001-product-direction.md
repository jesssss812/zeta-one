# 0001: Product direction: agent trust and risk, not fraud detection alone

Date: 2026-10-27. Status: accepted.

## Decision

Build a trust and risk layer for financial actions initiated by AI agents that belong to a
platform's business customers or to third parties. It combines agent identity, delegated
authorization and transaction risk into an enforceable allow, challenge or block decision with an
evidence record. "Know your agent" establishes trust in the actor; risk-adaptive authorization
establishes trust in the action. Payment fraud prevention is the goal it serves.

## How we got here

1. **Payment fraud detection with an investigation agent.** The first idea: rules plus a fast, cheap
   classifier to flag suspicious payments, a stronger AI agent to investigate hard cases, and human
   review. The investigation agent appealed because it explored new agent capabilities, could help
   fraud and support staff without replacing them, and connected detection to resolution. It
   survives as the stretch review assistant; computer use was later dropped (see below).
2. **P2P lending:** dropped. Less familiar domain, realistic risk evaluation needs data we don't
   have, synthetic lending data would make a weak demo, and lending isn't central to Rho.
3. **Business payment fraud:** vendor impersonation, invoice fraud, business email compromise,
   changed bank details, payment redirection. These fit business banking and accounts payable. They
   remain the threats Zeta One defends against.
4. **Guardrails for a payment agent:** spending limits, vendor restrictions, approvals, duplicate
   prevention, prompt-injection detection. Rejected as the product: these are necessary security
   hygiene, not a differentiator. The product is the trust, identity, authorization and fraud
   problem a platform faces when it accepts actions from external agents.
5. **Know your agent.** A fraud product advisor suggested KYA as an emerging gap for financial
   platforms, and pointed to Botscent (open-source automation detection) and a vendor's KYA
   proposal (identify the actor, the person behind it, and whether they authorized this action;
   signed requests and verifiable delegated credentials). The suggestion carried weight given the
   advisor's experience, but we deliberately didn't rebuild the product around one opinion. It
   surfaced an adjacent problem, which we then combined with the payment-fraud work. The vendor's
   performance claims are unverified.

## Alternatives considered

| Direction | Strengths | Why not alone |
| --- | --- | --- |
| A. Payment fraud detection with agent safeguards | Established problem; familiar evaluation; fits fraud-ML experience | Less differentiated; overlaps Rho's existing controls; treats identity and delegation as side features |
| B. Know your agent | Emerging domain; strong relevance as agents act autonomously | Identity signals can be unreliable; cryptographic verification needs a credential ecosystem; detecting automation doesn't prove authority; hard to show effectiveness without real identity infrastructure |
| C. Risk-adaptive authorization | A concrete decision at the center; clear outcome; combines deterministic enforcement with ML risk; supports challenge, not just allow/deny | Needs careful separation of hard rules from probabilistic risk; enforceability depends on integration |

B and C are combined; A's fraud focus is the objective rather than a competing product.

## Dropped from scope

- **Computer use and browser automation**, including as a stretch goal: heavy to build, distracts
  from the core, and structured API retrieval is better wherever data is available.
- **P2P lending.**

## Consequences

- Identity, authorization and risk stay separate inputs. Identity doesn't imply authorization, and
  authorization doesn't imply the absence of fraud.
- Hard constraints are deterministic; models inform risk only.
- The review assistant is a stretch feature; the core must work without it.
