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

## Phase 2 — MVP Prototype

### Objective

Build the first working prototype of the OM World intent lifecycle.

This phase is about demonstrating the loop:

**declare → bind → route → execute → prove → settle**

### Key Deliverables

#### 1. Intent Submission Interface

A simple interface where users can submit an intention.

Should support:

* natural language input
* structured intent preview
* constraint editing
* budget configuration
* verification requirement selection
* mandate generation

#### 2. Tool Registry Prototype

A basic registry of available tools.

Should support:

* tool listing
* tool metadata
* capability tags
* creator identity
* input/output schema
* pricing information
* verification method
* status and reputation fields

#### 3. Basic Agent Router

A simple routing engine that selects tools based on intent requirements.

Should support:

* tool matching
* execution plan generation
* risk warning
* cost estimation
* explanation of chosen path

#### 4. Execution Log Format

A standard log for recording agent and tool actions.

Should support:

* action timestamps
* tool calls
* inputs and outputs
* hashes
* errors
* retries
* final result

#### 5. Proof Hash Generator

A basic mechanism for hashing outputs, logs, and artifacts.

Should support:

* output hash
* execution trace hash
* artifact hash
* proof record export

#### 6. Public Explorer Prototype

A read-only explorer for viewing non-sensitive intent records.

Should show:

* intent ID
* status
* tools used
* proof hash
* verifier status
* settlement status
* public metadata

### Early MVP Use Cases

The first MVP should focus on narrow and verifiable use cases.

Recommended candidates:

1. Research report generation with source records
2. Code task execution with test logs
3. Cloud server comparison with decision proof
4. Smart contract risk analysis with finding hashes
5. Content generation with artifact history

### Exit Criteria

Phase 2 is complete when:

* a user can submit an intent
* the system can generate a mandate
* at least one tool can be invoked
* execution logs are created
* proof hashes are generated
* results can be viewed in an explorer
* the process can be reproduced by external contributors

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

## Current Immediate Priorities

The current Genesis priorities are:

1. Finalize README.md
2. Publish MANIFESTO.md
3. Publish LITEPAPER.md
4. Publish CONTRIBUTING.md
5. Publish ROADMAP.md
6. Publish BRAND.md
7. Upload Visual Language System v1
8. Open Genesis issues
9. Invite first contributors
10. Prepare first public builder thread

## Suggested Genesis Issues

Recommended public GitHub issues:

1. Draft Manifesto v0.1
2. Draft Litepaper v0.1
3. Define Intent Schema v0.1
4. Define Agent Mandate format
5. Define Execution Proof format
6. Design Tool Registry v0.1
7. Map first 10 intent use cases
8. Prepare first builder call
9. Translate Genesis documents into Chinese
10. Review Visual Language System v1

## Final Note

The roadmap of OM World should remain open.

A closed roadmap creates a product.

An open roadmap creates a world.

**One Mind, One World.**

**AI executes. Crypto verifies. Humanity owns its intentions.**
