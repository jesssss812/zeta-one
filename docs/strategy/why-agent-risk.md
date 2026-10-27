# Why agent risk: research and reusable narrative

Prepared 2026-10-27 for the submission site, write-up, and future slides. This synthesizes the
owner-supplied research discussion beginning “I agree with your framing: C should be a security
property…”, and distinguishes verified source material from hypotheses. It does not change the
[product scope](product.md) or promise new implementation.

## Core argument

Payment impersonation and redirection are established threats. Agents introduce a new attack
surface when they interpret external documents and propose financial actions. A verified agent
can operate within its authorization while following malicious contextual instructions. Identity,
authorization, and transaction risk therefore answer separate questions.

Our product hypothesis: a financial platform needs evidence about all three, with independent
execution controls and intervention proportionate to risk. Generic agent safeguards are necessary
security properties; the differentiator is useful financial risk decisions with transparent
supporting evidence and a measurable cost/friction trade-off.

## Verified sources and limits

| Source | What it supports | What it does not establish |
| --- | --- | --- |
| [FBI IC3: Business Email Compromise](https://www.ic3.gov/CrimeInfo/BEC) | BEC targets fund transfers; account-information changes should be verified using another channel | Agent-specific loss estimates; prevalence of a particular bank-change subtype |
| [NIST: Strengthening AI Agent Hijacking Evaluations](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations) | Malicious instructions embedded in data can redirect agent behavior; agent hijacking needs systematic evaluation | Financial fraud loss rates or effectiveness of Zeta One |
| [TypeSafe: introducing Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | Vendor describes structured probabilistic outputs and an inexpensive risk-classification candidate | Independent confirmation of cost, calibration, or accuracy on our payment scenarios |

The first two source pages were located and checked through web search on 2026-10-27. The TypeSafe
announcement was read earlier in this site work. Keep vendor performance statements attributed;
report our own measurements separately.

## Two threat models

1. Existing financial fraud applied to automated workflows: vendor impersonation, changed payment
   details, fraudulent invoices, and payment redirection. Faster processing or greater scale is a
   plausible agent-related amplification hypothesis, not a measured outcome in these sources.
2. Delegation and agent-specific failures: instructions in an invoice mistaken for authority,
   over-broad interpretation of a task, repeated execution, or unverified observations stored as
   trusted records. These motivate independent controls and provenance, not a claim that every
   mitigation is implemented.

The most useful intersection is familiar payment fraud manipulating a legitimate agent. A valid
signature proves neither that the proposed recipient is safe nor that the agent interpreted an
invoice correctly. Evidence from the bill, payee records, and payment history helps identify the gap.
Those records also require provenance; calling them ground truth does not make them infallible.

## Research leads requiring verification before publication

The pasted research lists $3.0B in 2025 reported BEC losses; 76% payment-fraud exposure, 74% BEC
exposure, and 58% check-fraud exposure in 2026 survey reporting; $8.6B investment-fraud losses;
and 63% wire / 50% ACH-credit BEC targeting in an earlier survey. Exact primary report pages,
populations, periods, and denominators were not supplied or verified here. Do not publish these
numbers until checked against the original FBI/AFP reports. Reported losses, survey exposure,
attempts, incidents, and transaction-level rates are different measures.

The discussion also mentions a Blue41 banking-assistant test and an IEEE agent-payment study without
exact paper citations. Preserve these as discovery leads, not evidence of actual financial losses.
No source here establishes population-level agent-driven financial fraud losses.

## Reusable copy

### Website

**Familiar fraud. A new actor moving money.**

A known agent with valid permissions can still be manipulated. Verify the actor. Bound its
authority. Assess the action.

### Write-up paragraph

Businesses already face vendor impersonation and payment-redirection attacks. Agents add a new
route into the same workflow: an instruction hidden in an invoice can influence what an otherwise
legitimate agent proposes. Zeta One separates who is acting, what the business authorized, and
whether the proposed payment is risky. Independent controls enforce hard boundaries; contextual
assessment identifies cases needing verification. The platform receives signals and evidence
alongside the outcome, while selective intelligence aims to reduce inference cost and avoid
unnecessary customer interruptions. Synthetic evaluation tests that trade-off; it does not
establish production fraud-detection accuracy.

### Future slide outline

- Existing threat: impersonation and payment redirection (FBI source).
- New attack surface: untrusted content influencing an agent (NIST source).
- Trust gap: verified identity and valid authority do not settle transaction risk.
- Product response: separate findings, evidence, proportionate intervention.
- Economics: inexpensive classification where suitable, selective escalation.
- Proof: baselines, recall, false positives, customer friction, cost, and latency.

## Use-case bank

The current synthetic fixtures cover changed vendor payment details, routine bill payment,
over-limit proposals, unknown agents, and invoice instructions redirecting payment. See the
[demo API scenarios](../reference/demo-api.md#scenarios) for expected results. The website illustrates
one category rather than suggesting vendor changes are the whole product.

Future evaluation ideas from the discussion include unfamiliar impersonation styles, compromised
legitimate vendor communications, subtle instruction injection, and legitimate urgent payments
that resemble fraud. These are candidate held-out variations, not completed benchmark results.

## Adaptation and feedback

Verified human corrections can become evaluation examples and inform proposed changes to risk
rules or models. Automate capture, evaluation, and monitoring while retaining human authority for
consequential decisions and policy changes. A complaint is not a verified fraud label. Independent
hard constraints continue to apply regardless of model improvements.

Measure useful detection at a stated review workload alongside inference cost and latency. Any
synthetic loss-exposure metric must disclose assumed amounts and labels; it is not money actually
saved. Follow the current [evaluation plan](evaluation.md) for implementation status and methodology.
