# 0012: Verified outcomes close the loop; claims are recorded but never become labels

Date: 2026-10-28. Status: accepted for the first version.

## Context

The evidence record says what the engine decided and why, but nothing recorded what turned out to be
true afterwards: whether a challenged payment was legitimate, or whether an allowed one was fraud.
Without that, friction can't be measured on real decisions, missed fraud has nowhere to go, and the
evaluation can only ever use generated cases. AGENTS.md rule 12 says a complaint is not a fraud
label and feedback carries its provenance and verification status
([../strategy/product.md](../strategy/product.md)).

## Decision

1. A **verified outcome** is a person's finding about a decided payment: `legitimate`, `payee_fraud`,
   `manipulated_agent` or `unauthorized`, with **how they know**. Only `callback_known_number`,
   `vendor_portal`, `bank_confirmation` and `signed_customer_attestation` make it verified;
   `customer_report` and `none` are recorded as claims.
2. A person records it with the admin token: on resolving a challenge, or later on any decision with
   `POST /v1/decisions/{id}/outcomes`, an allowed payment disputed as fraud included. No model and no
   agent records one. Outcomes are appended, never edited; the latest verified one counts.
3. `GET /v1/stats` reports, from real decisions only: decisions by kind, the challenge approval rate,
   verified findings, unverified claims, **missed fraud** (allowed, later verified as fraud) and
   **unneeded challenges** (challenged, later verified legitimate).
4. Verified outcomes become evaluation cases in a `feedback` set, with their provenance, so a proposed
   change to rules or models is scored on what actually happened as well as on generated cases.

## Not in this decision

Outcomes don't change how risk is decided yet: no trusted or blocked payee list feeds tier 0, and a
confirmed bank change is still a floor. That changes the decision model and gets its own record.

## Consequences

- The site and Loom can show the whole loop: decide, review, record what was true, measure.
- A feedback case is rebuilt from the proposal on the seed, not from a stored copy of the context at
  decision time; with live Rho data that would need a context snapshot in the record.
