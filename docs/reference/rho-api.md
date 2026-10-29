# What the Rho API allows

Sources: the public OpenAPI description (<https://docs.rho.co/api/v1/openapi>, read on
2026-10-27), answers from Rho's engineering team to our
questions on 2026-10-27, and Rho's public API page (<https://www.rho.co/product/api>, as quoted in
search results on 2026-10-27; the page itself could not be opened from the planning session).
Anything not listed here as confirmed is not confirmed.

## Confirmed

- **Hosts.** The spec lists production `https://rhoapi.rho.co/api/v1` and a sandbox
  `https://rhoapi-sandbox.rho.co/api/v1`. The hackathon uses a third host, staging (below). Whether
  hackathon tokens work against the sandbox is not known.
- **The spec's own description:** "Programmatic access to Rho's banking, spend, and treasury
  primitives: accounts, cards, payments, and the transaction ledger." Errors follow RFC 9457;
  timestamps are ISO 8601 UTC; "monetary amounts are integers in the smallest currency unit".
  Beta-tagged resources may change with notice; untagged ones are additive-only. Guides:
  `docs.rho.co/docs/v1/auth`, `/pagination`, `/versioning`.
- **Staging API base URL:** `https://rhoapi.rho-staging.co/api/v1`. Staging tokens only work
  there; a `401` from the production host with a staging token is expected.
- **Staging app:** `https://app.rho-staging.co/`. Reaching staging requires the OpenVPN profile Rho
  assigned.
- **Auth:** `Authorization: Bearer <token>`. Tokens are issued in Rho settings with a chosen subset
  of scopes. The hackathon staging token reads every list endpoint `scripts/staging_check.py` calls
  except `/fields`, which returns `403` for a missing scope.
- **Cloudflare sits in front of staging** and rejects some client signatures with `403` error 1010
  before the token is checked. Python's default `Python-urllib` user agent is rejected; a named user
  agent such as `zeta-one-staging-check/0.1` is accepted.
- **Read-only, by design and not only for the hackathon.** Rho's API page describes access tokens
  as read-only, scoped and revocable: they "cannot initiate payments or modify accounts". Only
  account Owners and Admins can create tokens (Settings → Configurations → Access Tokens), choosing
  read scopes, an optional IP allowlist and an expiry of up to one year. Rho asked that all hackathon
  API use be treated as read-only unless they announce more staging capabilities. The only
  documented write is `PATCH /transactions/{id}/note`, which needs the `transactions:note:write`
  scope.
- **A payments write is intended but not shipped.** The `accounts_payable:payments:write` scope is
  defined in the spec as "Initiate Accounts Payable payments", and the spec's description names
  payments among the API's primitives, but no endpoint uses the scope, and Rho confirmed payment
  requests can't be created. Creating or updating bills, payees (counterparties) or payment requests
  is not exposed.
- **Rho runs an MCP server, read-only, with Claude as the native client.** Rho's API page says Rho
  has a production MCP server, is listed in Anthropic's connector directory, and that Claude "can
  analyze balances, transactions and statements" with a connection that is read-only and
  revocable; other MCP clients can use the MCP guide at docs.rho.co. Not verified from our side:
  the directory listing (a third-party monitor showed the connector unhealthy on 2026-09-13), the
  server URL, whether it authorizes by OAuth or by access token, and its exact tool list. Verify by
  adding Rho under Connectors in claude.ai and asking Claude to list the tools.
- **The spec carries MCP annotations.** Operations may have `x-mcp-enabled` and
  `x-mcp-requires-approval`. In the copy we hold, only `PATCH /transactions/{id}/note` is annotated
  (`enabled: true`, `requires-approval: false`); the 37 read operations carry neither. The
  semantics are not documented in the spec. Read plainly, Rho's MCP layer has an approval-gating
  concept designed in; what triggers it and who approves is a question for Rho, not an assumption.
- **Approvals are readable, not actionable.** An external agent can read approval states and find
  expenses, reimbursements, bills or transactions waiting for approval. Submitting for approval,
  approving and rejecting happen only in the Rho app.
- **No webhooks and no pre-execution hook.** There are no documented webhook events or subscription
  endpoints, and no supported way for an external risk service to review a payment before it
  executes. Integrations poll the read endpoints; approval and execution stay inside Rho.

## What this means for Zeta One

Agents already act on Rho today: read-only, mostly through Claude over Rho's MCP server. No agent
can move money through the API yet, and the next scope on Rho's own list is
`accounts_payable:payments:write`. Zeta One is the control that would sit in front of that scope
before it ships, and `x-mcp-requires-approval` is the shape of the place its decision would plug
in. That framing is grounded in Rho's spec and page; anything beyond it (that Rho will ship the
scope, that the flag will gate it, when) is not confirmed. See
[../decisions/0009-engineered-escalation.md](../decisions/0009-engineered-escalation.md).

## Read endpoints

| Area | Endpoints |
| --- | --- |
| Business and users | `GET /business`, `/users`, `/users/{id}` |
| Accounts and cards | `GET /accounts`, `/accounts/{account_id}`, `/cards`, `/cards/{id}` |
| Transactions | `GET /transactions`, `/transactions/{id}`, `/transactions/{transaction_id}/files/{file_id}`, `/transactions/{transaction_id}/declined-authorizations`, `/scheduled-transactions` |
| Accounts payable | `GET /ap/counterparties`, `/ap/counterparties/{counterparty_id}`, `/ap/bills`, `/ap/bills/{bill_id}`, `/ap/bills/{bill_id}/files/{file_id}` |
| Expenses and reimbursements | `GET /expenses`, `/expenses/{expense_id}`, `/expenses/{expense_id}/activity`, `/expenses/{expense_id}/files/{file_id}`, `/reimbursements`, `/reimbursements/{reimbursement_id}`, `/reimbursements/{reimbursement_id}/files/{file_id}` |
| Invoicing | `GET /invoicing/customers`, `/invoicing/customers/{customer_id}`, `/invoicing/invoices`, `/invoicing/invoices/{invoice_id}`, `/invoicing/invoices/{invoice_id}/files/{file_id}` |
| Other | `GET /statements`, `/statements/{id}`, `/credit-programs` (+ `/{credit_program_id}`, `/{credit_program_id}/balance`), `/insights/cashflow`, `/insights/money-movement`, `/fields` |

## Staging data

What the staging business holds is in [staging-data.md](staging-data.md).
