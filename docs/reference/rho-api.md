# What the Rho API allows

Sources: the public OpenAPI description (copied to [rho-openapi.json](rho-openapi.json) on
2026-10-27 from <https://docs.rho.co/api/v1/openapi>), and answers from Rho's engineering team to
our questions on 2026-10-27. Anything not listed here as confirmed is not confirmed.

## Confirmed

- **Staging API base URL:** `https://rhoapi.rho-staging.co/api/v1`. Staging tokens only work
  there; a `401` from the production host with a staging token is expected.
- **Staging app:** `https://app.rho-staging.co/`. Reaching staging requires the OpenVPN profile Rho
  assigned. See [../runbooks/staging-access.md](../runbooks/staging-access.md).
- **Auth:** `Authorization: Bearer <token>`. Tokens are issued in Rho settings with a chosen subset
  of scopes. The hackathon staging token reads every list endpoint `scripts/staging_check.py` calls
  except `/fields`, which returns `403` for a missing scope.
- **Cloudflare sits in front of staging** and rejects some client signatures with `403` error 1010
  before the token is checked. Python's default `Python-urllib` user agent is rejected; a named user
  agent such as `zeta-one-staging-check/0.1` is accepted.
- **Read-only.** Rho asked that all hackathon API use be treated as read-only unless they announce
  more staging capabilities. The only documented write is `PATCH /transactions/{id}/note`, which
  needs the `transactions:note:write` scope.
- **No way to create or change money movement.** Creating or updating bills, payees
  (counterparties) or payment requests is not exposed. The `accounts_payable:payments:write` scope
  appears in the spec, but no endpoint uses it, and Rho confirmed payment requests can't be created.
- **Approvals are readable, not actionable.** An external agent can read approval states and find
  expenses, reimbursements, bills or transactions waiting for approval. Submitting for approval,
  approving and rejecting happen only in the Rho app.
- **No webhooks and no pre-execution hook.** There are no documented webhook events or subscription
  endpoints, and no supported way for an external risk service to review a payment before it
  executes. Integrations poll the read endpoints; approval and execution stay inside Rho.

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
