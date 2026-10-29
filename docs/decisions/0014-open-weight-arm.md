# 0014: The open-weight arm takes the strong tier's place; it is not a cascade step

Date: 2026-10-28. Status: accepted. Amends 0007's escalation rule for a language-model tier and 0009's
open-weight arm. Point 2's OpenRouter default is superseded for the evaluation by 0018 (a GPU we control); point 1's
shared prompt is amended by 0019 (a section on confirmation records).

## Context

Decision 0009 allowed an open-weight comparison arm, `[tier0, open-weight, strong]`, and 0007 said a
language-model tier escalates to the next one when its level is not `low` or it disagrees with tier
0. A model tier only runs when tier 0 isn't clean, so an open-weight model either agrees (not low,
escalate) or lowers (disagrees, escalate): the strong tier would run every time, and the arm could
never save a strong call. The question the owner wants answered is what a frontier model buys over
a cheaper open model at the same job.

## Decision

1. The arm is `open_weight`: `[tier0, open_weight]` on engineered escalation. The open-weight model
   gets the strong tier's system prompt, rendered request and answer schema, and its answer is
   handled the same way (evidence filtered, level at least its worst signal, confidence never used,
   failure challenged). The engine's merge rule and floors apply unchanged.
2. It is reached through any OpenAI-compatible chat API: OpenRouter by default, or another provider
   by `OPEN_WEIGHT_BASE_URL`; the model is `OPEN_WEIGHT_MODEL`, prices `OPEN_WEIGHT_PRICES`. Without
   prices its tokens are listed as unpriced, never as free.
3. It is an evaluation arm and an opt-in gateway configuration (`ZETA_RISK_CONFIGURATION=open_weight`),
   not the default. The strong tier stays Claude through Anthropic directly (decision 0011).

## Consequences

- The evaluation compares rules, engineered (Claude), `jev` and `open_weight` on the same cases, so
  cost per decision and detection can be set side by side.
- Invoice text and payee details go to the open-weight provider, and through OpenRouter to whichever
  host serves the model. For real business data that needs the provider's data terms checked first;
  the evaluation uses synthetic data only.
- Model id, price and JSON-output support are unverified until the first live call.
