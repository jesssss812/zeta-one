# Documentation

Two families live here.

**Reference** (`reference/`, `runbooks/`) describes things as they are. If one disagrees with
reality, the doc is wrong and should be fixed.

**Intent** (`strategy/`, `decisions/`) records goals and the reasons behind choices, dated when
written. A mismatch with the code is expected rather than a bug; check the date before treating it as
current.

What is not done yet is in [roadmap.md](roadmap.md). Every document under `docs/` is listed below.

## Reference

| Doc | What it covers |
| --- | --- |
| [reference/hackathon.md](reference/hackathon.md) | Dates, tracks, the submission checklist and the judging criteria |
| [reference/rho-api.md](reference/rho-api.md) | What the Rho staging API allows: read endpoints, auth, and the confirmed limits (read-only, no approvals, no webhooks, no pre-execution hook) |
| [reference/staging-data.md](reference/staging-data.md) | What the Rho staging business holds: record counts and field coverage per endpoint |
| [reference/rho-openapi.json](reference/rho-openapi.json) | Rho's public OpenAPI description, copied 2026-10-27 |

## Runbooks

| Doc | What it covers |
| --- | --- |
| [runbooks/staging-access.md](runbooks/staging-access.md) | Reaching Rho staging over the VPN, running the read-only staging check, and what its errors mean |

## Strategy

| Doc | What it covers |
| --- | --- |
| [strategy/product.md](strategy/product.md) | The problem, who acts, the decision model, where enforcement runs, scope, demo scenarios, open questions |
| [strategy/evaluation.md](strategy/evaluation.md) | How Zeta One is measured: case categories, comparisons, metrics |
| [strategy/messaging.md](strategy/messaging.md) | Tagline, project explanation, design philosophy, visual identity |

## Decisions

| Doc | What it decided |
| --- | --- |
| [decisions/0001-product-direction.md](decisions/0001-product-direction.md) | Agent trust and risk rather than fraud detection alone; directions considered and dropped |
| [decisions/0002-local-rho-stand-in.md](decisions/0002-local-rho-stand-in.md) | A local stand-in in Rho's data shapes, with live and snapshot backends and simulated payments |
| [decisions/0003-customer-side-gateway.md](decisions/0003-customer-side-gateway.md) | Enforce at a gateway that alone holds the execution credentials |
| [decisions/0004-name-zeta-one.md](decisions/0004-name-zeta-one.md) | The name, and how to show it |
