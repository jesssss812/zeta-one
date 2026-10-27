# What Rho staging holds

From `scripts/staging_check.py`, run 2026-10-27 16:00 UTC against
`https://rhoapi.rho-staging.co/api/v1`. Counts and field coverage only; the raw responses stay in
the gitignored `data/snapshots/`. Rerun the script and update this page if staging changes.

## Summary

The staging business is a fresh setup: funded accounts, one vendor, and no payment history. There
are no bills and no outgoing payments, and the only transaction is the opening deposit. Anything
that needs history (usual payees, usual amounts, bank-detail changes, duplicates) has to come from
synthetic scenarios.

## By endpoint

| Endpoint | Records | What is there |
| --- | --- | --- |
| `/business` | 1 | The staging business: legal name and TIN |
| `/users` | 2 | One active member and one invited; both have a role, email and phone |
| `/accounts` | 6 | 3 checking, 1 credit, 1 rewards, 1 investment. One holds $10,000,000; the rest hold $0. Account and routing last-4 are set on 3 of 6 |
| `/cards` | 2 | One active virtual card, one physical card being printed. No spending limits, spend period or usage window set |
| `/transactions` | 1 | A settled $10,000,000 ACH credit into checking on 2026-10-26: the funding deposit |
| `/ap/counterparties` | 1 | One active business vendor, created 2026-10-26, with address, email and phone, and 5 payment methods: ACH (default), wire, check, and international in USD and EUR |
| `/credit-programs` | 1 | One program with a cashback rate and repayment cadence |
| `/scheduled-transactions`, `/ap/bills`, `/expenses`, `/reimbursements`, `/invoicing/customers`, `/invoicing/invoices`, `/statements` | 0 | Empty |
| `/fields` | – | `403`: the token lacks the `fields:read` scope |

## Notes

- **Amounts are in minor units.** Every `Money` value is an integer in cents with a currency code,
  so `1000000000` is $10,000,000.
- **Payment methods carry no change history.** A counterparty's `payment_methods` list shows what
  is on file now, with no record of when bank details changed. Detecting a recent change needs the
  stand-in's own history, or comparison between snapshots taken over time.
