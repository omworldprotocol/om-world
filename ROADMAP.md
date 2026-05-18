# OM World Roadmap

## Status

This roadmap is a public draft.

OM World is currently in the Genesis phase.
Dates, phases, and deliverables may change as the community, technical architecture, and protocol design evolve.

The purpose of this roadmap is not to create hype.

The purpose is to make progress visible.

## North Star

OM World aims to become a decentralized intent economy protocol where:

* humans own their intentions
* AI agents execute under explicit mandates
* tools are open, composable, and economically rewarded
* execution is verifiable
* crypto provides rules, settlement, and accountability
* builders can create new intent-fulfillment capabilities
* users can transform intention into verifiable reality

**One Mind, One World.**

## Phase 0 — Genesis

### Objective

Establish the public foundation of OM World.

This phase is about identity, language, principles, community, and initial protocol direction.

### Key Deliverables

* Project name: OM World
* X account
* GitHub organization
* Main repository
* README.md
* MANIFESTO.md
* LITEPAPER.md
* CONTRIBUTING.md
* ROADMAP.md
* BRAND.md
* Visual Language System v1
* Initial issue board
* Initial contributor invitation

### Core Questions

* What is OM World?
* What problem does it solve?
* Why must intent be decentralized?
* What does “AI executes, crypto verifies” mean?
* What is intent sovereignty?
* Who are the first builders?
* What should be specified first?

### Exit Criteria

Phase 0 is complete when:

* the core documents are public
* the brand system is published
* the GitHub repository is active
* the first public issues are open
* the first contributors can understand how to participate
* the project can be explained clearly in one page

## Phase 1 — Protocol Specification

### Objective

Define the minimum protocol language required for an intent economy.

This phase is about turning vision into specifications.

### Key Deliverables

#### 1. Intent Schema v0.1

A structured format for representing user intentions.

Should include:

* intent ID
* originator
* natural language statement
* structured goal
* constraints
* budget
* time limit
* risk preferences
* privacy settings
* allowed tools
* forbidden actions
* verification requirements
* settlement rules
* signature or authorization reference

#### 2. Agent Mandate v0.1

A format for granting permission to an agent or tool.

Should include:

* mandate ID
* intent ID
* authorized agent
* permitted actions
* spending limits
* data access permissions
* tool permissions
* expiration
* revocation rules
* audit requirements
* originator signature

#### 3. Execution Proof v0.1

A format for proving that an action or outcome occurred.

Should include:

* proof ID
* intent ID
* mandate ID
* executor
* action summary
* output hash
* timestamp
* evidence URI
* verifier attestations
* settlement reference
* dispute status

#### 4. Tool Registry v0.1

A standard for registering intent-fulfillment tools.

Should include:

* tool ID
* creator
* capability description
* input schema
* output schema
* pricing model
* permissions required
* verification methods
* audit status
* reputation history
* risk level

#### 5. Verifier Model v0.1

A design for how outcomes can be verified.

Should include:

* verifier roles
* proof categories
* attestation rules
* dispute process
* slashing concepts
* privacy-preserving options
* minimum proof standards by intent type

#### 6. Use Case Map v0.1

A structured map of early intent categories.

Initial categories may include:

* research
* procurement
* code generation
* smart contract audit
* content creation
* data analysis
* personal productivity
* financial operations
* governance actions

### Core Questions

* What is the smallest useful definition of an intent?
* How does a user grant consent to an agent?
* What must be verified?
* Which parts should be on-chain?
* Which parts should remain off-chain?
* How can tools be discovered and trusted?
* What is the minimum viable proof for each use case?

### Exit Criteria

Phase 1 is complete when:

* Intent Schema v0.1 is published
* Agent Mandate v0.1 is published
* Execution Proof v0.1 is published
* Tool Registry v0.1 is published
* at least three early use cases are fully mapped
* contributors can build against the initial specifications

## Phase 2 — MVP Prototype (✅ shipped 2026-05-18)

**Live at https://app.omworld.one.** The MVP demonstrates one loop end-to-end:

**submit intent → LLM classify → match capability → execute → record pattern → credit OMC**

### What actually shipped (5 modules, per OM_World_MVP_Development_Spec_v0.1)

