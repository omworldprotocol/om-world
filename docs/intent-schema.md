# Intent Schema

> Draft. The canonical wire format for a user-issued intent.

## Goals

1. Expressive enough to capture real-world requests in natural language.
2. Structured enough to be machine-routable.
3. Signable, hashable, replay-resistant.

## Fields (v0)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | uuid | yes | Globally unique intent id |
| `principal` | address | yes | Issuer (human or org) |
| `body` | string | yes | Natural-language statement |
| `constraints` | object | no | Budget, deadline, jurisdiction, allowed tools |
| `success_criteria` | object | no | Machine- or human-evaluable success spec |
| `nonce` | uint | yes | Replay protection |
| `issued_at` | timestamp | yes | RFC3339 |
| `expires_at` | timestamp | no | RFC3339 |
| `signature` | sig | yes | Over the canonical hash |

## Canonicalization

TBD — describe the deterministic serialization used for hashing.

## Examples

```json
{
  "id": "…",
  "principal": "…",
  "body": "Find me the cheapest direct flight from SFO to Tokyo next Tuesday.",
  "constraints": { "budget_usd": 1200, "deadline": "2026-06-01T00:00:00Z" },
  "success_criteria": { "booked_pnr": true }
}
```

## Open questions

- How to express partial fulfillment?
- How to bind to non-fungible context (e.g., a specific email thread)?
