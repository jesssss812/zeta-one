# 0006: Ed25519-signed requests for identity; a JSON authorization checked in code

Date: 2026-10-27. Status: accepted.

## Context

Identity must rest on a verifiable mechanism, not on detection (decision 0001). Delegated
authorization must be deterministic (AGENTS.md rule 7). No credential ecosystem exists for agents
yet, so Zeta One issues and binds credentials itself. Two build days remain, so the first version
carries only the fields the demo scenarios need, with a shape that takes more.

## Decision

### Identity

Each agent is **registered** with Zeta One: `agent_id`, the `business_id` it acts for, the
accountable owner (a Rho user id or email), an Ed25519 public key, `status` (`active` | `revoked`),
and timestamps. The agent signs every request:

```
headers: Zeta-Agent-Id, Zeta-Timestamp (RFC 3339), Zeta-Nonce, Zeta-Signature (base64)
signed string: agent_id "\n" timestamp "\n" nonce "\n" METHOD "\n" path "\n" sha256(body)
```

The gateway verifies in order: agent known → status active → timestamp within ±300 s → nonce unseen
→ signature valid. The identity result is one of `verified`, `unsigned`, `unknown_agent`,
`revoked`, `stale_timestamp`, `replay`, `invalid_signature`. Only `verified` proceeds to the
authorization check. The scheme follows the shape of RFC 9421 HTTP message signatures but is not
claimed to be compliant.

Automation-detection signals (Botscent-style) are not implemented; the evidence record has a slot
for them as risk signals.

### Authorization

An **authorization** is the document in which a business says what an agent may do. One active
authorization per `(business_id, agent_id)`, JSON, stored by the gateway. Fields in the first
version:

| Field | Meaning |
| --- | --- |
| `authorization_id`, `version`, `policy_version` | identity and provenance |
| `granted_by`, `granted_at`, `expires_at`, `status`, `revoked_at` | lifecycle; `status` is `active` or `revoked` |
| `actions` | allowed actions, e.g. `["propose_payment"]` |
| `counterparties` | `{"mode": "any" \| "allowlist" \| "denylist", "ids": [...]}` |
| `limits.per_payment` | max amount per proposal |
| `human_approval_above` | amount above which an otherwise-clean proposal is challenged for human approval |

Fields the shape allows and a later version checks: `source_accounts`, `payment_method_types`,
`allow_new_counterparties`, `limits.rolling` (`{"window_days", "amount"}`). Unknown fields are
stored and ignored, so an authorization written for a later version still loads.

The checker is an ordered list of functions, one per field, each returning a violation
`{field, limit, observed}` or nothing; adding a constraint adds one function. All violations are
listed even though the first suffices. Violations are classed as **scope** (action not permitted,
denylisted or non-allowlisted counterparty, revoked) or **limit** (per-payment, expiry, and later
rolling), because the policy may treat them differently (decision 0008). The authorization as stored
is copied into the evidence record.

Signing the authorization with the grantor's key is a stretch; the hackathon build stores it
unsigned and says so.

## Alternatives

- **Bearer API keys per agent:** simpler, but a leaked key is indistinguishable from the agent, and
  there's no replay protection. Signatures cost little more.
- **OAuth-style delegated tokens / verifiable credentials:** the right long-term shape; too much
  infrastructure for two days and nothing on the Rho side consumes them.
- **Authorization as policy code (OPA/Cedar):** expressive, but a JSON document is easier to show in
  the UI and to copy into the evidence record.
- **"Mandate"** as the noun, by analogy with direct-debit mandates: rejected; "authorization" is the
  word the three questions already use and needs no explaining.

## Consequences

- Revocation is immediate: flipping `status` on the agent or the authorization blocks the next
  request.
- The demo's "unknown agent", "revoked agent" and "replay" scenarios need no risk model at all,
  which shows the layering.
- A second agent delegating to a third is out of scope; an authorization binds one agent.