1. **Intent Demand Entry** — `Submit an Intent` form (web), persisted to `intents` table, auto-classified by LLM, an `intent_type` written back.
2. **Capability Supply Entry** — `Contribute a Capability` form (web), persisted to `capabilities` table; supply types: `Tool` / `Agent` / `Human Service`.
3. **Matching Engine** — LLM-routed: classified intent + candidate capabilities → 1–3 ranked `realization_paths`. Half-automatic (user picks a path before execute).
4. **Pattern Library v0** — first execution of a new `intent_type` creates a Pattern record; subsequent executions of the same type adapt the existing Pattern (smaller LLM call, faster wall time), incrementing `reuse_count`.
5. **OM Credit Ledger v0** — internal OMC accounting: every user grant (100), submission cost (1), capability reward (10), pattern creation (5), and pattern reuse (2) writes a `credit_event` row. No on-chain token. No financial promise.

### First seeded capability & intent type

The MVP launched with one seeded capability: **Genesis Builder Recruitment Generator**, supporting the single intent type `community_growth.builder_recruitment`. This is the OM World founder's own first real need; it grounds the system in something used immediately.

### Self-growth validation

The MVP success criterion is: **the second realization of any intent_type should be easier than the first.** First production run (2026-05-18):
- Round 1 (fresh generation): ~78s wall time
- Round 2 (adapted from Pattern): ~57s wall time → **−20%**
- Pattern Library: 1 created, 1 reused, OMC ledger 227 issued / 27 distributed

This is small-N but it's the loop running on real LLM calls, not a mocked demo. Self-growth is validated in principle; the next step is widening it to more intent types.

### What was deliberately NOT in MVP

Per `OM_World_MVP_Development_Spec_v0.1 §14`:
- no on-chain token, no wallets
- no distributed storage, no compute network
- no complex governance or permission system
- no general agent platform
- no multi-intent-category support (just one)
- no mobile entry
- no cryptographic proofs (`trace_json` only)

Many of these are described as long-term targets in [`docs/*`](docs/), which now carry banners noting the MVP implements a simplified subset.

## Phase 3 — Testnet Experiment

### Objective

Move key protocol components on-chain in a controlled test environment.

This phase is about testing cryptographic settlement, registries, verification, and incentives.

### Key Deliverables

#### 1. On-chain Intent Registry

A smart contract or contract system for recording intent commitments.

Should include:

* intent hash
* originator
* timestamp
* status
* metadata pointer
* privacy-preserving design options

#### 2. Tool Registry Contract

A contract for registering tools and their creators.

Should include:

* creator identity
* tool metadata hash
* status
* stake requirement
* reputation pointer
* dispute status

#### 3. Verifier Registry

A contract or module for verifier participation.

Should include:

* verifier identity
* stake
* attestation history
* slashing conditions
* dispute history

#### 4. Escrow and Settlement Prototype

A contract for handling intent-related payments.

Should include:

* escrow
* milestone release
* refunds
* verifier rewards
* tool creator payments
* agent operator fees
* dispute hold

#### 5. Dispute Experiment

A basic process for handling failed or disputed outcomes.

Should test:

* user dispute initiation
* evidence submission
* verifier review
* settlement freeze
* refund or release decision
* reputation impact

### Core Questions

* Which records should be on-chain?
* How much data should be stored off-chain?
* What should be hashed?
* What should be encrypted?
* How do we prevent fake tools?
* How do we prevent verifier collusion?
* How do we resolve subjective results?
* How do we make settlement fair?

### Exit Criteria

Phase 3 is complete when:

* testnet contracts are deployed
* intents can be committed on-chain
* tools can be registered
* proof hashes can be anchored
* simple settlement can occur
* verifier attestations can be recorded
* at least one dispute simulation is completed

## Phase 4 — Builder Network

### Objective

Grow OM World from a prototype into a builder ecosystem.

This phase is about attracting tool creators, agent builders, verifiers, researchers, and interface builders.

### Key Deliverables

#### 1. Builder Program

A structured program for contributors.

Should include:

* onboarding guide
* contribution tracks
* tool creator challenge
* agent builder challenge
* verifier challenge
* research grants
* design grants
* documentation bounties

