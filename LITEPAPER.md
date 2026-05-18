# OM World Litepaper v0.1

> 📄 [Download PDF version](assets/litepaper/OM-World-Litepaper-v0.1-Genesis-Draft.pdf)

## Status

This document is a public draft.

OM World is currently in the Genesis phase. The Genesis MVP shipped on 2026-05-18 and is live at **https://app.omworld.one** (five modules: Intent Demand Entry, Capability Supply Entry, Matching Engine, Pattern Library v0, OM Credit Ledger v0). The MVP implements a simplified subset of the architecture described in this Litepaper. The fuller cryptographic, settlement, and governance design below is the long-term target, subject to community review, technical validation, and protocol iteration.

For the canonical engine architecture in operational terms, see [SELF_GROWTH_ENGINE.md](SELF_GROWTH_ENGINE.md).

## Abstract

OM World is a **self-growing intent realization network**.

It links three sides: human intentions on the demand side; tools, agents, and human services on the supply side; and a growing Pattern Library as the memory of every successful realization. Each time a new intent is realized, the path is saved as a reusable Pattern, so the next intent of the same kind is faster, cheaper, and requires less manual thinking. The system grows more capable on its own — and the people who created the underlying Patterns are credited each time their work is reused.

The single thesis: **every realization should make the next one easier.**

Beneath the engine, OM World is designed to mature into a decentralized intent economy protocol — where AI provides execution power, verifiable records provide the rules and audit trail, humans retain sovereignty over their intentions, and contributors are credited (not just paid) for the patterns and capabilities they bring. The MVP today is the smallest possible version of that loop. The rest of this document describes how it scales.

## 1. Background

The internet has been dominated by the attention economy.

Search engines, social platforms, marketplaces, and advertising networks have competed to capture and monetize human attention.

AI changes the primary unit of interaction.

Users increasingly express goals instead of queries, outcomes instead of clicks, and intentions instead of keywords.

This transition creates a new economic layer:

**the intent economy.**

In the intent economy, value is created when a human intention is understood, routed, executed, verified, and settled.

However, if this layer is controlled by centralized AI platforms, several risks emerge:

* User intentions may become proprietary platform assets.
* AI decisions may be shaped by hidden commercial incentives.
* Sponsored execution paths may replace user-aligned outcomes.
* Agent actions may occur without auditable consent.
* Users may lose ownership of their intent history.
* Tool creators and compute providers may be locked inside closed ecosystems.
* Verification may depend on institutional trust rather than open proof.

OM World proposes a decentralized alternative.

## 2. Vision

OM World is built around three principles:

### AI Is the Engine

AI provides the reasoning, planning, generation, coordination, and execution capacity required to fulfill complex human intentions.

### Crypto Is the Law

Cryptography, smart contracts, signatures, hashes, attestations, staking, and settlement rules provide the verifiable structure required for an open intent economy.

### Humanity Owns Its Intentions

The user, organization, or community that declares an intention remains the sovereign originator of that intention.

OM World is designed to make intentions:

* expressible
* executable
* verifiable
* composable
* auditable
* economically meaningful
* user-owned

## 3. Core Concepts

### 3.1 Intent

An intent is a structured expression of a desired outcome.

It may begin as natural language:

“I want to compare cloud servers under $100 per month for a latency-sensitive trading bot.”

But within OM World, it should be transformed into a structured object containing constraints, permissions, budget, risk preferences, tools allowed, verification requirements, and settlement rules.

### 3.2 Intent Originator

The person, organization, wallet, DAO, or system that declares an intent.

The originator owns the intent and defines the initial mandate.

### 3.3 Agent

An AI-powered executor that transforms an intent into a plan and performs actions through available tools.

Agents do not own the intent.

Agents act under mandate.

### 3.4 Mandate

A mandate is the explicit authorization granted by the intent originator.

It defines what an agent or tool may do, under what constraints, with what budget, for what purpose, and within what time period.

### 3.5 Tool

A tool is a registered capability that can help fulfill an intent.

Examples:

* search tools
* trading tools
* payment tools
* data tools
* code generation tools
* audit tools
* content creation tools
* procurement tools
* research tools
* scheduling tools
* verification tools

### 3.6 Execution Proof

An execution proof is evidence that a declared action or outcome occurred.

It may include:

