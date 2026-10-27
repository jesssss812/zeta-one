# 0002: A local Rho stand-in instead of a clone or live-only integration

Date: 2026-10-27. Status: accepted.

## Context

The Rho API is read-only for the hackathon: no creating payments, bills or counterparties, no
approvals and no webhooks ([../reference/rho-api.md](../reference/rho-api.md)). The demo scenarios
need events the API can't produce: a payment being proposed, a vendor's bank details changing, a
bill arriving with a malicious invoice. Also:

- staging needs a VPN, which judges and cloud sessions don't have
- the submission must be reproducible from a public repo
- staging access is expected to end after the hackathon, so it may not work at the Hack Fair
- live data can change under the evaluation

## Decision

Build a small local stand-in that uses Rho's own data shapes (generated from
[../reference/rho-openapi.json](../reference/rho-openapi.json)), with two backends behind one
interface:

- **Live:** read-only calls to Rho staging.
- **Snapshot:** a local store seeded from a one-time snapshot of staging, plus synthetic scenarios.

The snapshot backend also provides the writes the scenarios need: creating a payment (pending, held
or approved, executed or blocked), updating a counterparty's bank details with a change history, and
creating a bill with invoice text. Only Zeta One's gateway can call the payment endpoint.

Development, the evaluation and the demo run on the snapshot. The live backend shows that the Rho
connection is real.

## Alternatives

- **Full Rho clone:** rejected. It takes time from the decision engine and evaluation that judges
  score, weakens the "built on Rho" claim, and loses real vendor and payment history.
- **Live Rho only:** rejected for the reasons above.

## Consequences

- Payment execution is simulated, and the README, UI and video say so.
- Keep the stand-in to the handful of entities the scenarios need: counterparties, bills, accounts,
  transactions and payments.
- If staging data turns out sparse, synthetic scenarios carry more weight; the live read still proves
  the integration.
- If Rho announces staging write endpoints, the simulated payments can be swapped for real ones
  without changing the gateway.
