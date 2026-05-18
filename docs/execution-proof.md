# Execution Proof

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one records execution outcomes as JSON in the `executions` table (`output_json` + `trace_json`) — there are no cryptographic attestations, no on-chain anchors, no zkTLS, and no key revocation states implemented yet. The cryptographic primitives below are the long-term target. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

> The artifact an Agent posts to claim fulfillment.

## Purpose

Make execution legible to verifiers and disputable by anyone, without forcing the agent to reveal more than necessary.

## Envelope (v0)

```
ExecutionProof {
  spec_version  // e.g. "0" — verifiers must reject unknown versions, not downgrade
  intent_id
  mandate_id
  plan          // revealing the pre-committed plan_hash
  steps[]       // ordered tool invocations with inputs, outputs, attestations
  artifacts[]   // hashes / pointers to externally verifiable outputs
  success_claim // structured against intent.success_criteria
  signature
}
```

> **Aggregate envelope, not streaming.** One ExecutionProof represents one intent's complete fulfillment — all step records, artifacts, and the success claim are inside a single signed object. The agent does not emit multiple envelopes per intent. Per-step dispute localization is achieved through `prev_hash` chaining inside the single envelope (see Step record below), not through multiple envelopes. This keeps the proof bundle as a single point of attribution and a single signature surface.
>
> **The envelope is the unit; slicing is undefined behavior.** A consumer that wants only "the last N steps" of a long fulfillment MUST NOT truncate the envelope — doing so breaks the `prev_hash` chain and silently invalidates the proof under any honest verifier. If a relying party needs a partial view, it receives the full envelope and projects locally. Forwarding sub-receipts derived from a slice is unsupported and any verifier consuming such a slice should reject it.
>
> If a streaming / observability profile is later added, it MUST be an out-of-band channel mirroring the aggregate, not replacing it — settlement always references the aggregate envelope as the single accountability surface.

## Step record

| Field | Description |
|---|---|
| `tool_id` | Registered tool identifier |
| `input_hash` | Hash of canonicalized input |
| `output_hash` | Hash of returned output |
| `context_hash` | Hash of the tool's stateful context at call time (required for stateful tools; see below) |
| `attestation` | Tool-provided signature or TEE quote (when available) |
| `timestamp` | When the call returned |
| `prev_hash` | Hash of the preceding step's canonical record (optional; required in chained proof mode — see below) |

### context_hash — stateful tool attestation

For stateless tools (HTTP APIs, deterministic functions), `context_hash` may be omitted: the same `input_hash` always produces the same `output_hash`, so any verifier can reproduce the call.

For **stateful tools** — primarily memory stores — the same query against a different store state produces a different result. To enable dispute-grade replay, the step must include:

- `input_hash` — hash of (query embedding + similarity threshold used).
- `output_hash` — hash of (ranked result set with scores, in canonical order).
- `context_hash` — snapshot hash of the memory store at the moment the query executed, taken *before* any consolidation runs on that snapshot.

A verifier holding the snapshot can independently reproduce the retrieval and verify that the agent saw exactly the results claimed. Without `context_hash`, memory retrieval steps are unverifiable if the store has since been consolidated or modified.

**Rule:** Any step invoking a tool with `operation_class: read` against a stateful backend (as declared in the Tool Registry) MUST include `context_hash`. Steps missing `context_hash` for stateful tool calls are treated as unattested.

### prev_hash — chained proof mode

By default, steps form a flat sequence: all steps must be replayed to dispute any one. When per-step dispute localization is needed, steps may be linked via `prev_hash`:

- Each step's canonical record includes the prior step's full step hash as `prev_hash`.
- The first step sets `prev_hash` to the mandate's `plan_hash`, anchoring the chain to the pre-committed plan.
- Any verifier holding step N and step N-1 can verify the link independently, without replaying the full trace.
- A challenger may dispute step N specifically by submitting only steps N-1 and N as evidence.

