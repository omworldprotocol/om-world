# Tool Registry

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
| `attestation_method` | How calls are attested (sig, TEE, oracle, none) |
| `pricing` | Per-call or subscription terms |
| `slo` | Latency / availability commitments |
| `bond` | Provider stake, slashable on misbehavior |
| `tags` | Discovery hints |

## Discovery

Agents query the registry by capability, price, SLO, and reputation. Results are reproducible: the same query at the same block returns the same ranking.

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
