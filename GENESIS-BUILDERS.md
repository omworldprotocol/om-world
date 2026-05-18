# Genesis Builders

> How OM World protocol design grows through outside contributions while staying coherent.

## Why this exists

OM World is a protocol, not a product. A protocol that wants to last needs design contributions from outside its founding team — but "open contributions" only works if there is structure: roles, expectations, decision rights, exit paths.

The Genesis Builders system is that structure for OM World's first version cycle (Genesis through v1.0). It exists so that:

- Contributors know what they are committing to before they commit
- Existing contributors can rely on each other to be reachable
- Attribution is concrete, fair, and durable
- The spec stays coherent even as input distributes

We do not expect Genesis Co-builders to work for OM World. We expect them to do their own work, and to tell us when our spec helps or fails them. The obligations exist so that other Co-builders can rely on each other to be reachable — not so individual contributors are paying us back.

---

## The three roles

| Role | Recognizes | You commit to |
|------|------------|---------------|
| **Genesis Reviewer** | One or more substantive design suggestions adopted into a spec. | Be available for occasional review pings. If you don't have time, say so once — we won't keep asking. |
| **Genesis Co-author** | Multi-round design dialogue (≥3 rounds) that shaped at least two sections of one primitive. | (1) Review your primitive at v0.2 / v1.0 freeze (~1 week window per freeze). (2) Respond to design pings on your primitive within ~1 week — "out of cycle, ping me later" is a valid response. (3) Link OM World as the reference spec when your project uses the primitive you co-authored. (4) Raise spec disagreements through OM World channels before going public — otherwise the attribution signal gets noisy for everyone listed. |
| **Primitive Steward** | Long-term maintenance ownership of one primitive, typically after v1.0 freeze. | (1) Respond to issues on your primitive within ~3 days (response, not resolution). (2) Co-edit access on the spec section (push permissions). (3) Quarterly heartbeat in the Genesis Builders discussion (one message confirming you are still active is enough). (4) Participate in all major freezes for your primitive. |

Co-author obligation (3) is bidirectional: you get to badge your project as a reference implementation of an OM World primitive, and we get evidence that the spec is in use. Co-author obligation (4) protects everyone listed on the spec from confusion if a co-author publicly contradicts the work they co-authored without first surfacing the disagreement.

---

## What you get

- **Public attribution** in [CONTRIBUTORS.md](CONTRIBUTORS.md) and at the bottom of each spec file you shaped, with concrete citations to the sections or commits your contribution drove
- **Acknowledgment in the Litepaper** (v0.2 onward)
- **Pre-publication access** to spec changes 48 hours before they go public, for the primitive(s) you are listed on
- **Reference implementation status** — if your code implements the primitive you co-authored, we will link to it from the spec
- **Influence on design direction** — your patterns shape what the protocol becomes; reference implementations are how protocols actually propagate
- **Public attribution is the recognition.** No token is planned. No allocation of any token or financial instrument is contemplated for any contributor or class of contributors, now or in any future state of the protocol. Genesis Builder status confers exactly the items above (public credit, Litepaper acknowledgment, pre-publication access, reference-implementation linking, influence on design direction) — nothing more. Any future governance change, including but not limited to the introduction of a token, would be decided through the then-current governance process and is independent of Genesis Builder status; participation in that future process is not promised here.

---

## What we do not ask for

- ❌ Code contributions (welcome, never required for any role)
- ❌ Marketing, evangelism, or amplification
- ❌ Regular meetings (office hours are optional, see below)
- ❌ Exclusivity — work on competing or adjacent projects all you want; design discipline matters more than allegiance
- ❌ Lifetime commitment — step back any time; past contributions remain attributed

---

## How to become a Genesis Builder

There is no application form. Builders are recognized for what they have already done:

- **Genesis Reviewer** — give substantive design feedback on a spec; if it lands in the next revision, you get listed (with your permission)
- **Genesis Co-author** — over 3+ rounds, shape 2+ sections of one primitive; we will invite you when the pattern is clear
- **Primitive Steward** — earned by Co-authors who want to continue stewarding their primitive past v1.0 freeze