`prev_hash` is optional but recommended for multi-step pipelines where localized disputes are expected. When present in any step, all subsequent steps in the same proof MUST also include `prev_hash` (partial chaining is not valid).

### Spec version handling

Verifiers MUST read `spec_version` before evaluating any proof. If the version is unknown:

- Reject with `UNSUPPORTED_SPEC_VERSION` — do not silently downgrade to an older verification formula.
- Silent downgrade is a security anti-pattern: a tampered proof could claim an older `spec_version` to be evaluated against looser or preimage-vulnerable logic.
- Pattern: read `spec_version` → route to a version-specific verifier module → surface the error explicitly if no module exists.

## Canonicalization

All hashing operations in this spec — `prev_hash` linkage, step record hashing, envelope hashing for `signature` — use the same **JCS (JSON Canonicalization Scheme, [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785))** canonicalization defined in [intent-schema.md §Canonicalization](intent-schema.md#canonicalization).

A step's hash for `prev_hash` linkage is computed as:

```
step_hash = SHA-256(JCS(step_record_without_prev_hash))
```

The `prev_hash` field is excluded from its own step's hash input so the field can *contain* the previous step's hash without circular dependency. Step records are otherwise hashed including all present fields.

The proof envelope's `signature` is computed over `SHA-256(JCS(envelope_without_signature))` using the agent's signing key (the key materially bound to `intent.executor.agent_id`).

## Long-term verifiability

A signed proof remains verifiable only while the agent's signing key is still trusted. For receipts that need to remain verifiable across key rotation or compromise events (months to years after issuance), the proof MAY carry an [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161) timestamp sidecar countersigning the proof's signature input.

The timestamp is **not** part of the canonical envelope — it is attached alongside the proof — so it can be added or refreshed without invalidating the original signature. A verifier evaluating an old proof checks:

1. The agent's signing key was in a valid state at the time the RFC 3161 timestamp was issued (per the identity registry's key-state history).
2. The timestamp was issued by a Time Stamping Authority the verifier trusts.

If both hold, the proof remains verifiable even after the agent's signing key is rotated or revoked.

