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

## Open questions

- Multi-agent mandates (co-execution).
- Sub-mandates (delegating sub-tasks to other agents).
