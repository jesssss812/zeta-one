# 0005: Python stack, one payment action, a committed synthetic seed

Date: 2026-10-27. Status: accepted.

## Context

Two build days remain. The judges run the quick start themselves, score a working system over a
polished one, and the repo becomes public. Raw staging data can't be committed (AGENTS.md rule 3),
but the evaluation must be reproducible from the repo.

## Decision

**Stack.** Python 3.13, FastAPI, SQLite, Pydantic models for Rho's shapes written by hand from
[Rho's public OpenAPI description](https://docs.rho.co/api/v1/openapi) (only the fields the engine reads),
`httpx` for the live backend, `cryptography` for Ed25519, `pytest`. The UI is one static HTML page
served by FastAPI, no build step. Quick start is `pip install -r requirements.txt && uvicorn ...`.

**First action.** The gateway accepts exactly one action, `propose_payment`:

```json
{
  "bill_id": "optional Rho bill id",
  "counterparty_id": "...", "payment_method_id": "...",
  "source_account_id": "...",
  "amount": {"amount": 125000, "currency": "USD"},
  "memo": "...",
  "agent_rationale": "why the agent proposes this, in its own words",
  "source_document_ids": ["bill file ids the agent read"]
}
```

The agent states counterparty, payment method and amount explicitly even when a bill is given, so
"proposal disagrees with the bill" is observable and becomes a risk signal. Amounts use Rho's
`Money` shape: integer minor units and an ISO 4217 code.

**Data.** The snapshot backend seeds from `data/seed/`, a **committed synthetic dataset in Rho's
shapes**, with no real names, ids or amounts. Staging was checked the same day and holds one
vendor and no payment history ([../reference/staging-data.md](../reference/staging-data.md)), so
the seed's statistics come from assumptions about a small business's payables rather than from
staging, and the README says so. The evaluation and the demo run on the seed, so anyone can
reproduce them. The live backend is shown only to prove the Rho connection.

## Alternatives

- **TypeScript/Next.js:** better-looking UI faster, but the owner is faster in Python and the
  scored parts (engine, evaluation) are not UI.
- **Several actions** (create counterparty, change bank details, pay): more realistic, but each
  needs its own authorization fields, checks and scenarios. Bank-detail changes and bills still exist in the
  stand-in as *events* that the one action reacts to.
- **Run the eval on the staging snapshot:** truer, but unreproducible by judges and unpublishable.

## Consequences

- `data/seed/` is labelled synthetic in the README, with the generator script beside it.
- Any number reported from the live backend is shown as "live, read-only" and never used in the
  evaluation.
- Adding a second action later means a new authorization `actions` entry and a new checker; the policy
  and evidence record don't change.
