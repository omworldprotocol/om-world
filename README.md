# OM World

**One Mind, One World.**

OM World is a self-growing intent realization network.

It connects what people want with the capabilities that can deliver it, and turns every realization into a reusable pattern so the next intent of the same kind is easier, faster, and cheaper to fulfill.

We believe human intention should not be owned by AI platforms, auctioned by centralized systems, or decided by black boxes. Intent belongs to the one who declares it.

## What is OM World?

OM World is an open protocol that links three sides:

- **Intent demand** — what people want realized.
- **Realization supply** — the tools, agents, and humans that can deliver it.
- **A growing Pattern Library** — the memory of every successful realization, reusable next time.

AI provides the execution power.
Crypto and verifiable records provide the rules, settlement, and audit trail.
Humans retain sovereignty over their intentions and own the patterns they create.

The single success criterion is simple: **the second realization of any intent type should be easier than the first.**

## Core Principles

1. **Intent Sovereignty**  
   Every intention belongs to the person or entity that declares it.

2. **Verifiable Execution**  
   If an outcome cannot be proven, it did not happen.

3. **Open Protocol, Not Closed Platform**  
   OM World is designed as a public protocol, not a company-controlled application.

4. **AI as Engine, Crypto as Law**  
   AI turns intent into action. Crypto makes authorization, payment, execution, and outcomes verifiable.

5. **Composable Intent Tools**  
   Builders can create tools, agents, registries, verifiers, and interfaces that plug into the same intent economy.

## The Intent Lifecycle

1. **Declare** — a user expresses an intention.
2. **Bind** — the intention becomes a signed mandate.
3. **Route** — AI agents select tools and execution paths.
4. **Execute** — tools and agents perform the required actions.
5. **Prove** — results are hashed, attested, or verified.
6. **Settle** — payments, rewards, reputation, and records are finalized.
7. **Remember** — the intent, mandate, proof, and outcome become part of the user-owned intent history.

## Ecosystem Roles

- Intent Originators
- AI Agent Builders
- Tool Creators
- Compute Providers
- Verifiers
- Capital Providers
- Interface Builders
- Governance Participants

## Core Documents

- **[SELF_GROWTH_ENGINE.md](SELF_GROWTH_ENGINE.md)** — How OM World makes intent realization easier over time. The self-growth engine, the pattern library, the two-sided world, and the minimal core rules. **Start here to understand how the system is meant to work.**
- [MANIFESTO.md](MANIFESTO.md) — The philosophical foundation.
- [LITEPAPER.md](LITEPAPER.md) — The protocol overview.
- [GOVERNANCE.md](GOVERNANCE.md) — How OM World is governed.
- [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md) — The Co-builder system for early contributors.
- [CONTRIBUTORS.md](CONTRIBUTORS.md) — Public attribution of those who have shaped OM World.
- [docs/](docs/) — Spec drafts for Intent Schema, Agent Mandate, Execution Proof, and Tool Registry.

## Genesis MVP — Try it

A running minimal MVP is deployed at **https://app.omworld.one**:
two entry points (Submit an Intent / Contribute a Capability), an LLM-classified intent router, a
Pattern Library that captures every realization, and an internal OM Credit (OMC) ledger.

Source layout: `app/` (Next.js App Router), `lib/` (LLM routing + matching + patterns + credits),
`prisma/schema.prisma` (7 tables per spec). LLM calls route through OpenClaw GPT-5.5 with
DeepSeek auto-fallback. Deployment notes: [`scripts/deploy/README.md`](scripts/deploy/README.md).

## Current Status

OM World is in its Genesis phase. The Genesis MVP shipped on 2026-05-18.

Now live:
- **Genesis MVP** at https://app.omworld.one — Intent Demand Entry, Capability Supply Entry, Matching Engine, Pattern Library v0, OM Credit Ledger v0.
- **First seeded capability**: Genesis Builder Recruitment Generator (for the first intent type, `community_growth.builder_recruitment`).
- **Self-growth loop validated**: in side-by-side runs of the same intent type, the second realization completed in ~20% less wall time than the first by adapting the existing pattern instead of regenerating from scratch.

Published:
- Manifesto v0.1, Litepaper v0.1, Brand v0.1
- SELF_GROWTH_ENGINE.md v0.1 — the canonical engine architecture
- Genesis Builder contribution framework (GENESIS-BUILDERS, CO-BUILDER-ONBOARDING)
- Spec drafts in `docs/` (Intent Schema, Agent Mandate, Execution Proof, Tool Registry, Intent Lifecycle, Economic Model) — these describe the protocol-layer long-term target; the MVP currently implements a simplified subset.

In progress:
- Growing the capability supply side beyond the seeded recruitment generator.
- Seeding the second pattern (second intent type, TBD).
- Genesis Builder primitive freezes (Intent Schema and Execution Proof reviews underway).

## Join the Genesis

We are looking for:

- AI Agent builders
- Crypto protocol engineers
- Smart contract developers
- Designers
- Researchers
- Writers
- Community builders
- Governance designers
- Security researchers

If you believe human intention should be sovereign, verifiable, and executable in an open world, you are invited to help build OM World.

## Genesis Issues

The first OM World Genesis issues are now open.  
Builders, researchers, designers, writers, and protocol contributors are invited to join.

**One Mind, One World.**

