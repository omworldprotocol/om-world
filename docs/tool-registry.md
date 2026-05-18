# Tool Registry

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one uses a flat `capabilities` table that providers fill via a web form (Submit a Capability) with no bonds, no on-chain registration, no slashing, and no decentralized curation. The full registry primitives below — bonds, scope tokens, dispute mechanics, attestation chains — are the long-term target, not the current implementation. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

> The directory of capabilities agents can invoke.

## Purpose

Make tools discoverable, versioned, and accountable. A tool is anything an agent can call to act on the world: a contract method, an HTTP API, a model, a physical actuator.

## Registration

A tool entry contains:

| Field | Description |
|---|---|
| `tool_id` | Stable identifier |
| `version` | Semantic version |
| `provider` | Address of the provider |
| `interface` | Typed schema for input / output |
| `boundary` | Reachability class: `local` \| `relay` \| `public` (see below) |
| `operation_class` | Mutation class: `read` \| `write` \| `destructive` \| `admin` (see below) |
| `confirmation` | Human confirmation requirement: `automatic` \| `human-in-loop` \| `restricted` (see below) |
| `attestation_method` | How calls are attested: `sig` \| `tee` \| `oracle` \| `zktls` \| `none` |
| `stateful` | Boolean — whether the tool operates against mutable state (affects `context_hash` requirements in execution proofs) |
| `pricing` | Per-call or subscription terms |
| `slo` | Latency / availability commitments |
| `bond` | Provider stake, slashable on misbehavior |
| `tags` | Discovery hints |

### boundary

| Value | Meaning |
|---|---|
| `local` | Tool is hosted on the principal's own infrastructure; agents must operate behind the same network boundary |
| `relay` | Tool is reachable via a relay with restricted operation class (typically read-only by default) |
| `public` | Tool is openly reachable; any credentialed agent may invoke it |

### operation_class

| Value | Meaning |
|---|---|
| `read` | Returns data; no state mutation |
| `write` | Mutates state in a reversible or append-only way |
| `destructive` | Mutates state irreversibly (delete, format, transfer) |
| `admin` | Changes configuration, permissions, or access control |

Agents must declare the highest `operation_class` they will invoke per tool in `mandate.tools_declared`. Invoking a higher class than declared is a mandate violation.

### confirmation

| Value | Meaning |
|---|---|
| `automatic` | Agent may invoke without human confirmation |
| `human-in-loop` | Agent must present the planned invocation to the principal before executing |
| `restricted` | Invocation is blocked for autonomous agents; requires explicit out-of-band principal approval |

> **Open question:** Are `operation_class` and `confirmation` tool-defined (registered once, registry-enforced for all deployments) or deployment-defined (operator configures per-deployment, registry only surfaces the schema)? The former allows the registry to enforce constraints universally; the latter gives operators flexibility but makes cross-deployment guarantees impossible.

## Discovery

The default agent interaction model is **lazy discovery via meta-tools**, not full catalog enumeration. Exposing all registered tools upfront is impractical at scale and consumes excessive agent context.

The registry must support four meta-operations that agents use to discover and invoke tools incrementally:

| Meta-operation | Description |
|---|---|
| `registry.list_categories` | Returns top-level capability categories (not individual tools) |
| `registry.describe` | Returns full interface schema and security attributes for a specific `tool_id` |
| `registry.search` | Returns ranked `tool_id` list for a capability query, filtered by `boundary`, `operation_class`, and `confirmation` |
| `registry.check_permissions` | Returns whether the calling agent's mandate authorizes invocation of a specific tool at the requested `operation_class` |

Agents begin with `list_categories` or `search`, then call `describe` on candidates before invoking. Full upfront enumeration is supported but not the default interaction pattern.

Search results are reproducible: the same query with the same registry state returns the same ranking.

## Reputation

Reputation is derived from:
- Successful invocations (weight by stake & age).
- Dispute outcomes.
- Principal-side ratings (optional, bounded influence).

## Deprecation

Tools may be marked `deprecated` but not removed. Existing mandates referencing a deprecated tool remain valid until expiry.

## Open questions

- How to verify off-chain tool outputs at scale.
- Tool composition / aliasing (tool-as-a-pipeline).
- Permission tier source: should `operation_class` and `confirmation` be tool-defined (enforced uniformly by the registry) or deployment-defined (operator-configured per instance)? See note in §Registration above.
