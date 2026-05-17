# Agent Mandate

> The contract an Agent posts when it accepts an Intent.

## Purpose

A mandate is a signed commitment from an Agent to attempt fulfillment of a specific Intent under stated conditions. It is the unit of accountability.

## Fields (v0)

| Field | Type | Description |
|---|---|---|
| `intent_id` | uuid | The Intent being accepted |
| `agent` | address | Agent identity (must match `intent.executor.agent_id` when that field is set) |
| `plan_hash` | hash | Commitment to a plan (revealed on proof) |
| `bond` | amount | Slashable stake |
| `fee_quote` | amount | Maximum charge to principal on success |
| `tools_declared` | array | Capability scope tokens the agent reserves the right to use (see below) |
| `deadline` | timestamp | Self-imposed completion target |
| `signature` | sig | Over the canonical hash |

## tools_declared — capability scope tokens

`tools_declared` is an array of capability scope tokens, not tool URI references. Each entry declares *what the agent is permitted to do*, not *which specific endpoint or provider it will use*. The provider URI is a deployment detail resolved at execution time.

A capability scope token contains:

| Sub-field | Description |
|---|---|
| `tool_id` | Registered tool identifier from the Tool Registry |
| `scope` | Permitted operations (e.g., `memory:read`, `memory:write`, `web:search`) |
| `expiry` | When this capability authorization expires (defaults to `mandate.deadline`) |

This keeps the mandate loosely coupled to the execution environment: the same mandate is valid across runtimes, cloud providers, and tool provider rotations, as long as a compliant tool for that capability exists in the registry.

**Provider rotation without mandate reissue.** Because scope tokens declare capability rather than naming a provider, a tool provider can rotate its endpoints, hostnames, or backing infrastructure without the principal needing to re-sign the mandate. The Tool Registry's resolution layer maps the capability to the current provider at invocation time. Implementations may expose this resolution as an `upstreams` mapping returned alongside the mandate at execution time, similar to the pattern in [Garudex-Labs/caracal](https://github.com/Garudex-Labs/caracal/pull/183) where the delegation edge stores capability + optional resource ID while the runtime mandate carries a resolved upstream map.

> **Note:** Provider rotation that materially changes the trust properties of the capability (different jurisdiction, different KYC posture, different operator) is NOT covered by this rule — that is a re-consent event, not a deployment rotation. The boundary between "rotation" and "re-consent" is a deployment-policy question that the registry's `attestation_method` and `boundary` fields are meant to surface.

## Memory binding

When a mandate includes memory tools, the protocol specifies only the minimal interface — not the implementation.

**What the protocol specifies (loosely):**
- *Scope* — what memory namespace(s) the agent may read/write under this mandate.
- *Provenance* — each memory entry must carry creator identity and timestamp.
- *Semantic retrievability* — the agent must be able to retrieve by content query (not only by key).
- *Lifecycle* — memory access authorized by this mandate expires with the mandate.

**What the protocol does NOT specify** (implementation-specific, must not be hardcoded into the spec):
- Consolidation heuristics or schedules.
- Quality-scoring tiers for memory entries.
- Embedding model choice.
- Knowledge-graph schema.

These are intentionally left to the memory tool provider. Baking them into a protocol-level spec would freeze the state of the art and force every implementation to replicate a specific flavor.

## Executor constraint

If the intent carries an `executor` field, the mandate's `agent` address must correspond to the same on-chain identity (`executor.agent_id` under the declared `executor.id_scheme`). A mandate posted by a different agent identity is invalid and must be rejected by verifiers and solvers.

When `intent.executor` is absent, any credentialed agent may post a mandate.

## Bonding

- Bond is locked at MATCHED and released at SETTLED.
- Slashing conditions: see [execution-proof.md](execution-proof.md) §Disputes.

## Plan commitment

The agent commits to a plan *hash* up front, and reveals the plan inside the execution proof. This prevents post-hoc rationalization while preserving plan privacy until execution.

## Cancellation by agent

An agent may cancel before IN_FLIGHT by forfeiting a fraction of the bond. After IN_FLIGHT, cancellation is treated as a failed attempt.

## Composition with commerce protocols

Different commerce protocols (UCP, ACP, AP2, x402, MPP, …) make different choices about how an agent's authority is structured. To make the Mandate primitive admit all of them without forcing a single shape on every implementation, three axes are kept **orthogonal** in the Mandate type rather than collapsed:

| Axis | What it expresses | Example difference between protocols |
|---|---|---|
| **Discovery axis** | Does the agent discover the counterparty/tool, or know it a priori? | UCP exposes a `/.well-known/ucp` capability profile; ACP usually has endpoints known a priori. |
| **Session-state-model axis** | Stateless tool call vs. explicit lifecycle the consumer must track | UCP is often stateless or session-scoped per capability; ACP has explicit `checkout_session` with `created → ready → completed → cancelled`. |
| **Authorization-carrier axis** | Bearer / signed mandate / delegate payment token / something new | AP2 uses signed mandates; ACP uses Stripe-style delegate payment tokens; many UCP merchants use idempotency-key + bearer. |

If a Mandate collapses any two of these into one field, then whenever a deployment behaves differently along the collapsed axis (e.g. AP2-signed checkout against an ACP-state-machine merchant) the abstraction has to leak. Keeping the axes as independent attributes preserves the abstraction.

**Deliberately not encoded into Mandate fields** (left to the deployment layer or the Tool Registry's metadata):

- *Audit / compliance provenance* — which protocol carried the action, which authorization carrier signed. Belongs in the [Execution Proof](execution-proof.md) attestation chain, not in the signed Mandate.
- *Retry semantics* — `429 + Retry-After` vs `409 + idempotency_key` style choices. Belongs in the composable HTTP layer below the Mandate.

Encoding either of these into Mandate would force a Mandate spec revision every time a protocol changes its surface.

This decomposition is informed by the production experience of [Nolpak14/agorio](https://github.com/Nolpak14/agorio), a toolkit that bridges UCP + ACP + AP2 + MCP under one tool surface and documents the abstraction-leak points explicitly in [ADR 0002 — Quad-protocol](https://github.com/Nolpak14/agorio/blob/main/docs/adr/0002-quad-protocol.md) and [ADR 0004 — Composable HTTP](https://github.com/Nolpak14/agorio/blob/main/docs/adr/0004-composable-http.md).

## Open questions

- Multi-agent mandates (co-execution).
- Sub-mandates (delegating sub-tasks to other agents).
