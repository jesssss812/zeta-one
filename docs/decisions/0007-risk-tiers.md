# 0007: Three risk tiers: deterministic features, Jev, then Claude on escalation

Date: 2026-10-27. Status: accepted. Amended the same evening after the architecture review: the
merge rule, the escalation rules per tier kind, and the removal of the Haiku fallback (decision
0009). The "After Jev" escalation row is superseded by decision 0016.

## Context

Transaction risk is probabilistic and needs context (vendor history, document text, the agent's
stated rationale). The judges score performance (speed, cost) alongside depth, and the evaluation
plan compares configurations ([../strategy/evaluation.md](../strategy/evaluation.md)). Jev turned
out to be a real, cheap, typed decision model ([../reference/jev.md](../reference/jev.md)).

## Decision

Risk is assessed in up to three tiers; the policy consumes a single `risk` result, and risk can
never relax an identity or authorization block.

**Tier 0, deterministic features** (always runs, no network): computed from the data store for the
proposal's counterparty, bill and business history. Each feature is stored with its value and the
evidence it came from (record ids). A rule score bands them into `low` / `elevated` / `high`. This
alone is the "rules only" configuration. The first version computes the first five rows; the rest
are extensions.

| Feature | Source |
| --- | --- |
| `counterparty_is_new` | counterparty created date and settled payments to it |
| `payment_method_changed_days_ago` | payment-method history (a stand-in table; Rho exposes no method timestamps) |
| `amount_ratio_to_vendor_median` | prior outgoing transactions joined to the counterparty through its paid bills |
| `bill_mismatch` | proposal amount, counterparty or method differs from the referenced bill |
| `document_instruction_patterns` | lexical patterns in invoice text ("update bank", "new account", "ignore", urgency, addressed to automated systems) |
| `duplicate_candidate` | same counterparty and amount within 7 days, invoice number already paid, or the bill's status is already `paid` |
| `lookalike_counterparty` | name within small edit distance of an established vendor |
| `off_hours` | weekend or outside 07:00–19:00 business local time (weak) |
| `agent_velocity` | proposals by this agent in the last hour and rolling spend |

`method_not_on_counterparty` (payment method id not among the counterparty's methods) is request
validation, rejected deterministically before risk runs, not a feature.

**Tier 1, Jev** (cheap, typed): `state` = a compact rendering of the features, the bill and invoice
text, and the agent's rationale, and nothing else: never the scenario name, category or setup.
Questions: `risk_level` (choice: low / elevated / high), `document_targets_agent` (noul: does the
document instruct an automated reader to change payment details), `proposal_matches_documents`
(noul), `vendor_impersonation_signs` (noul). Each answer carries a probability. There is no
language-model stand-in for this tier (decision 0009).

**Tier 2, Claude** (strong): `claude-opus-5-5` with structured output (`messages.parse` into a
Pydantic model): `risk_level`, `signals[] {name, severity, evidence}`, `injection_detected`,
`recommended_decision`, `rationale`. The system prompt is fixed and cached; the per-request content
goes last. Effort set explicitly (`medium`), `max_tokens` small. Model id and SDK call to be
confirmed on the first Console call.

### Merge rule

The final `risk.level` is computed, not taken from the last tier:

1. Tier-0 **hard flags** set a **floor** no later tier can lower: `high` for `bill_mismatch` with
   a new or changed payee; `elevated` for `bill_mismatch` otherwise, `document_instruction_patterns`,
   `payment_method_changed_days_ago` within 30 days, and when present `lookalike_counterparty` and
   `duplicate_candidate`. A recent bank-detail change is exactly the fact a model must not be able
   to wave away.
2. Above the floor, a later tier may raise or lower the level; the latest tier that ran decides,
   because it saw the most.
3. The record names `level_set_by` (the tier) and `floor` (the level and the flags that set it).

This keeps rule 7 true in structure, not only in intent: a wrong or manipulated model answer
cannot turn a redirect pattern into an allow.

### Escalation rules

Which tiers run is the *configuration*; when the next tier runs is the *escalation rule*, and it
depends on what kind of tier precedes it:

| After | Run the next tier when |
| --- | --- |
| tier 0 only (engineered escalation) | tier 0 is `elevated` or `high`, or any soft signal is present (`payment_method_changed_days_ago` set, `amount_ratio_to_vendor_median` outside 0.5–2, `counterparty_is_new`) |
| Jev | `risk_level` probability below a threshold (nominal 0.8), or `risk_level` is `elevated`, or tier 0 and Jev differ by more than one band, or any noul is yes with probability below 0.9 |
| a language model (optional open-weight arm) | its level is not `low`, or it disagrees with tier 0; its self-reported confidence never gates, because it is not calibrated |

Thresholds are policy parameters recorded in the evidence record. Jev's calibration is a vendor
claim until the evaluation measures it on our cases, and the report says so with the sample size.

## Alternatives

- **Strong model on everything:** simplest; on vendor list prices it is roughly 50× the input
  cost of Jev per action and, on vendor latency figures, roughly 10× slower, and it hides the
  question of when a strong model is worth it. Kept as a comparison arm only.
- **A smaller language model as the cheap tier:** rejected (decision 0009).
- **Train a classifier on the seed:** the seed is synthetic, so the number would be meaningless.
  Tier 0 is the honest "trained on nothing" baseline.
- **Jev only, no strong tier:** cheap, but the adversarial invoice cases need reading comprehension
  over text that Jev's many-option accuracy figures don't inspire confidence in.
- **Last tier wins:** rejected after review; it lets a model lower a deterministic flag.

## Consequences

- Evaluation configurations fall out of switches: `[tier0]`, `[tier0, strong]` with engineered
  escalation, `[tier0, jev, strong]`, `[tier0, strong-always]`, and optionally
  `[tier0, open-weight, strong]`.
- Cost per action is computed from reported token usage and the prices in
  [../reference/jev.md](../reference/jev.md) and Claude's price list at run time; the report says
  which prices were used.
- Both model tiers return structured values only; no free text from a model reaches the decision.
  Model rationale is stored as evidence, labelled as model output.
