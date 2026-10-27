# 0007: Three risk tiers: deterministic features, Jev, then Claude on escalation

Date: 2026-10-27. Status: accepted.

## Context

Transaction risk is probabilistic and needs context (vendor history, document text, the agent's
stated rationale). The judges score performance (speed, cost) alongside depth, and the evaluation
plan compares rules-only, cheap classifier, strong model everywhere and selective escalation
([../strategy/evaluation.md](../strategy/evaluation.md)). Jev turned out to be a real, cheap,
typed decision model ([../reference/jev.md](../reference/jev.md)).

## Decision

Risk is assessed in up to three tiers; the policy consumes a single `risk` result whatever tier
produced it, and risk can never relax an identity or authorization block.

**Tier 0, deterministic features** (always runs, no network): computed from the data store for the
proposal's counterparty, bill and business history. Each feature is stored with its value and the
evidence it came from (record ids). A weighted rule score bands them into `low` / `elevated` /
`high`. This alone is the "rules only" configuration.

| Feature | Source |
| --- | --- |
| `counterparty_is_new`, `counterparty_age_days`, `prior_payments_count` | counterparty + settled transactions |
| `payment_method_changed_days_ago`, `payment_method_is_new` | payment-method history (stand-in event; live mode uses `updated_at` as a labelled proxy) |
| `amount_ratio_to_vendor_median`, `amount_percentile_in_business` | prior outgoing transactions |
| `duplicate_candidate` | same counterparty and amount within 7 days, or invoice number already paid |
| `bill_mismatch` | proposal amount, counterparty or method differs from the referenced bill |
| `method_not_on_counterparty` | payment method id not among the counterparty's methods |
| `lookalike_counterparty` | name within small edit distance of an established vendor |
| `off_hours` | weekend or outside 07:00–19:00 business local time (weak) |
| `document_instruction_patterns` | lexical patterns in invoice text ("update bank", "new account", "ignore", urgency) |
| `agent_velocity` | proposals by this agent in the last hour and rolling spend |

**Tier 1, Jev** (cheap, typed): `state` = a compact rendering of the features, the bill and
invoice text, and the agent's rationale. Questions: `risk_level` (choice: low / elevated / high),
`document_targets_agent` (noul: does the document instruct an automated reader to change payment
details), `proposal_matches_documents` (noul), `vendor_impersonation_signs` (noul). Each answer
carries a confidence.

**Tier 2, Claude** (strong): `claude-opus-5-5` with structured output (`messages.parse` into a
Pydantic model): `risk_level`, `signals[] {name, severity, evidence}`, `injection_detected`,
`recommended_decision`, `rationale`. The system prompt is fixed and cached; the per-request content
goes last. Effort set explicitly (`medium`), `max_tokens` small.

**Escalation (selective, the default configuration):** run tier 2 only when tier 1's `risk_level`
confidence is below a threshold (initially 0.8), tier 1 says `elevated`, tier 0 and tier 1 disagree
by more than one band, or any `noul` is yes with confidence below 0.9. The thresholds are policy
parameters recorded in the evidence record.

**Fallback:** if Jev is unreachable or no key is available, tier 1 is `claude-haiku-5-5` with the
same structured schema as tier 2, behind the same interface. The evidence record names the model
that ran.

## Alternatives

- **Strong model on everything:** simplest; ~50× the cost and ~10× the latency of Jev per action,
  and it hides the question of when a strong model is worth it. Kept as a comparison arm only.
- **Train a classifier on the seed:** the seed is synthetic, so the number would be meaningless.
  Tier 0 is the honest "trained on nothing" baseline.
- **Jev only, no strong tier:** cheap, but the adversarial invoice cases need reading comprehension
  over text that Jev's 79% many-option figure doesn't inspire confidence in.

## Consequences

- Four evaluation configurations fall out of switches: `tiers=[0]`, `[0,1]`, `[0,2]`, `[0,1,2]`.
- Cost per action is computed from reported token usage and the price table in
  [../reference/jev.md](../reference/jev.md) and the Claude pricing at run time; the report says
  which prices were used.
- Both model tiers return structured values only; no free text from a model reaches the decision.
  Model rationale is stored as evidence, labelled as model output.
