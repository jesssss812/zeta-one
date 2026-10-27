# 0006: Ed25519-signed requests for identity; a JSON mandate checked in code

Date: 2026-10-27. Status: accepted.

## Context

Identity must rest on a verifiable mechanism, not on detection (decision 0001). Authorization must be
deterministic (AGENTS.md rule 7). No credential ecosystem exists for agents yet, so Zeta One issues
and binds credentials itself.

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
mandate check. The scheme follows the shape of RFC 9421 HTTP message signatures but is not claimed
to be compliant.

Automation-detection signals (Botscent-style) are not implemented; the evidence record has a slot
for them as risk signals.

### Mandate

One active mandate per `(business_id, agent_id)`, a JSON document stored by the gateway:

| Field | Meaning |
| --- | --- |
| `mandate_id`, `version`, `policy_version` | identity and provenance |
| `granted_by`, `granted_at`, `expires_at`, `status`, `revoked_at` | lifecycle; `status` is `active` or `revoked` |
| `actions` | allowed actions, e.g. `["propose_payment"]` |
| `source_accounts` | Rho account ids the agent may pay from |
| `payment_method_types` | subset of `ach, wire, check, international` |
| `counterparties` | `{"mode": "any" \| "allowlist" \| "denylist", "ids": [...]}` |
| `allow_new_counterparties` | may pay a counterparty with no settled history |
| `limits.per_payment` | max amount per proposal |
| `limits.rolling` | `{"window_days": 30, "amount": ...}` cumulative over executed and pending proposals |
| `human_approval_above` | amount above which an otherwise-clean proposal is challenged for human approval |

Every field is checked in code; the result is a list of violations, each naming the field, the
limit and the observed value. Any violation blocks. The mandate as stored is copied into the evidence
record.

Signing the mandate with the grantor's key is a stretch; the hackathon build stores it unsigned and
says so.

## Alternatives

- **Bearer API keys per agent:** simpler, but a leaked key is indistinguishable from the agent, and
  there's no replay protection. Signatures cost little more.
- **OAuth-style delegated tokens / verifiable credentials:** the right long-term shape; too much
  infrastructure for two days and nothing on the Rho side consumes them.
- **Mandate as policy code (OPA/Cedar):** expressive, but a JSON document is easier to show in the
  UI and to copy into the evidence record.

## Consequences

- Revocation is immediate: flipping `status` on the agent or the mandate blocks the next request.
- The demo's "unknown agent", "revoked agent" and "replay" scenarios need no risk model at all,
  which shows the layering.
- A second agent delegating to a third is out of scope; the mandate binds one agent.
