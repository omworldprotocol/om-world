# Agent Mandate

> The contract an Agent posts when it accepts an Intent.

## Purpose

A mandate is a signed commitment from an Agent to attempt fulfillment of a specific Intent under stated conditions. It is the unit of accountability.

## Fields (v0)

| Field | Type | Description |
|---|---|---|
| `intent_id` | uuid | The Intent being accepted |
| `agent` | address | Agent identity |
| `plan_hash` | hash | Commitment to a plan (revealed on proof) |
| `bond` | amount | Slashable stake |
| `fee_quote` | amount | Maximum charge to principal on success |
| `tools_declared` | array | Tools the agent reserves the right to use |
| `deadline` | timestamp | Self-imposed completion target |
| `signature` | sig | Over the canonical hash |

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
