# 0003: Enforce at a customer-side gateway that holds the execution credentials

Date: 2026-10-27. Status: accepted.

## Context

Rho confirmed there is no supported way for an external risk service to review a payment before it
executes, approvals can't be actioned through the API, and there are no webhooks
([../reference/rho-api.md](../reference/rho-api.md)). Zeta One can't enforce decisions inside Rho.

## Decision

Agents send proposed actions to Zeta One's gateway. The gateway checks identity, authorization and
risk, enforces the decision, and alone holds the credentials that execute an approved action.
Agents never get unrestricted payment credentials, so they can't bypass the gateway.

## Consequences

- The protection covers agents that route through the gateway. Never present it as protecting every
  Rho payment.
- Rho's missing pre-execution hook is part of the story: the demo shows what such a hook would
  allow. It belongs under "next steps" in the README and the pitch: what Rho would need to expose to
  make this enforceable for every agent.
- Rho approval states are readable, so an optional extra can poll items waiting for approval, score
  them with the same engine and show the evidence to the person approving in Rho. Build it only once
  the core flow works.
- The only allowed Rho write, a transaction note, could attach a verdict to a settled transaction.
  Low priority, and each use needs explicit approval.
