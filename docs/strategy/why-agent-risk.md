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
| [OWASP: LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | Defines prompt injection, including indirect injection through content a model reads, such as a file or web page | How often it happens, or losses from it |
| [TypeSafe: introducing Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | Vendor describes Jev, its first "System One" model: typed answers with probabilities instead of generated text, $0.042 per million input tokens with output free, 70–500 ms; an inexpensive risk-classification candidate | Independent confirmation of cost, calibration, or accuracy on our payment scenarios |

The FBI and NIST pages were located and checked through web search on 2026-10-27; the TypeSafe
announcement and the OWASP page were read directly on 2026-10-29. Keep vendor performance statements attributed;
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

## Payment-fraud figures, checked

These measure payment fraud in general. None of them measures fraud carried out through AI agents,
and none may be quoted as if it did (AGENTS.md rule 16). Checked against the primary sources on
2026-10-29.

| Figure | What it measures | Source |
| --- | --- | --- |
| $3.05 billion reported business email compromise (BEC) losses in 2025 (24,768 complaints); BEC was the second-largest loss category after investment fraud ($8.65 billion) | Losses reported to the FBI by victims, US-centred; reported losses, not all losses | [FBI IC3, 2025 Internet Crime Report](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf) |
| 76% of organizations saw attempted or actual payments fraud in 2025; 74% were targeted by BEC; 58% saw check fraud | A survey of 465 US treasury practitioners in January 2026: the share of organizations exposed, not a loss amount or a rate per payment | [AFP, 2026 Payments Fraud and Control Survey (press release, 14 April 2026)](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/over-75-percent-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags) |

Business email compromise is a scam in which an attacker compromises or imitates a business or
supplier email account to have payments sent to an account the attacker controls; changed bank
details on an invoice are a common form of it.

Not verified, so not for publication: a figure of 63% (wire) and 50% (ACH credit) of BEC attempts
by payment method from an earlier AFP survey, which the 2026 press release does not give; and the
Blue41 banking-assistant test and the IEEE agent-payment study mentioned in the research
discussion, for which no exact citation was supplied. No source here establishes population-level
agent-driven financial fraud losses.

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

The variations the discussion raised (unfamiliar impersonation styles, compromised legitimate
vendor communications, subtle instruction injection, legitimate urgent payments that resemble
fraud) are now part of the [evaluation plan](evaluation.md#sets): the `hard` set, written outside the generator, and
the generator's dimensions. They are planned cases, not results.

## Adaptation and feedback

Verified human corrections can become evaluation examples and inform proposed changes to risk
rules or models. Automate capture, evaluation, and monitoring while retaining human authority for
consequential decisions and policy changes. A complaint is not a verified fraud label. Independent
hard constraints continue to apply regardless of model improvements.

How this is measured, including detection at a stated review workload, synthetic loss exposure,
and verified outcomes as evaluation cases, is in the [evaluation plan](evaluation.md); this doc
doesn't restate it.
