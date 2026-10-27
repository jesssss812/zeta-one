# 0009: Cost savings come from engineered escalation, not from weaker models

Date: 2026-10-27. Status: accepted. Amends 0007.

## Context

Decision 0007 named Claude Haiku as the fallback cheap tier if Jev was unavailable. The architecture
review pointed out that a language model's self-reported confidence is not calibrated, so the same
escalation threshold cannot be shared between Jev and an LLM. The owner added a product position:
lower inference cost should come from engineering built into the product, not from routing to
less capable models.

## Decision

1. **The cheap tier is Jev or nothing.** Jev is a typed decision model whose purpose is calibrated
   probabilities at low cost; that is the one job a cheap model is legitimately for. No smaller
   general-purpose language model stands in for it.
2. **The baseline cascade is engineered:** tier 0 decides, and the strong model runs only when
   tier 0 is `elevated` or `high` or carries a soft signal (the rule in 0007). This configuration
   exists regardless of Jev and is the clearest demonstration that savings come from deciding most
   routine actions deterministically.
3. **An open-weight model of Opus/Sonnet class may be added as a comparison arm**, reached through
   an OpenAI-compatible adapter so any provider fits, chosen by what is actually available at build
   time. It is optional, off the critical path, and gated like any language model: on its level
   and its agreement with tier 0, never on its self-reported confidence.
4. **Thresholds apply only to calibrated probabilities**, and the evaluation measures Jev's
   calibration on our cases rather than trusting the vendor, stating the sample size.

## Consequences

- Evaluation arms: rules only; rules → strong (engineered escalation); rules → Jev → strong; strong
  on everything; optionally rules → open-weight → strong.
- If Jev's key or request shape isn't settled on Tuesday, nothing on Wednesday's path changes: the
  engineered cascade is the default and the Jev arm joins when it works.
- The pitch says: most legitimate actions need no model at all; the ones that do are a small,
  measured fraction; a frontier model reads documents only where judgement is needed.