* transaction hashes
* signed logs
* tool output hashes
* verifier attestations
* zero-knowledge proofs
* screenshots or artifact hashes
* external oracle attestations
* reproducible result records

### 3.7 Settlement

Settlement finalizes economic consequences.

It may include:

* user payment
* tool creator revenue
* agent operator fees
* compute provider rewards
* verifier rewards
* capital provider returns
* refunds
* slashing
* dispute outcomes
* reputation updates

### 3.8 Intent Ledger

The Intent Ledger is the record of declared intents, mandates, execution traces, proofs, settlements, and reputation events.

Not every detail needs to be public.

Sensitive data may remain encrypted, hashed, or stored off-chain, while proofs and commitments remain verifiable.

## 4. Protocol Architecture

OM World is best understood not as a single stack but as **three nested layers**:

1. The **12 core systems** — the modules of the mature world.
2. The **8 module groups** — how those systems organize as the ecosystem expands.
3. The **5 MVP modules** — what is actually shipped today.

This nesting matters: the MVP is not a "v0 of the full system" — it is a deliberate, minimal subset chosen so the self-growth loop can be validated before larger commitments are made.

### 4.1 The 12 core systems (mature form)

In its mature form, OM World consists of twelve interlocking systems:

| # | System | Role |
|---|---|---|
| 1 | **Intent Demand Portal** | Where users declare what they want — natural language, voice, file, multi-turn refinement, default authorizations, intent history. |
| 2 | **Capability Supply Portal** | Where supply-side participants register what they can do — tool / agent / API / human service / compute / storage / data / pattern. |
| 3 | **Intent Router** | The "brain" — classifies an intent, retrieves matching patterns, selects the fastest / cheapest / most reliable realization path. |
| 4 | **Pattern Library** | The memory — every realization is recorded as a reusable pattern with cost, time, success rate, reuse count, and reward distribution. The compounding asset. |
| 5 | **Distributed Storage Network** | Where patterns, execution traces, tool metadata, and proofs live. Begins centralized, evolves toward user-contributed storage with on-chain commitment anchors. |
| 6 | **Distributed Compute Network** | Tiered compute supply — light nodes (feedback, caching), local execution nodes (scripts, browser automation), compute nodes (LLM, embedding, inference), expert nodes (human services, audit, design). |
| 7 | **Execution Runtime** | The engine that actually invokes capabilities, composes multi-tool flows, records traces, returns results. |
| 8 | **Proof & Trace Layer** | Confirms execution happened, with what output, by whom — for settlement, reuse, and dispute resolution. Not for moral judgment. |
| 9 | **Settlement System** | The internal value flow. **MVP uses an OM Credit (OMC) ledger only — no token.** Mature form may add stablecoin settlement or other accounting layers via independent review. |
| 10 | **Value Distribution Engine** | Splits proceeds across contributors (capability providers, agent operators, compute / storage nodes, pattern creators, interface builders, core maintenance) by event-time records, not committee decisions. |
| 11 | **Node Client** | Lets ordinary users turn their device into a participating node (storage, compute, local tools, browser execution, lightweight verification) for OMC. |
| 12 | **OM World Index / Explorer** | Read-only world-state surface: how many intents are flowing, what patterns are most reused, who's contributing what, where the network is growing. |

### 4.2 The 8 module groups (organizing principle)

The twelve systems above expand into ~100 sub-modules over time. Those sub-modules cluster into eight groups:

**A. Demand modules** — web / mobile / browser-extension / voice / file / image intent input; intent clarification; user preferences; default authorization; intent history.

**B. Supply modules** — tool registry; agent registry; API registry; human-service registry; compute-node registry; storage-node registry; data-source registry; pattern submission; pricing declaration; capability testing.

**C. Matching modules** — intent classification; pattern retrieval; tool matching; compute matching; cost / time estimation; multi-path comparison; path scoring; path composition; automatic retry.

**D. Execution modules** — LLM calls; tool invocation; API calls; browser automation; local-node execution; cloud execution; multi-agent coordination; file handling; code execution; task queue.

**E. Pattern modules** — pattern creation; pattern storage; pattern retrieval; pattern reuse; pattern forking; pattern versioning; pattern success rate; pattern revenue; pattern ranking; pattern graph.

**F. Storage & compute modules** — storage nodes; compute nodes; node reputation; node rewards; data sharding; redundant backup; node liveness; local-execution environments; GPU task dispatch; storage proofs.

