# Execution Proof

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one records execution outcomes as JSON in the `executions` table (`output_json` + `trace_json`) — there are no cryptographic attestations, no on-chain anchors, no zkTLS, and no key revocation states implemented yet. The cryptographic primitives below are the long-term target. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

> The artifact an Agent posts to claim fulfillment.

## Purpose

Make execution legible to verifiers and disputable by anyone, without forcing the agent to reveal more than necessary.

## Threat model

The Execution Proof envelope records **what** was claimed and **when**, signed by a key with a known revocation state. It deliberately does *not* claim **runtime honesty** — the property that the agent's internal reasoning, prompts, or tool-call decisions inside the runtime were truthful representations of what the agent actually computed.

What the envelope does claim:
- The bytes inside this envelope were signed by a key paired with the declared agent identity at the declared time
- The signing key's revocation state at proof-validation time matches the rule applied (see [§Key revocation states](#key-revocation-states))
- The plan revealed matches the mandate's `plan_hash` commitment
- Each step's attestation, where present, is internally consistent
- The chained `prev_hash` (when used) is unbroken

What the envelope deliberately does *not* claim:
- That the agent's internal decisions were honest (use a TEE-attested runtime for that, composed underneath the envelope)
- That a stateful tool's snapshot at `context_hash` reflects ground truth — only that the snapshot was committed to before the query ran
- That the runtime was not coerced, prompt-injected, or otherwise manipulated upstream of the signing surface — runtime-honesty disputes are handled through optimistic challenge windows, not through cryptographic attestation alone

Runtime honesty composes cleanly underneath this envelope: a TEE-attested runtime can wrap the signing key, an optimistic-challenge protocol can run above the settlement layer, and the envelope itself remains unchanged in either direction. This separation is intentional — coupling runtime-honesty into the proof envelope would force every relying party to trust whichever runtime substrate the agent chose, which defeats the multi-decade verifier-viability goal.

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

**Retrieval is three layers, not one snapshot.** For embedding/vector retrieval specifically, a snapshot hash over *only* the corpus is insufficient if the retrieval *procedure* can change. A complete `context_hash` for a retrieval step must cover three layers, so a verifier knows it is replaying the same corpus **and** the same retrieval policy:

1. **Corpus state** — which knowledge assets existed at time T (the snapshot hash above).
2. **Retrieval procedure** — embedding model + version, query transform, filters, `top_k`, score function. A change here produces different results from an identical corpus.
3. **Returned evidence** — asset IDs, scores/ranks, and any extracted subgraph/triples used downstream (the `output_hash` above).

