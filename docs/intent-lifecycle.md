# Intent Lifecycle

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

TBD — default windows per state.

## Replay & double-fulfillment

TBD — how the protocol prevents the same intent being executed twice.

## Observability

Each transition emits a typed event. See [execution-proof.md](execution-proof.md) for the proof envelope.
