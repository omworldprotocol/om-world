# Execution Proof

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

## Verifier responsibilities

1. Re-check the plan hash matches the mandate's commitment.
2. Validate each step's attestation against the tool registry.
3. If `intent.executor` is set, verify that the proof's `signature` originates from the same agent identity (`executor.agent_id`). A proof signed by a different agent identity than the one committed in the intent must be rejected.
4. If `intent.attestation` is set, verify that the proof's attestation type and scheme match what the principal declared. A proof using an attestation type not listed in `intent.attestation` must be rejected.
5. Evaluate `success_claim` against the intent's `success_criteria`.
6. Emit verdict event.

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