**G. Settlement modules** — internal credits; user top-up; task debit; revenue distribution; node payouts; tool payouts; pattern payouts; withdrawal; ledger; (future, only if ever proposed) on-chain settlement.

**H. Explorer & growth modules** — total intents; fulfillment rate; pattern reuse rate; cost-decline curve; node count; capability map; total settlement; category expansion; leaderboards; growth dashboard.

This is the long-term shape. The MVP picks five.

### 4.3 The 5 MVP modules (shipped 2026-05-18)

The MVP at https://app.omworld.one implements exactly five modules — the minimum needed to validate that pattern accumulation reduces future realization friction.

1. **Intent Demand Entry** — `Submit an Intent` web form; intent saved with `intent_id`; LLM classifies into an `intent_type`.
2. **Capability Supply Entry** — `Contribute a Capability` web form; supply types: `Tool`, `Agent`, `Human Service`.
3. **Matching Engine** — half-automatic: LLM proposes 1–3 ranked realization paths; user / operator picks one before execute.
4. **Pattern Library v0** — first execution creates a Pattern record; subsequent executions of the same `intent_type` adapt the existing pattern (smaller LLM call, faster wall time) and increment `reuse_count`.
5. **OM Credit Ledger v0** — internal accounting only; no token, no on-chain representation. Spec values: 100 OMC initial user grant, 1 OMC submission cost, 10 OMC capability reward, 5 OMC pattern-creation reward, 2 OMC pattern-reuse reward.

The MVP success criterion is the operating principle of OM World, stated as a test: **the second realization of any intent type should be easier than the first.** First production runs validated this on `community_growth.builder_recruitment` with a ~20% wall-time drop.

Everything else — wallets, on-chain settlement, distributed storage, compute network, complex governance, multi-intent breadth, mobile — is explicitly out of scope for MVP and discussed only in the long-term-target docs at [`docs/`](docs/).

## 5. Intent Lifecycle

### 5.0 MVP lifecycle (live today)

The Genesis MVP at https://app.omworld.one implements a 5-state lifecycle (per the canonical [SELF_GROWTH_ENGINE.md](SELF_GROWTH_ENGINE.md) loop):

```
submitted → classified → matched → in_execution → fulfilled
                                         ↘ failed
```

- **submitted** — user posted a `Submit an Intent` form. Stored in `intents` table.
- **classified** — LLM assigned an `intent_type` (e.g. `community_growth.builder_recruitment`).
- **matched** — one or more `realization_paths` proposed; user / operator selected one.
- **in_execution** — the chosen capability is being invoked.
- **fulfilled** — output JSON saved; a Pattern is either created (first time for this type) or reused (subsequent times), and OMC events fire.

### 5.1 – 5.7 Mature lifecycle (long-term design)

In its mature form, an intent passes through the following protocol-layer lifecycle (not all phases are implemented yet — items below the MVP scope are described in [`docs/`](docs/)):

#### 5.1 Declare

A user expresses an intention.

The system converts the intention into a structured intent object.

A user expresses an intention.

The system converts the intention into a structured intent object.

### 5.2 Bind

The user reviews and signs a mandate.

The mandate defines permissions, constraints, budgets, risks, and verification requirements.

### 5.3 Route

AI agents evaluate available tools, compute providers, capital sources, and execution paths.

The selected path should be explainable and recorded.

### 5.4 Execute

Agents and tools perform the actions required to fulfill the intent.

Each significant action produces a log or proof commitment.

### 5.5 Prove

Execution results are verified.

Proofs may be generated by tools, verifiers, smart contracts, or external attestations.

### 5.6 Settle

Payment, rewards, refunds, reputation updates, and dispute outcomes are finalized.

### 5.7 Remember

The intent, mandate, execution proof, and outcome become part of the user-controlled intent history.

## 6. Ecosystem Roles

### 6.1 Intent Originators

Users, organizations, or DAOs that declare intentions.

They define goals, constraints, and authorization.

### 6.2 AI Agent Builders

Builders who create agents capable of planning and executing intent workflows.

### 6.3 Tool Creators

Developers who create specialized tools that agents can invoke.

### 6.4 Compute Providers

Participants who provide inference, execution, storage, or specialized compute resources.

### 6.5 Verifiers