You can always raise spec issues on the [om-world repo](https://github.com/omworldprotocol/om-world/issues) without being a Builder. The Builder roles exist to recognize patterns of contribution, not to gatekeep contribution itself.

When you accept an invitation, you can expect a consistent onboarding sequence — public attribution, spec-file citation, reference-implementation link (where applicable), a personal welcome thread in the Genesis Builders discussion, and a confirmation reply on the original outreach thread that names the next concrete touchpoint (typically the freeze-review window). The exact steps are documented in [CO-BUILDER-ONBOARDING.md](CO-BUILDER-ONBOARDING.md) so the same recognition surface is given to every Co-builder, regardless of who runs the onboarding.

---

## Decision rights

Spec direction is decided by the editors (currently the founding team).

| Action | Authority |
|--------|-----------|
| Write spec content | Editors |
| Strong consultation / public review at freeze | Co-authors (their primitive) · Reviewers (any primitive) |
| Veto power | **None.** Major disagreements are discussed in the open, documented if unresolved, and decided by editors |
| Modify your own attribution | The contributor (to remove or update) · Editors (to add) |

This is the Linux kernel model, not the DAO model. We chose this because **spec coherence is the load-bearing property of a protocol**, and coherence requires concentrated authorship even with widely distributed input.

Dissenting opinions on a freeze can be recorded in the spec's appendix.

---

## Communication

Default mode: **open by default.** Private channels exist for specific reasons (pre-publication coordination, sensitive disagreements), not as the default.

| Channel | Purpose | Visibility |
|---------|---------|------------|
| **GitHub Issues & PRs** on `omworldprotocol/om-world` | Primary channel for spec design dialogue | Public |
| **GitHub Discussions → `Genesis Builders` category** | Cross-primitive synthesis, freeze coordination, builder-to-builder dialogue | Public to read; topics owned by active Builders |
| **Private signal** (email, Signal, etc.) | Pre-publication coordination, sensitive design disagreements before they are ready for public discussion | Per-Builder, optional |
| **Office hours** | Bi-weekly 30-minute synchronous call (starts when active Builders reach 3+) | Active Builders only, optional, recorded summary posted publicly |

For sensitive synchronous communication, each Builder picks their preferred channel at the time of invitation. We default to GitHub for everything else.

---

## Lifecycle

Normal path:

```
Outside contributor → Reviewer → Co-author → (optional) Steward → (eventually) Emeritus
```

Status triggers:

- **Sustained silence (60 days with no response to direct ping)** → active status moves to `inactive`. Attribution stays. If you re-engage, status flips back to `active` automatically.
- **Public disagreement on direction** → discussed transparently in the relevant spec issue. Editors make the final decision. Substantive dissenting views are recorded in the spec appendix.
- **Misuse of the OM World name** (representing positions you do not hold, claiming authority beyond what is attributed) → private notice, then a formal written notice if the behavior continues. Active status is removed; past contributions remain attributed. **Attribution is a record of fact; we do not rewrite history when relationships sour.**

You can step back voluntarily at any time. Email or open an issue saying so. Your past attribution remains; we just stop including you in active pings, pre-publication previews, and freeze invitations.

---

## Versioning the spec

OM World specs version through these stages:

- **v0.x — Drafts** — rapid iteration; sections can change without freeze
- **v0.2 — First freeze** — each primitive's design intent is stable enough that implementations can build against it without expecting silent breakage
- **v1.0 — Public protocol** — wire formats stable; all changes through a formal RFC process (to be defined before v1.0)

Current freeze targets:

| Primitive | v0.2 freeze | Notes |
|-----------|-------------|-------|
| [Intent Schema](docs/intent-schema.md) | **2026-07-04** | Already shaped through multi-round dialogue; freezes ahead of the wave |
| [Agent Mandate](docs/agent-mandate.md) | **2026-08-01** | First freeze wave |
| [Execution Proof](docs/execution-proof.md) | **2026-08-01** | First freeze wave |
| [Tool Registry](docs/tool-registry.md) | **2026-08-01** | First freeze wave |

v1.0 dates will be set once v0.2 implementations have had ~2 quarters of ecosystem feedback.

---

## Questions

Open an issue tagged `genesis-builders` on the [om-world repo](https://github.com/omworldprotocol/om-world).