**Rule:** Proofs whose signing key has moved to *compromised* status (see [Key revocation states](#key-revocation-states) below) MUST present a valid RFC 3161 timestamp predating the compromise event in order to remain verifiable. Proofs whose signing key has merely been *rotated* in normal course do not require a timestamp sidecar.

## Key revocation states

A signing key referenced by `intent.executor.agent_id` is in exactly one of three states from a verifier's perspective:

| State | Meaning | Verifier action |
|---|---|---|
| **Active** | Currently authorized to sign proofs | Accept signatures |
| **Rotated** | Retired in normal course | Accept signatures issued during the key's validity window |
| **Compromised** | Retired due to compromise | Accept signatures only with an RFC 3161 timestamp predating the compromise event |

The identity registry (whichever the `intent.executor.id_scheme` points to — ERC-8004, DID method, pubkey + revocation registry) maintains key-state transitions with effective dates. Verifiers MUST consult the registry's state at proof-validation time, not at proof-creation time, so that a compromise event that surfaces later still flows through to verdicts on old proofs.

## Verifier responsibilities

1. Read `spec_version` and route to the matching verifier module; reject with `UNSUPPORTED_SPEC_VERSION` if no module exists.
2. Re-check the plan hash matches the mandate's commitment.
3. Validate each step's attestation against the tool registry.
4. If `intent.executor` is set, verify that the proof's `signature` originates from the same agent identity (`executor.agent_id`). A proof signed by a different agent identity than the one committed in the intent must be rejected.
5. Consult the identity registry for the signing key's revocation state (see [Key revocation states](#key-revocation-states)) and apply the state-specific acceptance rule.
6. If `intent.attestation` is set, verify that the proof's attestation type and scheme match what the principal declared. A proof using an attestation type not listed in `intent.attestation` must be rejected.
7. Evaluate `success_claim` against the intent's `success_criteria`.
8. Emit verdict event.

## On-chain verification

The spec is intentionally agnostic between three verification paths a relying party may use:

1. **Off-chain verification** — a relying party (settlement orchestrator, dispute challenger, auditor) runs the verifier locally. JCS canonicalization plus the signature scheme work in any language that has a reference implementation.
2. **On-chain native verification** — direct on-chain signature verification, viable where the chain offers a suitable precompile (Solana for Ed25519; certain EVM L2s for secp256r1 via RIP-7212). Native EVM Ed25519 currently lacks a stable precompile; ZK-friendly Ed25519 (the EIP-665 successor work, Poseidon-over-Ed25519 circuits) is the longer-term path.
3. **Relayer-attested on-chain** — a relayer (or a committee) verifies the proof off-chain and posts an on-chain attestation that the settlement contract can check cheaply.

**Rule (relayer-attested path):** The relayer's attestation MUST commit to the exact bytes of the JCS-canonicalized payload it verified, not to a re-hash or a derived digest. Otherwise a malicious relayer could attest "I verified something that hashes to X" and the dispute path would be unable to reconstruct what was actually shown to the verifier. The relayer's attestation itself MUST be cryptographically attributable to a stable relayer identity so that a successful challenge can slash the relayer, not just the agent.

The choice of path is a deployment decision. Any on-chain settlement built on top of this spec MUST express its verification path back to the canonical JCS + signature primitives so that disputes can be replayed under any of the three modes.

## Disputes

Anyone may post a challenge during the dispute window. A successful challenge slashes the agent's bond proportionally to the severity:

| Class | Slash |
|---|---|
| Fabricated step | 100% |
| Tool misuse / unattested call | 50% |
| Plan/mandate mismatch | 25% |
| Latency / minor protocol breach | ≤10% |

## Privacy

Proofs may include sealed fields decryptable only by the principal. Public verifiers check structural integrity; semantic verification happens under the principal's key.

## Open questions

- Zero-knowledge proofs for sensitive tool inputs.
- Cross-domain attestation (off-chain APIs without native signing): zkTLS covers HTTP response proofs; TEE covers agent execution proofs. A hybrid (`attestation.type: multi`) likely covers most cases — formalize the combination rules.
- Memory snapshot distribution: who is responsible for storing and serving the snapshot that `context_hash` commits to? Options: the memory tool provider, a dedicated snapshot oracle, or the agent itself (with provider co-signature).

## Related work

A small but real cluster of agentic-commerce and agent-execution specs is converging on **JCS (RFC 8785) + JWS + Ed25519** as the canonical-form + signature stack. Known instances at the time of writing:

- [Trusteedxyz/Trust-Receipt-Verifier](https://github.com/Trusteedxyz/Trust-Receipt-Verifier) — JWS Compact + JCS + Ed25519 for trust receipts in agentic commerce
- AP2 v0.2 Verifiable Intent (in development)
- Several wallet-side credential profiles in the broader agent ecosystem

The convergence is independent — no coordination body, just multiple specs picking the same primitives because they avoid the same failure modes: canonicalization drift, signature-suite fragmentation, per-language verifier reimplementation cost. Documenting it explicitly compounds the benefit: relying parties building verifiers can share canonicalization and signature-verification code across the lot.

If you ship a spec or implementation in this cluster and want to be listed here, open an issue tagged `genesis-builders` on the [om-world repo](https://github.com/omworldprotocol/om-world/issues).

## Contributors

This spec was shaped by — see [CONTRIBUTORS.md](../CONTRIBUTORS.md#execution-proof) for current attribution:

- **[@Trusteedxyz](https://github.com/Trusteedxyz)** — Genesis Reviewer of Execution Proof. Shaped §Canonicalization (JCS RFC 8785), §Long-term verifiability (RFC 3161 sidecar), §Key revocation states (rotated vs compromised), the envelope-is-the-unit non-goal in §Envelope, the relayer-bytes-commitment rule in §On-chain verification, and the §Related work convergence note across multiple rounds of design dialogue.
