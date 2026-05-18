# Intent Schema

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one implements a simplified subset of this design (a form-submitted intent + LLM classification + an `intents` table in SQLite). The cryptographic, lifecycle, and registry primitives below are the long-term target, not the current implementation. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

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
- *Creation-time binding* — the principal pre-selects which agent identity will execute. Simpler, but couples the intent to a known agent before the solver matches, which defeats permissionless solver networks.
- *Activation-time binding* (recommended) — `executor` is absent or null at creation. At claim time the winning agent signs its ERC-8004 identity into the fulfillment bundle submitted by the solver. Proof chain: `principal constraints → solver match → agent activation → execution proof`. The extra signature step is negligible latency (<1 s off-chain ECDSA) and preserves solver permissionlessness.

If `executor` is omitted, any agent holding a valid mandate may execute. When present (creation-time) or once filled in (activation-time), the mandate and execution proof must originate from the same identity.

## attestation

Declares the proof format the principal considers acceptable evidence of settlement. Without this field the solver chooses the proof format; with it, the principal defines the verification standard up front.

Single attestation type:

```json
"attestation": {
  "type": "zktls",
  "scheme": "tlsn-v1",
  "verifier": "0x..."
}
```

Multi-type attestation:

```json
"attestation": {
  "type": ["zktls", "tee"],
  "scheme": "hybrid",
  "verifier": {
    "zktls": "0x TLSNotary verifier address",
    "tee": "0x SGX quote verifier address",
    "fallback": "0x dispute council multisig"
  }
}
```

| Sub-field | Description |
|---|---|
| `type` | `zktls` \| `tee` \| `onchain_tx` \| `signed_log`, or an array for multi-type |
| `scheme` | Specific implementation: `tlsn-v1`, `nitro-enclave`, `sp1`, … |
| `verifier` | Single address (when `type` is a string) or per-dimension map (when `type` is an array). A reserved `fallback` key in the map declares the adjudicator-of-last-resort if the primary verifier is compromised or returns inconclusive results. |

When `type` is an array, the agent must satisfy **ALL** listed types. Each type covers a distinct *attestation dimension* — not redundant coverage of the same claim.

> **Attestation dimensions:** zkTLS proves external data state (e.g., an API response at a point in time). TEE proves agent execution correctness (code ran as declared inside a trusted environment). A financial execution requiring both an oracle price proof (zkTLS) and an agent execution trace (TEE) uses two types, each covering a different dimension. Requiring the same dimension twice is an anti-pattern.
>
> **Why per-dimension verifier map:** The intent must be self-describing so that any party — including dispute challengers and independent auditors — can verify any single dimension without querying external router state. A routing contract that wraps this schema internally is a valid gas optimization at the deployment layer, but the schema itself must surface individual verifier addresses. The one exception is cross-chain proof routing, which is an infrastructure concern below the schema layer.
>
> **Verifier pinning:** The `attestation.verifier` map is hashed into `intent.id` at signing time and is therefore immutable. A solver cannot substitute a different verifier than the one declared by the principal. This guarantees deterministic knowledge of which verifier contract validates which dimension for every party — solver, challenger, auditor — without querying external state.
>
> **Deployment responsibility:** When a verifier contract is upgraded, old intents remain bound to the verifier address they declared. The prior verifier contract must stay operational until all intents referencing it have reached SETTLED or EXPIRED. The 48-hour dispute window on PROVEN state (see [intent-lifecycle.md](intent-lifecycle.md)) bounds this obligation.
>
> **Cross-chain extension (v1):** When verifiers live on different chains, per-dimension entries may be extended with a `chain` field: `{"chain": "base", "address": "0x..."}`. This is deferred to v1; v0 assumes all verifiers are reachable from the same execution context.
>
> **Fallback adjudicator:** A `fallback` key inside `verifier` declares the address that adjudicates if the primary verifier for any dimension is compromised, paused, or returns inconclusive results. Typically a dispute-council multisig or oracle that can independently evaluate the raw proof. The fallback is pinned at intent creation alongside the per-dimension verifiers and inherits the same immutability. Without a `fallback`, a compromised verifier leaves the intent stuck in DISPUTED with no automatic escalation path.
>
> **Compromise response (deployment pattern):** Verifier compromise is handled at two layers, not in the intent schema itself:
>
> - *On-chain VerifierRegistry* — maps `(attestationType, verifierAddress) → status (Active | Paused | Decommissioned)`. A timelocked multisig may `pauseVerifier(...)` for emergency response. The intent's pinned verifier address does not change; instead, the router short-circuits a paused verifier and the intent escalates to its declared `fallback`.
> - *Off-chain signal* — a signed message from the protocol's security council declaring a verifier compromised. Validators and solvers watch for this signal and reject proofs from that verifier immediately, without waiting for the timelock to clear. The on-chain pause follows as the formal record.
>
> The schema's `fallback` field is what makes both layers safe: compromise pauses the primary path but does not block intent resolution.

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

