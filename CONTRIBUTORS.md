# OM World Contributors

> Public attribution for everyone who has shaped OM World — from a single design suggestion to ongoing Primitive Stewardship.

The roles, expectations, and lifecycle below are defined in [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md).

Past contributions are permanent. Active status can change. Names appear here with the contributor's permission.

---

## Genesis Co-builders

### Intent Schema

#### Co-authors

**Kawacu Rugiraneza Arnaud Kennedy** — [@kawacukennedy](https://github.com/kawacukennedy) · [@kawacukennedy on X](https://x.com/kawacukennedy) · [kubernalabs.vercel.app](https://kubernalabs.vercel.app) — Joined 2026-05-17

Shaped four sections of the [Intent Schema](docs/intent-schema.md) across 5 rounds of design dialogue ([reference thread](https://github.com/kawacukennedy/kuberna-labs/issues/4)):

- **`executor` binding model** — established activation-time binding as the recommended default and explained why creation-time binding defeats permissionless solver networks ([commit a3bdb5d](https://github.com/omworldprotocol/om-world/commit/a3bdb5d))
- **`attestation.type: multi` semantics** — proposed and grounded the ALL-with-fallback-chain-by-dimension model over the original "satisfy at least one" framing, with the anti-pattern rule for same-dimension redundancy ([commit a3bdb5d](https://github.com/omworldprotocol/om-world/commit/a3bdb5d))
- **`attestation.verifier` per-dimension map** — moved the schema default from single routing-contract address to per-dimension addresses; surfaced the dispute-resolution argument (challenger should not need an extra RTT through a router inside a 48h window) ([commit cad3c57](https://github.com/omworldprotocol/om-world/commit/cad3c57))
- **`attestation.verifier.fallback` adjudicator field** — added the escape hatch for verifier compromise during the dispute window, with the two-layer compromise response pattern (on-chain VerifierRegistry timelocked pause + off-chain security-council signal) ([commit b24ef68](https://github.com/omworldprotocol/om-world/commit/b24ef68))

Reference implementation: [Kuberna `IVerifierRouter` Solidity interface](https://gist.github.com/kawacukennedy/2c42da7b4a74aff0d83bd40968a77864) — canonical maintained gist by @kawacukennedy as a reference shape for implementations to adopt or adapt.

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

_Substantive design improvements that landed in the spec. Reviewers are listed once the change ships and the contributor consents to public attribution._

### Agent Mandate

**[@Nolpak14](https://github.com/Nolpak14)** — Joined 2026-05-18

Multi-round design feedback ([reference thread](https://github.com/Nolpak14/agorio/issues/50)) grounded in production agorio code paths, shaping four sections of the [Agent Mandate](docs/agent-mandate.md) spec:

- **Three-axis decomposition for cross-protocol composition** — the framing of Discovery / Session-state-model / Authorization-carrier as orthogonal axes in §Composition with commerce protocols, preventing the silent leak that happens when any two are collapsed into one Mandate field
- **`tools_declared[*].carrier` field for explicit carrier binding** — a minimal v0.2 addition that lets verifiers reject mandate/carrier mismatches instead of silently adopting bearer semantics, closing the sub-credential expiry split-brain (`AP2 mandate.expiresAt` vs `tools_declared[*].expiry`)
- **`executor.delegates: address[]` for multi-LLM sub-agent attribution** — pre-authorizes a set of sub-agent addresses under one parent identity, so EU AI Act attribution (which LLM authorized what) survives without forcing one slashable bond per sub-agent
- **Asymmetric framing of UCP vs ACP in §Composition** — UCP is the canonical vocabulary; ACP and AP2 are adapted into it. Stated explicitly so implementers don't assume parity and silently break on ACP-specific behaviors (lifecycle transitions, mid-session `payment_handler` swap)

Reference implementation: [Nolpak14/agorio](https://github.com/Nolpak14/agorio) — quad-protocol toolkit (UCP / ACP / MCP / AP2) cited in §Composition with commerce protocols as a reference single-agent runtime that composes cleanly under an OM World mandate.

Genesis Reviewer for the **agent-mandate v0.2 freeze** (target 2026-08-01); pre-publication review window ~2026-07-15.

---

### Execution Proof

**Tyche Institute** — maintainer of the [EATF](https://github.com/tyche-institute/eatf) research project · contact `dev@tyche.institute` — Joined 2026-05-19

Multi-round design feedback ([reference thread](https://github.com/tyche-institute/eatf/issues/1)) shaping two sections of the [Execution Proof](docs/execution-proof.md) spec:

- **§Threat model — runtime honesty as an explicit out-of-scope property** — added [§Threat model](docs/execution-proof.md#threat-model) at the top of the spec, stating verbatim what the envelope claims and what it deliberately does not, with the composition story (TEE underneath optional, optimistic challenge above, envelope unchanged in either direction). The term "runtime honesty" itself is adopted from Tyche; it sharpens the boundary that prior drafts treated implicitly.
- **§Related work — key-rooted + key-history-mirror as a complementary axis** — added EATF to [§Related work](docs/execution-proof.md#related-work) as a key-rooted reference instance, complementary to the JCS/JWS stack already in the cluster. The cross-spec convergence is now framed around four converging primitives (JCS canonicalization + key-rooted signatures + RFC 3161 timestamping + runtime-honesty out-of-scope) rather than just JCS+JWS+Ed25519.

**Posture:** Tyche's listing is for technical review of substrate / canonicalization / freshness / revocation decisions. It is explicitly **not** an endorsement of OM World governance, business model, or any future commercial state. Tyche reserves the right to withdraw attribution if a token, ICO, or commercial offering is introduced prior to v0.2 publication, or if the no-token policy in [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md) is rescinded.

**License of contribution:** CC-BY-4.0 (per the prose scope in [LICENSE](LICENSE)).

Genesis Reviewer for the **execution-proof v0.2 freeze** (target 2026-08-01); pre-publication review window ~2026-07-25. Schedule conditional on no collision with Tyche's own public-release prep under `github.com/tyche-institute` — to be confirmed ~2026-07-15.

---

**[@Trusteedxyz](https://github.com/Trusteedxyz)** — Joined 2026-05-17

Multi-round design feedback ([reference thread](https://github.com/Trusteedxyz/Trust-Receipt-Verifier/issues/3)) that shaped six sections of the [Execution Proof](docs/execution-proof.md) spec:

- **JCS (RFC 8785) as the canonical-form requirement** — moved [intent-schema §Canonicalization](docs/intent-schema.md#canonicalization) out of TBD and grounded [execution-proof §Canonicalization](docs/execution-proof.md#canonicalization) in a deterministic, multi-language-supported standard ([commit d380a69](https://github.com/omworldprotocol/om-world/commit/d380a69))
- **RFC 3161 timestamp sidecar pattern** — added [§Long-term verifiability](docs/execution-proof.md#long-term-verifiability) so proofs remain verifiable across signing-key rotation and compromise events without invalidating the original signature ([d380a69](https://github.com/omworldprotocol/om-world/commit/d380a69))
- **Two-state key revocation (rotated vs compromised)** — added [§Key revocation states](docs/execution-proof.md#key-revocation-states) with the verifier rule that revocation state is consulted at proof-validation time rather than proof-creation time ([d380a69](https://github.com/omworldprotocol/om-world/commit/d380a69))
- **"Envelope is the unit; slicing is undefined behavior"** — pinned in [§Envelope](docs/execution-proof.md#envelope-v0) as a documented non-goal to prevent the predictable forwarding-of-sub-receipts failure mode ([commit pending])
- **Relayer attestation must commit to exact JCS-canonicalized bytes** — encoded as a rule in the new [§On-chain verification](docs/execution-proof.md#on-chain-verification) section, closing the dispute-path reconstruction gap on the relayer-attested path
- **JCS + JWS + Ed25519 ecosystem-convergence note** — surfaced in the new [§Related work](docs/execution-proof.md#related-work) so verifier code can be shared across the cluster

Reference implementation: [Trusteedxyz/Trust-Receipt-Verifier](https://github.com/Trusteedxyz/Trust-Receipt-Verifier) — JWS Compact + JCS + Ed25519 trust-receipt stack for agentic commerce.

Genesis Reviewer for the **execution-proof v0.2 freeze** (target 2026-08-01).

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
