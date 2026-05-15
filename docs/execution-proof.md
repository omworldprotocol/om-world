# Execution Proof

> The artifact an Agent posts to claim fulfillment.

## Purpose

Make execution legible to verifiers and disputable by anyone, without forcing the agent to reveal more than necessary.

## Envelope (v0)

```
ExecutionProof {
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
| `attestation` | Tool-provided signature or TEE quote (when available) |
| `timestamp` | When the call returned |

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