#### 2. Tool Creator Cohorts

Focused groups of builders creating tools for specific intent categories.

Possible cohorts:

* research tools
* code tools
* audit tools
* procurement tools
* content tools
* financial tools
* governance tools

#### 3. Developer Documentation

Clear technical documentation for building with OM World.

Should include:

* schema docs
* registry docs
* API docs
* SDK docs
* smart contract docs
* verifier docs
* example workflows

#### 4. Community Governance Experiments

Early governance processes for protocol decisions.

Should include:

* proposal template
* working groups
* public review process
* contributor voting experiments
* council or steward models
* conflict resolution process

### Exit Criteria

Phase 4 is complete when:

* multiple external builders are contributing
* multiple tools are registered
* at least two independent agents can use the registry
* documentation is sufficient for new contributors
* community governance is active
* public use cases are visible

## Phase 5 — Open Intent Economy

### Objective

Launch OM World as an open, multi-participant intent economy.

This phase is about real usage, real settlement, and real accountability.

### Key Deliverables

* production-grade protocol contracts
* security audits
* public tool marketplace
* agent marketplace
* verifier network
* reputation system
* settlement system
* dispute system
* governance system
* ecosystem grants
* public explorer
* user-facing interfaces
* developer SDKs

### Long-term Capabilities

OM World should eventually support:

* multi-agent execution
* cross-tool workflows
* cross-chain settlement
* private intent execution
* zero-knowledge verification
* decentralized compute integration
* autonomous tool markets
* user-owned intent history
* verifiable AI decision records
* decentralized governance of protocol parameters

### Exit Criteria

Phase 5 is complete when:

* real users can declare intents
* real tools can fulfill them
* real agents can execute under mandate
* real verifiers can attest outcomes
* real settlement can occur
* real disputes can be resolved
* real governance can modify protocol parameters

## Current Immediate Priorities (post-MVP shipment)

With Phase 2 MVP live at https://app.omworld.one, priorities have shifted:

1. **Grow capability supply** — register additional `Tool` / `Agent` / `Human Service` capabilities beyond the seeded Genesis Builder Recruitment Generator
2. **Seed the second intent type** — accept a real second-category intent so the Pattern Library expands beyond `community_growth.builder_recruitment`
3. **Run real Genesis Builder recruitment campaigns** using the live MVP — for OM World itself and for one or two partner open-source / agent / crypto projects — and feed results back as Pattern Library evidence
4. **Freeze Intent Schema v0.1** with Co-author kawacukennedy (see CONTRIBUTORS.md)
5. **Freeze Execution Proof v0.1** with Reviewer Trusteedxyz
6. **Recruit Co-authors / Reviewers** for Agent Mandate and Tool Registry
7. **MVP UI polish** — capability detail pages, pattern detail page improvements, dashboard time-series chart for self-growth visualization
8. **Documentation alignment** — keep public docs aligned with SELF_GROWTH_ENGINE.md as the canonical engine architecture
9. **Translate Manifesto + Litepaper + SELF_GROWTH_ENGINE to Chinese**
10. **Adversarial review** — red-team published documents and the live MVP; file issues with specific quotes

## Suggested Genesis Issues

Recommended public GitHub issues:

1. Submit a real intent at https://app.omworld.one/intent and report the friction
2. Register a `Tool` or `Agent` capability for an intent type *other* than `community_growth.builder_recruitment`
3. Co-author Intent Schema v0.2 (post-Genesis-Builder freeze)
4. Co-author Agent Mandate v0.2 (Co-author slot open)
5. Co-author Execution Proof v0.2
6. Co-author Tool Registry v0.2 (Co-author slot open)
7. Map the next 10 candidate intent categories with success criteria
8. Translate Manifesto + Litepaper to Chinese
9. Review Visual Language System v1 and propose an MVP UI theme
10. Red-team the published documents for token-language drift or self-growth-thesis contradictions

## Final Note

The roadmap of OM World should remain open.

A closed roadmap creates a product.

An open roadmap creates a world.

**One Mind, One World.**

**AI executes. Crypto verifies. Humanity owns its intentions.**
