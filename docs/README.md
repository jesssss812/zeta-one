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
| [reference/rho-api.md](reference/rho-api.md) | What the Rho API allows: hosts, auth, read endpoints, the confirmed limits (read-only by design, no payments write yet, no webhooks or pre-execution hook), the MCP server and the `x-mcp-*` annotations, and what that means for Zeta One |
| [reference/staging-data.md](reference/staging-data.md) | What the Rho staging business holds: record counts and field coverage per endpoint |
| [reference/rho-openapi.json](reference/rho-openapi.json) | Rho's public OpenAPI description, copied 2026-10-27 |
| [reference/jev.md](reference/jev.md) | What Jev (TypeSafe's typed decision model) is, how it is called and priced, with the request and answer shapes |
| [reference/deterministic-stages.md](reference/deterministic-stages.md) | Implemented seed, identity, authorization and tier-0 interfaces, provenance and gateway wiring |
| [reference/evaluation-system.md](reference/evaluation-system.md) | How the evaluation's cases are made, labelled, frozen, run and reported, who does each step (a person, a model, code), and the configurations and models compared |
| [reference/dev-baseline.md](reference/dev-baseline.md) | The first runs of every configuration on labelled `dev`, before tuning: results, cost, the misses and how to compare a later run |
| [reference/dev-tuning.md](reference/dev-tuning.md) | Each change tuned on `dev` after the baseline: what was measured and what it changed |
| [reference/demo-api.md](reference/demo-api.md) | The contract between the engine and the demo site: endpoints, scenario result, evidence record, ownership of directories |

## Runbooks

| Doc | What it covers |
| --- | --- |
| [runbooks/staging-access.md](runbooks/staging-access.md) | Reaching Rho staging over the VPN, running the read-only staging check, and what its errors mean |

## Strategy

| Doc | What it covers |
| --- | --- |
| [strategy/why-agent-risk.md](strategy/why-agent-risk.md) | Research-backed rationale, claim limits, and reusable copy for the site, write-up, and slides |
| [strategy/product.md](strategy/product.md) | The problem, who acts, the decision model, where enforcement runs, scope, demo scenarios, open questions |
| [strategy/evaluation.md](strategy/evaluation.md) | How Zeta One is measured: labels, case sets, labelling, comparisons, metrics, and what waits until after the hackathon |
| [strategy/security.md](strategy/security.md) | Where Zeta One adds risk of its own (models, design, build, claims), the guardrails for each, and the detailed work |
| [strategy/messaging.md](strategy/messaging.md) | Tagline, project explanation, design philosophy, visual identity |
| [strategy/implementation-plan.md](strategy/implementation-plan.md) | Architecture, modules, API, policy table, evidence record, seed and scenarios, schedule and cut list |
| [strategy/architecture.md](strategy/architecture.md) | Every component, how they connect, what runs where (laptop, judges' machines, the web), and the tradeoffs behind each technology and hosting choice |
| [strategy/parallel-build.md](strategy/parallel-build.md) | The engine's kernel, six workstreams with their files, seams and briefs, and how coding agents land work together |
| [strategy/vision.md](strategy/vision.md) | The narrative for judges and Rho, and the draft submission write-up |

## Decisions

| Doc | What it decided |
| --- | --- |
| [decisions/0001-product-direction.md](decisions/0001-product-direction.md) | Agent trust and risk rather than fraud detection alone; directions considered and dropped |
| [decisions/0002-local-rho-stand-in.md](decisions/0002-local-rho-stand-in.md) | A local stand-in in Rho's data shapes, with live and snapshot backends and simulated payments |
| [decisions/0003-customer-side-gateway.md](decisions/0003-customer-side-gateway.md) | Enforce at a gateway that alone holds the execution credentials |
| [decisions/0004-name-zeta-one.md](decisions/0004-name-zeta-one.md) | The name, and how to show it |
| [decisions/0005-stack-and-first-action.md](decisions/0005-stack-and-first-action.md) | Python/FastAPI/SQLite; one action, `propose_payment`; a committed synthetic seed for reproducibility |
| [decisions/0006-identity-and-authorization.md](decisions/0006-identity-and-authorization.md) | Ed25519-signed requests for identity; a JSON authorization checked in code |
| [decisions/0007-risk-tiers.md](decisions/0007-risk-tiers.md) | Deterministic features, then Jev, then Claude on escalation; tier-0 hard flags are a floor no model can lower |
| [decisions/0008-friction-ladder.md](decisions/0008-friction-ladder.md) | A challenge is a typed step-up (confirm, renew authorization, verify payee); friction scales with risk and is measured |
| [decisions/0009-engineered-escalation.md](decisions/0009-engineered-escalation.md) | Cost savings from engineered escalation, not weaker models; the cheap tier is Jev or nothing |
| [decisions/0010-gateway-guardrails.md](decisions/0010-gateway-guardrails.md) | Guardrails on the gateway's own weak points: recorded model lowering, fail closed, no re-rolling, admin token, gateway-side bill lookup, rolling limit, recheck on resolve |
| [decisions/0011-deployment-and-hosting.md](decisions/0011-deployment-and-hosting.md) | Live gateway on the laptop, SQLite state, Anthropic direct, a static Vercel site with recorded real runs, CI on every push |
| [decisions/0012-verified-outcomes.md](decisions/0012-verified-outcomes.md) | People record what turned out to be true and how they know; only verified findings count, and they feed the stats and the evaluation |
| [decisions/0013-outcomes-change-risk.md](decisions/0013-outcomes-change-risk.md) | Verified outcomes change risk through append-only, scoped adjustments: a fraud finding blocks the payment method, a confirmed bank change stops being a floor; the downstream risks |
| [decisions/0014-open-weight-arm.md](decisions/0014-open-weight-arm.md) | The open-weight arm takes the strong tier's place on the same prompt and rules, through any OpenAI-compatible API; it is a comparison, not a cascade step |
| [decisions/0015-case-review-assistant.md](decisions/0015-case-review-assistant.md) | An AI assistant assembles a case file for a person: code gathers internal evidence, a minimised call researches the vendor on the web, no verdict; its risks |
| [decisions/0016-jev-rule-after-tuning.md](decisions/0016-jev-rule-after-tuning.md) | After Jev, the strong tier never runs on a high floor and runs when Jev's findings contradict its own level |
