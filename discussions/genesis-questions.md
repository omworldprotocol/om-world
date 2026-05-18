# Genesis Questions

> Open questions to resolve before mainnet genesis. Each should end with either a decision (linked to a spec or doc) or an explicit deferral.

## Closed (decided in the Genesis phase)

- **Token or no token?** **Decided: no token in the Genesis phase.** Settlement uses an internal OM Credit (OMC) ledger only — see [GENESIS-BUILDERS.md §What you get](../GENESIS-BUILDERS.md), [GOVERNANCE.md §Relationship to Future Token](../GOVERNANCE.md). No allocation of any token or financial instrument is contemplated for any contributor or class of contributors, now or in any future state of the protocol. Any future settlement asset would require an independent, public review process and is not committed.

## Protocol

1. **What is the minimum viable proof?** Can we ship without TEE attestations, relying on optimistic disputes alone? *(Open. MVP currently records `trace_json` only; no cryptographic proofs are in scope yet.)*
2. **Plan privacy vs. transparency.** How much of the plan must be public at mandate time?
3. **Multi-agent mandates.** First-class, or compose via sub-mandates?
4. **Off-chain tool attestation.** How do we onboard APIs that cannot sign their responses?

## Governance

5. **Founding stewards.** Who, how many, with what term limits?
6. **Council formation trigger.** Time-based, milestone-based, or both? *(Today: editorial decisions sit with the GENESIS-BUILDERS editors group; no Council yet exists.)*
7. **Treasury constitution.** What can the treasury fund, and what is permanently out of scope? *(Today: no treasury exists.)*

## Economics

8. **Default fee split.** Is 60/25/10/5 right? On what basis? *(MVP uses OMC test values per `OM_World_MVP_Development_Spec_v0.1` §8: capability reward 10, pattern creation 5, pattern reuse 2, intent submission cost 1.)*
9. **Cold-start subsidies.** Should subsidies exist for early supply-side contributors? If yes, sunset rule?

## Brand & community

10. **License.** MIT, Apache-2.0, BSL with a conversion date, or something else?
11. **Working language.** English-primary with translated mirrors, or multilingual from day one?
12. **Where do discussions live?** GitHub issues, a forum, a chat — or all three with clear roles?

---

*Add your name and stance under any question via PR. Closed questions stay above with a brief decision record; deeper rationale lives in [../docs/](../docs/) or the relevant top-level doc.*
