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
| `executor` | object | no | Agent identity commitment (see below) |
| `attestation` | object | no | Expected proof format for settlement (see below) |
| `on_expire` | string\|object | no | Behaviour when `expires_at` passes without fulfillment (see below) |
| `nonce` | uint | yes | Replay protection |
| `issued_at` | timestamp | yes | RFC3339 |
| `expires_at` | timestamp | no | RFC3339 |
| `signature` | sig | yes | Over the canonical hash |

## executor

Binds an authorized agent identity to the intent, so that execution proofs can be attributed to a specific, verifiable actor rather than any agent holding a valid mandate.

```json
"executor": {
  "agent_id": "0xabc...def",
  "id_scheme": "erc-8004",
  "commitment": "<agent-signed hash of intent_id + agent_id>"
}
```

| Sub-field | Description |
|---|---|
| `agent_id` | The agent's on-chain identity hash (ERC-8004 or equivalent) |
| `id_scheme` | Identity standard used: `erc-8004` \| `did` \| `pubkey` |
| `commitment` | Agent's own signature over `intent_id + agent_id`, proving it accepted responsibility |

**Binding models:**
- *Creation-time binding* — the principal pre-selects which agent identity will execute. Simpler, but breaks if that agent goes offline.
- *Activation-time binding* — the agent signs its own identity into the intent before submitting to a solver. More composable; requires a second signature step.

If `executor` is omitted, any agent holding a valid mandate may execute. When present, the mandate and execution proof must originate from the same identity.

## attestation

Declares the proof format the principal considers acceptable evidence of settlement. Without this field the solver chooses the proof format; with it, the principal defines the verification standard up front.

```json
"attestation": {
  "type": "zktls",
  "scheme": "tlsn-v1",
  "verifier": "0x..."
}
```

| Sub-field | Description |
|---|---|
| `type` | `zktls` \| `tee` \| `onchain_tx` \| `signed_log` \| `multi` |
| `scheme` | Specific implementation: `tlsn-v1`, `nitro-enclave`, `sp1`, … |
| `verifier` | Address or URL of the contract or endpoint that validates this proof type |

`type: multi` carries an array of acceptable types; the agent must satisfy at least one.

> **Note:** zkTLS proves external data state (e.g., an API response at a point in time). TEE proves agent execution correctness. For intents requiring both — e.g., a financial execution that needs an oracle price proof (zkTLS) and an agent execution trace (TEE) — use `type: multi`.

## on_expire

Defines what happens when `expires_at` passes and the intent has not reached PROVEN state.

```json
"on_expire": "cancel"
```

```json
"on_expire": {
  "action": "escalate",
  "notify": "0x..."
}
```

| Value | Behaviour |
|---|---|
| `"cancel"` | Intent moves to CANCELLED; matched mandate released; bond partially forfeited per [agent-mandate.md §Cancellation](agent-mandate.md) |
| `"revert"` | Like `cancel`, but additionally triggers any rollback artifacts declared in the execution proof |
| `"escalate"` | Sends a notification to `notify` for human review before finalising state |

Default when field is omitted: `"cancel"`.

## Canonicalization

TBD — describe the deterministic serialization used for hashing.

## Examples

```json
{
  "id": "01HZ…",
  "principal": "0x1234…",
  "body": "Find me the cheapest direct flight from SFO to Tokyo next Tuesday.",
  "constraints": { "budget_usd": 1200, "deadline": "2026-06-01T00:00:00Z" },
  "success_criteria": { "booked_pnr": true },
  "executor": {
    "agent_id": "0xabc…def",
    "id_scheme": "erc-8004",
    "commitment": "0xsig…"
  },
  "attestation": {
    "type": "zktls",
    "scheme": "tlsn-v1",
    "verifier": "0xverif…"
  },
  "on_expire": "cancel",
  "nonce": 1,
  "issued_at": "2026-05-15T00:00:00Z",
  "expires_at": "2026-05-16T00:00:00Z",
  "signature": "0xsig…"
}
```

## Open questions

- How to express partial fulfillment?
- How to bind to non-fungible context (e.g., a specific email thread)?
- Activation-time vs creation-time executor binding: which should be the default?
- Should `attestation.type: multi` require ALL types or satisfy ANY one?
