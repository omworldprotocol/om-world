# Economic Model

> **Status: v0 design draft — protocol-layer specification.** The MVP at https://app.omworld.one uses an internal OM Credit (OMC) ledger with simple fixed event values (`OMC_INTENT_SUBMISSION_COST=1`, `OMC_CAPABILITY_REWARD=10`, `OMC_PATTERN_CREATION_REWARD=5`, `OMC_PATTERN_REUSE_REWARD=2`, `OMC_INITIAL_USER_CREDITS=100`). There are no bonds, no slashing, no treasury, and no on-chain settlement. The cashflow and slashing model below describes the long-term target. See [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) for the canonical Genesis MVP architecture.

> Draft. Numbers are placeholders until calibration.

## Actors & cashflows (long-term target)

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

## Settlement asset

**Decided: no token in the Genesis phase.** MVP settlement uses internal OM Credit (OMC) ledger units only — see `OM Credit Ledger v0` in [SELF_GROWTH_ENGINE.md](../SELF_GROWTH_ENGINE.md) and the values listed at the top of this file. No party has been promised any allocation of any token or financial instrument. Any future settlement asset would require an independent, public review process and is not committed.

## Fee anatomy (long-term target, not yet implemented)

| Component | Default share |
|---|---|
| Agent | 60% |
| Tool providers (split per call) | 25% |
| Treasury | 10% |
| Verifier pool | 5% |

The split above is a calibration starting point, not a decision. The MVP does not collect fees.

## Slashing flows (long-term target, not yet implemented)

Slashed bonds flow to: (a) the principal (compensation), (b) the challenger (bounty), (c) treasury. Split TBD. No bonds exist in the MVP.

## Sybil & spam (long-term target)

- Issuance of intents requires a refundable deposit when the principal lacks reputation.
- Agents must hold minimum bond regardless of mandate count, to bound parallel risk.

## Open questions

- Subsidies for cold-start tools.
- Cross-chain fee settlement (only if a chain-based settlement is ever introduced — none planned).
- MEV-style extraction in plan auctions.
