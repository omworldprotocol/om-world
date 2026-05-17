# OM World Contributors

> Public attribution for everyone who has shaped OM World — from a single design suggestion to ongoing Primitive Stewardship.

The roles, expectations, and lifecycle below are defined in [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md).

Past contributions are permanent. Active status can change. Names appear here with the contributor's permission.

---

## Genesis Co-builders

### Intent Schema

#### Co-authors

**[@kawacukennedy](https://github.com/kawacukennedy)** — Joined 2026-05-17

Shaped four sections of the [Intent Schema](docs/intent-schema.md) across 5 rounds of design dialogue ([reference thread](https://github.com/kawacukennedy/kuberna-labs/issues/4)):

- **`executor` binding model** — established activation-time binding as the recommended default and explained why creation-time binding defeats permissionless solver networks ([commit a3bdb5d](https://github.com/omworldprotocol/om-world/commit/a3bdb5d))
- **`attestation.type: multi` semantics** — proposed and grounded the ALL-with-fallback-chain-by-dimension model over the original "satisfy at least one" framing, with the anti-pattern rule for same-dimension redundancy ([commit a3bdb5d](https://github.com/omworldprotocol/om-world/commit/a3bdb5d))
- **`attestation.verifier` per-dimension map** — moved the schema default from single routing-contract address to per-dimension addresses; surfaced the dispute-resolution argument (challenger should not need an extra RTT through a router inside a 48h window) ([commit cad3c57](https://github.com/omworldprotocol/om-world/commit/cad3c57))
- **`attestation.verifier.fallback` adjudicator field** — added the escape hatch for verifier compromise during the dispute window, with the two-layer compromise response pattern (on-chain VerifierRegistry timelocked pause + off-chain security-council signal) ([commit b24ef68](https://github.com/omworldprotocol/om-world/commit/b24ef68))

Reference implementation: [Kuberna `IVerifierRouter` Solidity interface](https://github.com/kawacukennedy/kuberna-labs/issues/4#issuecomment-4466850557) (shared openly by @kawacukennedy as a reference shape for implementations to adopt or adapt).

Genesis Reviewer for the **intent-schema v0.2 freeze** (target 2026-07-04) and the **v0.2 freeze wave** (2026-08-01).

---

### Agent Mandate

_Co-authors will be listed here as primitive design dialogue matures._

---

### Execution Proof

_Co-authors will be listed here as primitive design dialogue matures._

---

### Tool Registry

_Co-authors will be listed here as primitive design dialogue matures._

---

## Genesis Reviewers

_Single substantive design improvements that landed in the spec. Reviewers are added when the change ships._

_(none yet listed publicly — pending consent from contributors whose suggestions have already been folded into drafts)_

---

## Primitive Stewards

_Stewards take long-term maintenance ownership of a primitive's spec section, typically after v1.0 freeze._

_(none yet — earliest possible Steward appointment is post-v0.2)_

---

## Genesis Co-builder Emeritus

_Past Co-builders who have stepped back from active status. Their attributed contributions remain in the lists above._

_(none yet)_

---

## How attribution works

- Listing here requires the contributor's permission. If you have shaped the spec but are not listed, you may not have been asked yet — open an issue tagged `genesis-builders` and we will reach out.
- Listings are concrete: they cite the specific spec sections or commits the contribution shaped, not a general "thanks to X."
- Past contributions are **permanent**. We do not rewrite attribution if active status later changes (see [GENESIS-BUILDERS.md §Lifecycle](GENESIS-BUILDERS.md#lifecycle)).
- Listings link to the contributor's GitHub profile by default; alternate handles (X, personal site) are added on request.
