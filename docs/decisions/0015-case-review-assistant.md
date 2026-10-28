# 0015: A case-review assistant assembles evidence for a person; it never decides

Date: 2026-10-28. Status: accepted for the first version. The P2 review assistant of
[../strategy/product.md](../strategy/product.md#review-and-learning-stretch), now that the core works.

## Context

When a customer reports that a payment the gateway allowed was fraud, a case worker has to rebuild
what happened: the decision and why, the payee's history, every payment to that bank account, the
bank-change timeline, earlier findings, and what the outside world says about the vendor. That is
slow, and it is exactly the kind of gathering and summarising rule 12 allows an AI to do. Rule 12
also bounds it: the assistant never confirms fraud, revokes an agent, changes a label or moves
money.

## Decision

1. **A case file is assembled on request** by a person with the admin token (`POST /v1/cases`
   naming a decision), typically after a customer's report. It is stored append-only and shown on a
   review page served by the gateway; the person then records a finding through the existing
   outcome endpoint (0012), which is what changes risk (0013).
2. **Internal evidence is gathered by code, not by the model**: the decision record with the
   proposal and context as decided, every payment by the business to the same payee and to the same
   payment method, the method-change timeline, outcomes and risk adjustments. Code gathering is
   complete and auditable; the model is given it, cannot ask for more, and cannot write.
3. **Web research is a separate, minimised call.** A first model call gets only public facts, the
   vendor's name and any web domains or phone numbers in the invoice text, and uses Anthropic's web
   search (at most 5 searches). It never sees amounts, account or method ids, the business or the
   agent. Its findings come back with their URLs and are passed to the second call as untrusted text
   in bounded blocks, like invoice text, because a web page can carry instructions too.
4. **The second call writes the case file** as structured output with no verdict field: a summary,
   a timeline, verified facts (each citing a record id or URL), inferences with their basis,
   contradictions, open questions, missing evidence and suggested next steps for a person (such as a
   call-back on the number already on file). Any web finding is labelled as such.
5. **Fail soft, never fail open.** If research fails, the case file says so and is built from internal
   evidence; if assembly fails, the case records the error and the raw evidence is still shown.
   Nothing here changes a decision, a payment or risk.

## Risks

| Risk | Limit now | Still needs |
| --- | --- | --- |
| Business data leaking into web search queries | The research call never receives it | A check of the logged queries against the case's sensitive values |
| A web page or invoice steering the summary | Untrusted blocks, with a per-request boundary; the person reads cited sources | An evaluation of the assistant on adversarial pages |
| A person rubber-stamping the summary | No verdict field; facts cite sources; the finding still needs a verification method (0012) | Measuring how often findings match the case file's suggestions |
| Cost per case | One research call (5 searches at most) and one assembly call, recorded with the case | A per-day budget |
| The model inventing a "verified fact" | Facts must cite a record id or URL present in the evidence; others are dropped to inferences | Spot checks |

## Consequences

- The demo can show the agentic part where it is safe: gathering and research for a person, after
  the deterministic engine has decided.
- Needs the Anthropic key; the tests run against a stubbed client.