All hashing operations on intent objects in this spec — computing `id`, hashing the intent for the principal's `signature`, hashing for `executor.commitment`, and any downstream hashing performed by verifiers — use **JCS (JSON Canonicalization Scheme, [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785))** over the canonical JSON representation, with the field being signed excluded from its own hash input.

JCS is the canonicalization standard because:

- It is deterministic, specified, and has reference implementations across TypeScript, Python, Java, Go, and Rust — verifiers in any of those runtimes produce identical canonical bytes from identical logical input.
- It avoids the "everyone reinvents canonicalization" trap that has plagued earlier signed-JSON ecosystems.
- It composes cleanly with JWS / JWT / COSE / raw Ed25519 signature schemes that implementations may choose for the signature itself.

The canonical bytes are the SHA-256 input for:

- `id` — `SHA-256(JCS(intent_object_without_id_and_signature))`
- `signature` — over `SHA-256(JCS(intent_object_without_signature))` using the principal's signing key
- `executor.commitment` — over `SHA-256(JCS({"intent_id": id, "agent_id": executor.agent_id}))` using the agent's signing key

Implementations MUST NOT introduce additional canonicalization layers (re-sorting keys after JCS, additional normalization, etc.) — JCS output is the final canonical form.

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
    "type": ["zktls", "tee"],
    "scheme": "hybrid",
    "verifier": {
      "zktls": "0xverif-tlsn…",
      "tee": "0xverif-sgx…",
      "fallback": "0xcouncil-multisig…"
    }
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
- ~~Activation-time vs creation-time executor binding: which should be the default?~~ **Resolved:** activation-time binding is recommended. Creation-time binding couples the intent to a specific agent before solver matching, defeating permissionless solver networks. See `executor` §Binding models above.
- ~~Should `attestation.type: multi` require ALL types or satisfy ANY one?~~ **Resolved:** ALL, structured as a fallback chain by attestation dimension (zkTLS for external data, TEE for agent execution). Not redundant parallel coverage. See `attestation` §type: multi above.
- ~~Should `attestation.verifier` be a single routing-contract address or a per-dimension map?~~ **Resolved:** per-dimension map is the schema default (self-describing, dispute-ready); routing contracts are a valid deployment-layer optimization. See `attestation` above.

## Reference implementations

- **[Kuberna `IVerifierRouter` Solidity interface](https://gist.github.com/kawacukennedy/2c42da7b4a74aff0d83bd40968a77864)** — a reference shape for a verifier-routing contract that satisfies this schema's per-dimension verifier requirement. Maintained by [@kawacukennedy](https://github.com/kawacukennedy) (Kuberna intents SDK) as part of the design dialogue that shaped the `attestation.verifier` map and `fallback` adjudicator field. Implementations may adopt or adapt.

## Contributors

This spec was shaped by — see [CONTRIBUTORS.md](../CONTRIBUTORS.md#intent-schema) for current attribution:

- **[@kawacukennedy](https://github.com/kawacukennedy)** — Genesis Co-author of the Intent Schema. Shaped `executor` binding model, `attestation.type: multi` semantics, per-dimension `attestation.verifier` map, and `attestation.verifier.fallback` adjudicator field across multiple rounds of design dialogue.