Participants who validate execution claims and attest that outcomes match declared requirements.

### 6.6 Capital Providers

Participants who supply capital for intents requiring upfront funding, liquidity, escrow, or guarantees.

### 6.7 Interface Builders

Developers who create wallets, dashboards, explorers, marketplaces, and user interfaces for OM World.

### 6.8 Governance Participants

Community members who help define rules, standards, grants, disputes, registries, and upgrades.

## 7. Verification Model

The core rule of OM World is:

**If it cannot be proven, it did not happen.**

Verification does not mean every private detail must be public.

It means that every economically or procedurally important claim should have sufficient evidence.

### 7.1 Verification Types

OM World may support multiple verification methods:

* on-chain transaction verification
* signed execution logs
* tool output hashing
* decentralized verifier attestations
* oracle-based verification
* zero-knowledge proof systems
* reproducible computation
* human arbitration for subjective outcomes

### 7.2 Proof Requirements

Different intent types require different proof levels.

A simple content generation intent may require a hash of the final artifact.

A payment intent may require a transaction hash.

A procurement intent may require order confirmation, price evidence, and delivery proof.

A financial execution intent may require state transition evidence and risk logs.

A governance intent may require vote records and quorum proof.

### 7.3 Privacy

OM World should support privacy-preserving verification.

Sensitive user data should not be exposed by default.

The protocol should support:

* private inputs
* public commitments
* selective disclosure
* encrypted records
* zero-knowledge proofs where appropriate
* off-chain storage with on-chain hashes

## 8. Economic Model

OM World is an open intent economy.

Value flows to participants who help fulfill intentions.

### 8.1 Payment Flows

A user may pay for:

* agent execution
* tool usage
* compute resources
* verification
* data access
* capital usage
* dispute resolution
* premium interfaces

### 8.2 Revenue Distribution

A completed intent may distribute value to:

* tool creators
* agent operators
* compute providers
* verifiers
* capital providers
* protocol treasury
* interface providers
* referrers or curators

### 8.3 Staking and Slashing

Certain roles may require staking to ensure accountability.

Potential staking roles:

* tool registry participants
* verifiers
* agent operators
* oracle providers
* dispute jurors
* governance delegates

Slashing may apply when participants submit fraudulent proofs, misrepresent capabilities, violate mandates, or act against protocol rules.

### 8.4 Reputation

Reputation is critical to the intent economy.

Reputation may be built from:

* successful executions
* verified outcomes
* user ratings
* dispute history
* uptime
* cost efficiency
* audit status
* stake behavior
* community review

Reputation should be portable and protocol-readable.

## 9. Settlement Asset

**No token exists. No token is planned in the Genesis phase. No party has been promised any allocation of any token or financial instrument.**

OM World's MVP uses an internal **OM Credit (OMC)** ledger — see Section 8 and the spec at [SELF_GROWTH_ENGINE.md](SELF_GROWTH_ENGINE.md). OMC is a non-transferable internal accounting unit used to record who contributed what realization, and to reward pattern creators when their patterns are reused. It is not a token, has no on-chain representation, and confers no financial right.

Any future settlement asset — if ever proposed — would require an independent, public review process for legal, economic, security, and governance risks before it could be introduced. No retroactive allocation to any party participating in OM World today is implied or owed.

The following are open research questions for any hypothetical future asset, not commitments and not roadmap:

- whether bonds, fees, and grants are better expressed in stablecoins, in OMC alone, or in a separate unit;
- whether dispute bonding and verifier compensation can be sustained without a dedicated asset;
- whether reputation-weighted participation is sufficient for governance, or requires economic skin-in-game.

These questions have no current decision, and none is forced by the Genesis MVP.

## 10. Governance

OM World should not be controlled by a single company or closed team.

Governance should evolve progressively.

### 10.1 Genesis Governance

In the Genesis phase, governance begins as open discussion, public documents, GitHub issues, community calls, and contributor review.

### 10.2 Protocol Governance

As the protocol matures, governance may include:

* proposal processes
* working groups
* contributor councils
* verifier councils
* tool registry governance
* grants committees
* dispute systems
* DAO mechanisms

### 10.3 Governance Principles

Governance should be:

* transparent
* accountable
* upgradeable
* resistant to capture
* contributor-aware
* user-sovereign
* technically grounded
* slow on values, fast on execution

## 11. Use Cases

