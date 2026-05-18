# Intent Lifecycle

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one uses a simpler 5-state model in the `intents` table (`submitted → classified → matched → in_execution → fulfilled`, plus `failed` / `archived`). The dispute/resolution/expiry paths described below are the long-term target, not the current implementation. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

## States

```
DRAFT → ISSUED → MATCHED → IN_FLIGHT → PROVEN → SETTLED
                                    ↘ DISPUTED → RESOLVED
                                    ↘ EXPIRED
                                    ↘ CANCELLED
```

## Transitions

| From | To | Trigger | Who |
|---|---|---|---|
| DRAFT | ISSUED | sign + publish | Principal |
| ISSUED | MATCHED | mandate accepted | Agent |
| MATCHED | IN_FLIGHT | first tool call | Agent |
| IN_FLIGHT | PROVEN | proof posted | Agent |
| PROVEN | SETTLED | verifier ack | Verifier |
| PROVEN | DISPUTED | challenge raised | Anyone |
| DISPUTED | RESOLVED | adjudication | Council / contract |
| ISSUED \| MATCHED \| IN_FLIGHT | EXPIRED | `expires_at` passed | Anyone |
| ISSUED \| MATCHED | CANCELLED | signed cancel | Principal |

## Timeouts

Default windows per state (all overridable by `intent.on_expire` and `mandate.deadline`):

| State | Default window | On expiry |
|---|---|---|
| ISSUED | Until `intent.expires_at` | → EXPIRED; matched agents release mandate |
| MATCHED | Until `intent.expires_at` | → EXPIRED; mandate released; partial bond forfeited |
| IN_FLIGHT | Until `intent.expires_at` | → EXPIRED; treated as failed attempt; full bond slashable |
| PROVEN | 48 h dispute window | → SETTLED automatically if no challenge raised |
| DISPUTED | 7 days | → RESOLVED by council/contract; unresolved → re-opens dispute |

When `intent.on_expire` is set, that rule takes precedence over the default for ISSUED / MATCHED / IN_FLIGHT transitions:

- `"cancel"` — move to CANCELLED (not EXPIRED), release mandate, partial bond forfeiture.
- `"revert"` — as cancel, plus trigger rollback artifacts if any were declared in the execution proof.
- `"escalate"` — notify the address in `on_expire.notify`; state pauses at MATCHED or IN_FLIGHT until a human acknowledges, then follows the default path.

## Replay & double-fulfillment

TBD — how the protocol prevents the same intent being executed twice.

## Observability

Each transition emits a typed event. See [execution-proof.md](execution-proof.md) for the proof envelope.