When all three are bound, a dispute between two agents claiming X vs. Y reduces cleanly to one of: different corpus root, different retrieval policy, nondeterministic ranking, or a false claim about the returned assets — each of which is independently checkable. Folding the retrieval procedure into the attested context is what makes layer (2) disputes detectable rather than silent. (This three-layer decomposition was raised on [OriginTrail/dkg#539](https://github.com/OriginTrail/dkg/issues/539) in the context of decentralized-knowledge-graph retrieval.)

### prev_hash — chained proof mode

By default, steps form a flat sequence: all steps must be replayed to dispute any one. When per-step dispute localization is needed, steps may be linked via `prev_hash`:

- Each step's canonical record includes the prior step's full step hash as `prev_hash`.
- The first step sets `prev_hash` to the mandate's `plan_hash` — the value **pre-committed in the intent record before execution begins**, not a hash computed by the agent at proof time. This binds the chain to what was authorized; a compromised agent that swapped the plan post-hoc cannot produce a valid-looking chain anchored to the original `plan_hash`.
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

**Absent optional fields are excluded from the JCS input** — a missing `context_hash` or `attestation` field MUST NOT be serialized as `null` in the canonical record. Implementations that disagree on `null` vs. omit will produce divergent hashes from identical step data, breaking interoperability before any signature is even checked.

**`context_hash` is binary: absent, or present-with-a-real-hash.** The field is **absent** when the tool's output is fully determined by its inputs (a pure function or stateless transform). It is **present** when the output depends on external state — a database read, a live fetch, or prior session state not captured in `prev_hash`. The cases `"context_hash": ""` (empty string) and `"context_hash": "sha256:0000…0000"` (empty hash) are **not** valid encodings: if the field appears in the JCS input, it must carry a hash of something real.

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

**Pre-commitment of the signing key.** The verifier's correctness rests on the signing key being **committed to a registry before** the proof is generated, not after. This is what makes claims about the runtime substrate (TEE, sandbox, bare metal) irrelevant to verification: even if substrate-attestation is fully delegated to a third-party broker, an agent that signs with a non-registered key has its proof rejected at item 4; an agent that signs with a registered key cannot retroactively claim a different key was the "real" one. The economic bet collapses to ECDSA (or whatever signature scheme the registered identity uses) — forging a proof requires the private key. This is why the spec is comfortable leaving substrate selection to the deployment while still claiming verifier-level correctness.

**Conditional load-bearing on externally-attested agent identity.** Item 4 is **conditionally required** depending on deployment context. Externally-attested `executor.agent_id` is load-bearing when the deployment admits a solver market, runs an adversarial bond/dispute layer, or otherwise requires the principal to identify, bond, and dispute against a counterparty they do not control. It is **optional** when the deployment is single-account / single-runtime / single-trust-domain — for example, a developer running an agent locally against their own credentials, with no competing pool of agents bidding to execute and no slashable bond. In that mode, `executor.agent_id` may be a routing string (which adapter to dispatch to) rather than a cryptographic principal, and identity is the OS-user plus optionally a workflow-level attestation. Verifiers in such deployments still apply items 1–3 and 5–8 verbatim; item 4 reduces to an existence check rather than a registry resolution. The two questions — externally-attested agent identity and on-chain settlement — collapse to the same trigger: both become load-bearing the moment the deployment admits adversarial counterparties.

## On-chain verification

The spec is intentionally agnostic between three verification paths a relying party may use:

1. **Off-chain verification** — a relying party (settlement orchestrator, dispute challenger, auditor) runs the verifier locally. JCS canonicalization plus the signature scheme work in any language that has a reference implementation.
2. **On-chain native verification** — direct on-chain signature verification, viable where the chain offers a suitable precompile (Solana for Ed25519; certain EVM L2s for secp256r1 via RIP-7212). Native EVM Ed25519 currently lacks a stable precompile; ZK-friendly Ed25519 (the EIP-665 successor work, Poseidon-over-Ed25519 circuits) is the longer-term path.
3. **Relayer-attested on-chain** — a relayer (or a committee) verifies the proof off-chain and posts an on-chain attestation that the settlement contract can check cheaply.

**Rule (relayer-attested path):** The relayer's attestation MUST commit to the exact bytes of the JCS-canonicalized payload it verified, not to a re-hash or a derived digest. Otherwise a malicious relayer could attest "I verified something that hashes to X" and the dispute path would be unable to reconstruct what was actually shown to the verifier. The relayer's attestation itself MUST be cryptographically attributable to a stable relayer identity so that a successful challenge can slash the relayer, not just the agent.

**Rule (verifier independence):** The trust root for verifying any execution proof MUST be the deterministic open-source verifier + the versioned schemas + the exported evidence bytes. Hosted indices, APIs, or convenience services run by the protocol or any single operator are an acceptable convenience layer for discovery, slicing, and retrieval — but verification correctness MUST NOT depend on trusting them. A third-party auditor receiving a complete export must be able to verify it offline, including chain continuity, signatures and anchors where present, schema version, and the location of any verification failure. This rule protects the dispute path from a class of failure where a hosted API silently substitutes a different payload than what was actually anchored.

The choice of path is a deployment decision. Any on-chain settlement built on top of this spec MUST express its verification path back to the canonical JCS + signature primitives so that disputes can be replayed under any of the three modes.

## Disputes

The dispute layer is decomposed into three deliberately-separate mechanisms. Conflating them produces a class of failure where reputation swings on disputes and becomes manipulable.

**1. Hard enforcement at proof submission (binary, automatic, pre-dispute).** A proof whose signature does not recover to the agent identity committed in `intent.executor` (or, where executor is unbound, the signing identity claimed in the proof itself) MUST be rejected at submission time. The honest path and the malicious-attempt path are indistinguishable to downstream consumers because the malicious attempt never lands. This is the verifier's job (see [§Verifier responsibilities](#verifier-responsibilities)), not the dispute layer's.

**2. Reputation accumulation (signal, monotonic).** Reputation MUST be increment-only on successful settlement. It MUST NOT decrement on dispute resolution. A slashed agent retains their historical settled-jobs count; what they lose is bond and the right to take new jobs until the bond is restored. The rationale is sybil-resistance: reputation that swings on disputes can be manipulated by a coordinated griefing campaign, but reputation that swings only on settlements is bounded by the buyer-volume curve of the deployment.

**3. Bond slashing (post-settlement, adversarial).** Anyone may post a challenge during the dispute window. The challenger posts a dispute bond (anti-griefing). Resolution is objective wherever possible — a successful challenge slashes the agent's bond proportionally to the severity:

| Class | Slash |
|---|---|
| Fabricated step | 100% |
| Tool misuse / unattested call | 50% |
| Plan/mandate mismatch | 25% |
| Latency / minor protocol breach | ≤10% |

The slash is a **funding event, not a reputation event**: bond redistribution follows the severity table; the agent's reputation score is not retroactively altered. Subjective output-quality judgments are out-of-scope for the slashing rule (subjective quality is the reputation accumulator's signal, not bond slashing's).

This three-mechanism decomposition is independent of whether the deployment is on-chain or off-chain. On-chain deployments express each mechanism as a contract surface (e.g. `AttestationVerifier` for #1, a reputation vault for #2, a slashing arbiter for #3); off-chain deployments express the same three concerns as discrete relying-party checks. The spec only requires that the three concerns remain separable.

## Privacy

Proofs may include sealed fields decryptable only by the principal. Public verifiers check structural integrity; semantic verification happens under the principal's key.

## Deletion evidence (commit-then-redact)

An append-only proof envelope sits in tension with deletion regimes such as GDPR right-to-erasure: once raw PII enters an immutable chain, "deleting" it requires either breaking the chain or breaking the regulation. The spec resolves this by **commit-then-redact**, a profile under which deletion is itself an attestable event without invalidating chain continuity:

1. **Minimize PII before ingest.** Raw PII MUST NOT be written into the append-only envelope by default. The envelope carries commitments (hashes, encrypted sealed fields, or zero-knowledge claims) rather than raw personal data.
2. **Keep raw / deletable material in a controller-owned sidecar store**, outside the proof envelope. The sidecar is the only place from which deletion can be effected.
3. **On a verified deletion request,** destroy or redact the sidecar material AND append a **deletion-evidence event** to the envelope chain. The deletion event records what was deleted (by commitment, not by raw content), under whose request, at what time, with what authority — and is itself signed and chained like any other step record.
4. **The envelope's append-only property is preserved.** A verifier reconstructing the chain after deletion sees a coherent history that includes the deletion event; it cannot reconstruct the deleted raw material, but it can verify that the deletion happened, was authorized, and did not retroactively alter earlier records.

This is a **profile**, not a compliance certification. It provides an evidence substrate that supports GDPR / data-minimization regimes, but legal sufficiency for any specific regulator depends on controller-specific review of the full deployment context (sidecar storage choice, key management, redaction completeness).

## Open questions

- Zero-knowledge proofs for sensitive tool inputs.
- Cross-domain attestation (off-chain APIs without native signing): zkTLS covers HTTP response proofs; TEE covers agent execution proofs. A hybrid (`attestation.type: multi`) likely covers most cases — formalize the combination rules.
- Memory snapshot distribution: who is responsible for storing and serving the snapshot that `context_hash` commits to? Options: the memory tool provider, a dedicated snapshot oracle, or the agent itself (with provider co-signature).
- **Cross-chain proof aggregation.** When an intent originates on chain A (e.g. Base) and the agent executes against tools or settlement on chain B (e.g. Solana), the proof must be verifiable on the originating chain without forcing the originating chain to natively parse the foreign chain's transactions. Two candidate shapes: (a) **a new primitive** — a `proof_relay_contract` field in the Intent Schema that lets the principal declare the relay path at intent issuance, or (b) **a deployment pattern** — handled outside the spec by relayer attestation, with the spec only requiring that the relayer's attestation commit to exact JCS bytes and be cryptographically attributable (see [§On-chain verification](#on-chain-verification)). Current lean is (b) for v0.2 — relayer attestation handles the single- or homogeneous-relayer path cleanly. (a), the `proof_relay_contract` primitive, is **reserved for v0.3 and scoped specifically to the heterogeneous-relayer case**: when an intent's relay path crosses chains served by *different* relayers, (b) would collapse the originating chain's trust onto the weakest relayer in the path, and a principal-declared relay path is what bounds that trust assumption at intent issuance. (Trigger-condition refinement contributed by @kawacukennedy, Genesis Co-author of the Intent Schema.) Further pushback welcome before the freeze.

- **Config-injected stateless tools.** Tools that are otherwise pure but read external configuration at startup — environment variables, feature flags, per-tenant settings — depend on state that is neither per-invocation input (so not in `input_hash`) nor prior step output (so not in `prev_hash`). Three candidate placements: (a) fold the configuration commitment into `context_hash`; (b) introduce a separate `env_hash` field at step level; (c) declare the boundary out of scope and require the agent's signing key to cover the configuration via a separate signed attestation outside the step record. **Current lean for v0.2: (c) — explicitly out-of-scope at step level**, with a one-line marker in §Step record so the boundary is visible. A composability test vector exercising a "config-injected stateless tool" case will be added to the proof-spec composability PR to surface implementation disagreements before they diverge. (Raised by the `ark-forge/proof-spec` reviewer; promote to (a) or (b) only if v0.2 implementations report it as a real friction point.) **Reference shape for (c):** Compliance Receipts v0.1 attaches an `env_attestation` signed by the *provisioner*, not the executing agent — configuration provenance lives at the session envelope, keeping step-level hashing clean and bounded. This is the recommended concrete instantiation of the out-of-scope-at-step-level path.
- **Parallel step execution.** The `prev_hash` chain in [§Step record](#step-record) is linear and assumes sequential steps. Parallel tool invocations — fan-out followed by join — do not fit this shape. A Merkle root over the set of step hashes produced in parallel handles the case: the same per-step canonicalization rules apply, only the composition into the next step's `prev_hash` changes (from "previous step's hash" to "root of parallel-set step hashes"). **Out of scope for v0.2** — flagged as a v0.3+ fork point so implementations don't quietly invent incompatible Merkle compositions when they hit the case. **Sort order must be pinned before the Merkle composition is specified piecemeal:** the reference shape is `MerkleRoot(lexicographic_sort(step_hashes))` — lexicographic on a deterministic step ID — stated now so parallel implementations don't diverge on leaf ordering (the ambiguity that makes parallelism painful to retrofit). (Both this and the sort-order refinement raised by the `ark-forge/proof-spec` reviewer.)

## Related work

A small but real cluster of agentic-commerce and agent-execution specs is converging on **JCS (RFC 8785) + key-rooted signatures + RFC 3161 timestamping** as the canonical-form + verifiability stack, with **runtime-honesty deliberately separated from the proof envelope**. Known instances at the time of writing:

- [Trusteedxyz/Trust-Receipt-Verifier](https://github.com/Trusteedxyz/Trust-Receipt-Verifier) — JWS Compact + JCS + Ed25519 for trust receipts in agentic commerce
- [Tyche Institute / EATF](https://github.com/tyche-institute/eatf) — key-rooted attestation with hybrid PQC (RSA-4096 / ECDSA-P256 / ML-DSA-65), JCS canonicalization, RFC 3161 timestamps, and an externally-mirrored key history (reference mirror at `tyche-institute/eatf-trust-anchors`). Multi-decade-verifier-viability framing; runtime-honesty explicitly out-of-scope of the envelope, composable underneath via TEE if needed.
- [Occasio Labs / occasio](https://github.com/occasiolabs/occasio) — audit-only end of the cluster. In-toto Statement over a JSONL hash-chain, RFC 8785-subset canonicalization (with documented deviations and integer-only numbers), mirrored JS and Python verifiers, DSSE-wrapped, Sigstore keyless via GitHub Actions OIDC, Rekor inclusion proof in CI. The economic/settlement axis is intentionally absent — a clean reference for the audit/economic decoupling pattern.
- [winsznx/pact](https://github.com/winsznx/pact) — deployed on-chain execution-attestation verifier (0G mainnet). Pre-registered signing-address commitment + EIP-191-signed 5-field canonical text (`contentHash:usageHash:providerType:providerIdentity:tlsCertFingerprint`) + `AttestationVerifier.sol` running `ECDSA.recover` at submission time. Three-mechanism dispute decomposition (hard enforcement / reputation accumulator / bond slashing) shaped [§Disputes](#disputes) in this spec. PACT's `AttestationVerifier` can verify an OM World Execution Proof as-is when the proof's canonical-text shape matches and is EIP-191-signed against a key registered in PACT's `PactRegistry` — a useful interop surface for deployments that want to settle on 0G.
- [ark-forge/proof-spec](https://github.com/ark-forge/proof-spec) — Compliance Receipts v0.1, an open spec for verifiable agent-to-agent execution proofs. `previous_receipt_hash` in CR v0.1 is structurally equivalent to `prev_hash` in this spec's Step record — same role, same anchoring pattern; `step.timestamp` (ISO 8601 UTC) maps directly. OM World's chained proof mode composes with the CR v0.1 pipeline format **without additional fields**. Composability confirmed by the maintainer ([@desiorac](https://github.com/desiorac)), who also shaped the §Canonicalization absent-optional-fields rule and the §Step record `plan_hash` pre-commitment clarification.
- [attestplane/attestplane](https://github.com/attestplane/attestplane) — compliance-and-audit-substrate end of the cluster. **alpha-stage** verifiable audit substrate framed explicitly as an **AIA-12 aligned profile** (Article 12 of the EU AI Act), not a compliance certification: role-bound event fields (provider/deployer/operator/human reviewer), system+model+policy version refs, event categories mapping to high-risk operations (decision / human intervention / exception / drift / audit-export), continuity checkpoints, optional external timestamp anchoring, offline-readable auditor export. Verifier-independence rule (deterministic OSS verifier + versioned schemas + exported bytes as the trust root; hosted APIs as convenience only) and the **commit-then-redact** retention/deletion profile (raw PII in controller-owned sidecar; deletion appended as a signed, chained evidence event) were independently arrived at and align with [§Verifier independence](#on-chain-verification) and [§Deletion evidence](#deletion-evidence-commit-then-redact) in this spec. Attestplane provides evidence-substrate primitives, not a legal compliance conclusion for any deployed high-risk system.
- [aeoess/agent-passport-system](https://github.com/aeoess/agent-passport-system) — Ed25519-rooted delegated-identity stack with a per-action canonical content addressing scheme: action identifier = SHA-256(RFC 8785 JCS canonical form of action tuple), which doubles as the dedup key (a verifier tracking seen identifiers within the relevant window rejects duplicates). Independent convergence on the canonical-form-as-identity rule that this spec adopts in [§Canonicalization](#canonicalization); their 4-field preimage and canonical form are written up in IETF [`draft-pidlisnyi-aps`](https://datatracker.ietf.org/doc/draft-pidlisnyi-aps/). The same project's root-key-issues-scoped-delegations model + monotonic-narrowing-with-covering-predicate invariant shaped [`agent-mandate.md §Identity model`](agent-mandate.md#identity-model--root--delegation-chain) and [`§Scope narrowing`](agent-mandate.md#scope-narrowing--monotonic-invariant--issuancevsruntime-split).
- AP2 v0.2 Verifiable Intent (in development)
- Several wallet-side credential profiles in the broader agent ecosystem

The convergence is independent — no coordination body, just multiple specs picking the same primitives because they avoid the same failure modes: canonicalization drift, signature-suite fragmentation, per-language verifier reimplementation cost, and conflation of audit-grade attestation with runtime-honesty claims. Documenting it explicitly compounds the benefit: relying parties building verifiers can share canonicalization and signature-verification code across the lot, and the audit/economic decoupling pattern (audit envelope on Rekor-class infrastructure, economic settlement separately on-chain when needed) is now visible as a deliberate design axis rather than a quirk.

### Concrete attestation implementations

The following projects provide deployable attestation primitives that compose with the Execution Proof envelope. Each produces a cryptographically attributable payload that can be carried in an Execution Proof step's `attestation` field through a tool adapter without changing the step-record structure.

- **[Reclaim Protocol](https://reclaimprotocol.org)** — zkTLS for HTTP response proofs. A prover generates a zero-knowledge proof of an HTTPS session with a TLS notary; the proof attests to specific response bytes without revealing the full session. Reclaim's `SignedClaim` schema can be embedded in an Execution Proof step via a tool adapter that wraps the Reclaim SDK. Verifier contracts deployed across EVM chains. Integration surface: the JCS-canonicalized step record becomes the Reclaim proof's `context` field, binding the attestation to the specific step in the proof chain.

- **[zkPass](https://zkpass.org)** — zkTLS for HTTPS data verification. Uses multi-party computation (MPC) between three distributed notaries instead of a single notary, eliminating notary-side-channel risk at the cost of higher setup latency. zkPass's `Attestation` schema maps to the Execution Proof envelope's `type: multi` attestation pattern. Verifier contracts deployed on Ethereum and Arbitrum. Transpiler support for schema-free HTTPS data — any JSON API response can be attested without server-side changes.

- **[Phala Network](https://phala.network)** — TEE attestation runtime via Intel SGX. Phala's `pRFC` (Phala Remote Attestation Framework) produces SGX quotes that attest to specific code execution within an enclave. The Execution Proof's `context_hash` primitive matches Phala's stateful execution model naturally — `context_hash` serves as the enclave-memory commitment. Phala's `Orakl` verifier validates SGX quotes on-chain, enabling the relayer-attested on-chain verification path. An OMW agent running in a Phala TEE can sign step records with a key whose attestation chain terminates in an SGX quote rather than an external KMS, collapsing the runtime-honesty question into the attestation itself.

- **[Marlin (Oyster)](https://marlin.org/oyster)** — TEE attestation via Intel SGX and AMD SEV-SNP. Oyster produces signed attestation statements (`AttestationDocument`) that can be verified on-chain through Marlin's `AttestationVerifier`. Oyster's `AttestationDocument` format can be carried in the Execution Proof step's `attestation` bytes, with the verifier calling Marlin's on-chain verifier to validate the quote at settlement time. Marlin's `Oyster` SDK provides `getAttestation()` and `verifyAttestation()` primitives that an OMW tool adapter can call directly.

- **[Step-record chaining — `certificate.ts`](https://github.com/omworldprotocol/om-world/blob/main/packages/protocol/certificate.ts)** — reference implementation of step-record hashing, `prev_hash` computation, and JCS canonicalization. `createCertificateChain()` and `verifyCertificateChain()` demonstrate the exact byte-level processing a verifier must implement, including the null-vs-omit rule for absent optional fields. Any zkTLS or TEE attestation adapter should produce signatures over the same JCS-canonicalized payload that `certificate.ts` produces, guaranteeing verifier reuse across attestation substrates. New implementation ports (Rust, Python, Solidity) should target this function as the conformance baseline.

If you ship a spec or implementation in this cluster and want to be listed here, open an issue tagged `genesis-builders` on the [om-world repo](https://github.com/omworldprotocol/om-world/issues).

## Contributors

This spec was shaped by — see [CONTRIBUTORS.md](../CONTRIBUTORS.md#execution-proof) for current attribution:

- **[@Trusteedxyz](https://github.com/Trusteedxyz)** — Genesis Reviewer of Execution Proof. Shaped §Canonicalization (JCS RFC 8785), §Long-term verifiability (RFC 3161 sidecar), §Key revocation states (rotated vs compromised), the envelope-is-the-unit non-goal in §Envelope, the relayer-bytes-commitment rule in §On-chain verification, and the §Related work convergence note across multiple rounds of design dialogue.
- **Tyche Institute** (maintainer of the [EATF](https://github.com/tyche-institute/eatf) research project) — Genesis Reviewer of Execution Proof (institutional attribution). Shaped §Threat model (runtime-honesty as an explicit out-of-scope property of the envelope) and the cross-spec convergence framing in §Related work (key-rooted + key-history-mirror as a complementary axis to the JCS/JWS stack). Posture: technical review only; not an endorsement of OM World governance, business model, or any future commercial state.
- **attestplane project** (maintained by [@merchloubna70-dot](https://github.com/merchloubna70-dot)) — Genesis Reviewer of Execution Proof (institutional attribution). Shaped the verifier-independence rule in §On-chain verification, the §Deletion evidence (commit-then-redact) section, and the compliance-and-audit-substrate corner of the §Related work cluster. Posture: spec-level convergence only; not an endorsement of OM World governance, business model, or any future commercial state.
- **ark-forge/proof-spec** (Compliance Receipts v0.1, maintained by [@desiorac](https://github.com/desiorac)) — Genesis Reviewer of Execution Proof (institutional attribution). Shaped the §Canonicalization absent-optional-fields rule (null vs. omit) and the `context_hash` binary-presence rule (absent for pure/stateless tools, present-with-a-real-hash for stateful, no empty-string/empty-hash encodings); the §Step record `plan_hash` pre-commitment clarification (intent-record value, not agent-computed at proof time); the §Related work composability note for Compliance Receipts v0.1 (`previous_receipt_hash` ≡ `prev_hash`); and the §Open questions entries on config-injected stateless tools (`env_hash` boundary) and parallel step execution (Merkle root). Posture: spec-level convergence only; not an endorsement of OM World governance, business model, or any future commercial state.
