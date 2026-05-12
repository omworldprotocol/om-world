# Economic Model

> Draft. Numbers are placeholders until calibration.

## Actors & cashflows

```
Principal ──fee──▶ Agent ──share──▶ Tool Providers
                       │
                       └──share──▶ Protocol Treasury ──▶ Verifiers, Stewards, Public Goods
```

## Principles

1. **Pay on proof, not on promise.** Fees settle only after PROVEN → SETTLED.
2. **Bonds scale with claim.** Higher fee quotes require higher agent bonds.
3. **Verifiers are paid by the protocol, not the agent.** Avoid the obvious conflict.
4. **Tool providers earn per attested call.** Unattested calls earn nothing.

## Token (if any)

TBD — open question whether a native token is required, or whether stablecoins + reputation suffice. See [discussions/genesis-questions.md](../discussions/genesis-questions.md).

## Fee anatomy

| Component | Default share |
|---|---|
| Agent | 60% |
| Tool providers (split per call) | 25% |
| Treasury | 10% |
| Verifier pool | 5% |

## Slashing flows

Slashed bonds flow to: (a) the principal (compensation), (b) the challenger (bounty), (c) treasury. Split TBD.

## Sybil & spam

- Issuance of intents requires a refundable deposit when the principal lacks reputation.
- Agents must hold minimum bond regardless of mandate count, to bound parallel risk.

## Open questions

- Subsidies for cold-start tools.
- Cross-chain fee settlement.
- MEV-style extraction in plan auctions.