### 11.0 MVP — supported today

The Genesis MVP supports exactly **one** intent type:

**`community_growth.builder_recruitment`** — "I want to recruit N early contributors for my project."

Submitting this intent at https://app.omworld.one/intent triggers the Genesis Builder Recruitment Generator capability, which produces a complete recruitment package: project positioning, X article, X thread, DM templates, GitHub issue plan, target builder profiles, follow-up plan. The first run creates the underlying Pattern; subsequent runs (for other projects) adapt the same Pattern at lower cost.

This choice is deliberate: the founder's own first real need was recruiting Genesis Builders for OM World itself. Grounding the MVP in a real, recurring task that the team uses *immediately* is what gives the self-growth thesis real-world weight.

### 11.1 – 11.6 Long-term candidate categories

The system is designed to expand to many intent categories over time. The following are candidate categories under consideration (none yet implemented):

#### 11.1 Research Intent

A user declares a research question.

Agents gather sources, summarize evidence, produce a report, and provide citations or source hashes.

#### 11.2 Procurement Intent

A user defines a budget and constraints.

Agents compare vendors, produce a decision record, and optionally execute purchase through authorized payment tools.

#### 11.3 Code Intent

A user requests a software task.

Agents generate code, run tests, produce artifacts, and record test logs as proof.

#### 11.4 Audit Intent

A user submits a smart contract or protocol.

Agents identify risks, generate findings, produce reproducible proof-of-concepts, and record evidence.

#### 11.5 Content Intent

A user wants a campaign, article, video script, or social thread.

Agents generate outputs, track versions, and record artifact hashes.

#### 11.6 Financial Intent

A user defines a trading, treasury, or yield strategy under strict constraints.

Agents execute only under signed mandates and verifiable risk parameters.

## 12. Roadmap

### Phase 0 — Genesis

* Establish project identity
* Publish manifesto
* Publish litepaper
* Open GitHub organization
* Open X account
* Publish visual language system
* Invite founding contributors

### Phase 1 — Protocol Specification

* Intent Schema v0.1
* Agent Mandate v0.1
* Execution Proof v0.1
* Tool Registry v0.1
* Verifier Role v0.1
* Contributor Framework v0.1

### Phase 2 — MVP (✅ shipped 2026-05-18, live at https://app.omworld.one)

The five MVP modules that actually shipped (per [SELF_GROWTH_ENGINE.md](SELF_GROWTH_ENGINE.md) and `OM_World_MVP_Development_Spec_v0.1`):

* Intent Demand Entry (web form + LLM classification)
* Capability Supply Entry (web form, types: Tool / Agent / Human Service)
* Matching Engine (LLM-routed, half-automatic)
* Pattern Library v0 (Pattern record + adaptive reuse)
* OM Credit Ledger v0 (internal OMC accounting only, no token)

First seeded capability: Genesis Builder Recruitment Generator (intent type `community_growth.builder_recruitment`). Self-growth verified on first production runs with ~20% wall-time drop between fresh and adapted realizations. See ROADMAP §"Phase 2 — MVP Prototype" for the full shipped-vs-deferred breakdown.

### Phase 3 — Testnet

* Smart contract registry
* Verifier staking experiment
* Tool creator onboarding
* Agent execution records
* On-chain settlement prototype
* Dispute process experiment

### Phase 4 — Open Intent Economy

* Multi-agent execution
* Multi-tool marketplace
* Reputation system
* Governance modules
* Grants program
* Ecosystem partnerships
* Developer SDKs

## 13. Open Questions

OM World is early.

Important open questions include:

* How should intents be structured without limiting human expression?
* Which parts of execution must be on-chain, off-chain, private, or public?
* How should subjective outcomes be verified?
* How can agent decisions be made explainable without exposing sensitive data?
* How should tool creators be rewarded?
* How should bad tools be penalized?
* How can governance avoid capture?
* How can the protocol support both human users and autonomous agents?
* How should privacy and verification be balanced?
* What is the minimum viable proof for each intent category?

## 14. Conclusion

OM World is an attempt to build the protocol layer for the decentralized intent economy.

It starts from a simple premise:

Human intention should not be owned by platforms, auctioned by advertisers, or executed by black boxes.

A new world requires new laws.

AI is the engine.
Crypto is the law.
Humanity owns its intentions.

**One Mind, One World.**
