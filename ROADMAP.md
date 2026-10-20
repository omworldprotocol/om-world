# OM World Roadmap

## Status

This roadmap is a public draft.

OM World is currently in the Genesis phase.
Dates, phases, and deliverables may change as the community, technical architecture, and protocol design evolve.

### Maintenance snapshot — 2026-10-20

| Area | Evidence status for this restart |
|---|---|
| Phase 0 foundation | Core documents, visual assets, repository, and initial issues are present; the full exit criteria have not been independently accepted here. |
| Phase 1 specifications | Four primitive design drafts are present. Freeze completion and the requirement for three fully mapped use cases are unconfirmed; candidate use-case descriptions are not complete protocol mappings. |
| Phase 2 MVP | Historically reported as shipped on 2026-05-18; current service availability, behavior, and performance are not revalidated. |
| Phase 3 testnet | Future design; an OM World deployment and its exit criteria have not been verified for this restart. External related-work deployments are not OM World deployments. |
| Phases 4–5 network and economy | Long-term design, not a current delivery, budget, grant, bounty, or contributor commitment. |

The phase numbers organize the historical roadmap; they do not certify that earlier exit criteria passed. Past review dates in [Genesis Builders](GENESIS-BUILDERS.md#versioning-the-spec) remain historical targets. Current work is the documentation maintenance listed below, not automatic progression to a later phase.

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

The planning lists below are historical design checklists, not canonical wire formats or evidence that each item has shipped. Current field definitions are in [Intent Schema](docs/intent-schema.md#fields-v0), [Agent Mandate](docs/agent-mandate.md#fields-v0), [Execution Proof](docs/execution-proof.md#envelope-v0), and [Tool Registry](docs/tool-registry.md#registration), each still marked as a design draft. Verification requirements are discussed within the Execution Proof; the separate Verifier Model heading below is a planning topic, not a claim of a second delivered specification.

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

A format for recording an agent's fulfillment claim and its supporting evidence. The current [envelope](docs/execution-proof.md#envelope-v0), [step record](docs/execution-proof.md#step-record), and [threat model](docs/execution-proof.md#threat-model) define the actual draft surface and its limits.

Historical planning items (not current field names; for example, `proof_id` and `settlement_reference` are not envelope fields):

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

## Phase 2 — Historical MVP shipment report (2026-05-18)

**Historical deployment address: https://app.omworld.one.** Current availability and behavior are unverified for this restart. The historical report describes this loop:

**submit intent → LLM classify → match capability → execute → record pattern → credit OMC**

### Modules described in the historical shipment report (per OM_World_MVP_Development_Spec_v0.1)

1. **Intent Demand Entry** — `Submit an Intent` form (web), persisted to `intents` table, auto-classified by LLM, an `intent_type` written back.
2. **Capability Supply Entry** — `Contribute a Capability` form (web), persisted to `capabilities` table; supply types: `Tool` / `Agent` / `Human Service`.
3. **Matching Engine** — LLM-routed: classified intent + candidate capabilities → 1–3 ranked `realization_paths`. Half-automatic (user picks a path before execute).
4. **Pattern Library v0** — first execution of a new `intent_type` creates a Pattern record; subsequent executions of the same type adapt the existing Pattern (smaller LLM call, faster wall time), incrementing `reuse_count`.
5. **OM Credit Ledger v0** — internal OMC accounting: every user grant (100), submission cost (1), capability reward (10), pattern creation (5), and pattern reuse (2) writes a `credit_event` row. No on-chain token. No financial promise.

### First seeded capability & intent type

The MVP launched with one seeded capability: **Genesis Builder Recruitment Generator**, supporting the single intent type `community_growth.builder_recruitment`. The shipment report described this as the founder's first use case; this is historical context, not evidence of current use.

### Historical timing observation (not current validation)

The proposed MVP success criterion was: **the second realization of any intent_type should be easier than the first.** The historical report recorded these values for 2026-05-18 (retained as reported, not remeasured):
- Round 1 (fresh generation): ~78s wall time
- Round 2 (adapted from Pattern): ~57s wall time → **−20%**
- Pattern Library: 1 created, 1 reused, OMC ledger 227 issued / 27 distributed

The stated ~78s and ~57s point values imply approximately 26.9% less wall time, while the historical report labels the change −20%; the original timing evidence and calculation basis have not been rechecked here. These approximate, small-N observations do not establish a general performance result or validate the self-growth thesis. No runtime or model rerun was performed for this correction.

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

## Current Immediate Priorities — documentation maintenance

1. Align contribution guidance, roadmap status, and the [restart record](docs/collaboration-restart.md) with delivered documents and merged PRs, while retaining historical dates and evidence limits.
2. Prepare disposition proposals for existing issues: distinguish draft delivery, remaining design questions, and historical activities. Do not treat this list as an instruction to close or relabel issues.
3. Review bounded documentation inconsistencies against the current primitive drafts and cite the exact source revision. No new adapter, deployment, or experiment is required to complete this maintenance step.

Translation, contributor recruitment, calls, live-service validation, and technical expansion are deferred until separately scoped. No new freeze date, review assignment, budget, or partner commitment is established by this update.

## Historical Genesis task suggestions

The post-MVP suggestions below are retained as historical planning context, not current assignments or an instruction to create issues, run the service, recruit contributors, or start translation. Existing drafts should be reviewed before proposing a new specification task:

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
