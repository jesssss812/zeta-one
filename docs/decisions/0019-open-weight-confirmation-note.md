# 0019: The open-weight model is told what the business's confirmation records mean

Date: 2026-10-29. Status: accepted. Amends point 1 of 0014: the open-weight model no longer gets
exactly the strong tier's prompt.

## Context

On `dev`, Qwen 3.6 27B on our GPU (decision 0018) blocked 7 legitimate payments and cleared none
that tier 0 had flagged. In the bank changes the business had confirmed, it read the vendor's
ordinary note ("we confirmed the new details by phone with your team") as an injection, and set
aside the confirmation record in the gateway facts. Opus reads that record as settling the change.
The strong tier's prompt never says what a confirmation record means.

## Decision

1. The open-weight model's prompt is the strong tier's, plus one section
   (`zeta_one/risk/prompts/open_weight_records.md`): a change with `confirmed_by`, or the feature
   `payment_method_change_confirmed`, was verified by a person at the business, and that record,
   not the vendor's text, settles it; a vendor's note matching a confirmed change is ordinary
   correspondence, not an injection; `injection_detected` is for text that tells a reader to act;
   an unconfirmed change, or a claimed confirmation the records do not show, is still a redirect
   risk.
2. The strong tier's prompt is unchanged.

## Consequences

- On `dev` the open-weight arm went from 39 to 50 of 51 acceptable, with no fraud let through and
  no legitimate payment blocked. The section was written from `dev`'s failures, so a gain that
  holds only on `dev` is overfitting; `test` and `hard` decide.
- The two arms no longer read the same prompt: Opus does without the section. The report says so.
- Whether Opus would gain from the section too is not measured.
