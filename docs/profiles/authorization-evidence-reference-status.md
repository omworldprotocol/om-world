# B4/B5 bounded engineering implementation

This adds an isolated [offline Python reference](../../reference/authorization_evidence/README.md), leaving legacy SDK/runtime, schema, wire formats, hashing/signature formulas, attribution and licenses unchanged. Profile design adoption and bounded engineering test results are distinct from full profile interoperability or production deployment.

## Delivered

- B4: single-deployment SQLite WAL/FULL transaction core; atomic shared Intent/Acceptance/Consent/credential account reservations, replay/authority nonce binding, final consume/release and signed audit log/checkpoints. Large money values use exact integer decimal strings. Crash recovery does not re-execute or automatically release unknown outcomes.
- B5: offline strict JSON/I-JSON/JCS/schema/ID/Ed25519 verification, mandatory principal Consent and roles, finite scope/delegation/time checks, typed dependencies, approval claims, exact Invocation/Context/proof step association, artifact-digest outcomes and separately gated budget admission. No network resolver, tool call or external adapter.
- Independent engineering checks: RFC8032 published Ed25519 test vector and RFC8785 Appendix B finite-number vectors; Node/V8 cross-check of canonical bytes/object IDs; OpenSSL CLI verification of the profile's digest-signature input. These are independent vectors/engines, not independent human review or full interoperability certification.

The engineering suite currently has **69 tests**, including concurrent contention, crash-before/after-commit, checkpoint rollback, materialized nonce/state and log tampering, supersized integer budgets, consent/role/context/chain failures and offline admission. Tests use synthetic keys/approvals/outcomes only. An initial large-integer event-serialization failure was repaired by storing decimal strings in the signed event payload as well as SQLite state; the failed run is retained in the delivery evidence. No claim of first-run perfection is made.

Source vectors: [RFC8032 §7.1](https://www.rfc-editor.org/rfc/rfc8032#section-7.1), [RFC8785 Appendix B](https://www.rfc-editor.org/rfc/rfc8785#appendix-B). Vector data retain original IETF source attribution; no RFC implementation code was copied.

## Result and trust boundaries

Historical proof verification returns `VERIFIED_WITH_BUDGET_PENDING`, never fresh execution authority. Separate pre-call requests require independently configured current active-Intent/history checkpoints and return `AUTHORIZED_WITH_BUDGET_PENDING`. Per-call admission into the principal-consented local ledger returns `RESERVED_NO_ACTION` only for a newly committed reservation. Idempotent retries return `ALREADY_RECORDED_NO_ACTION`, never a fresh execution authorization. No API executes a tool or payment.

Ledger event/checkpoint export is an implementation-local signed accounting format containing all shared accounts. It does not substitute for the specification's BudgetEvent wire object or prove external budget history by itself. Profile BudgetProfile binds authority/deployment; runtime admission uses that local authority state and a caller-held independent checkpoint. The original schema is unchanged. The local authority DB/key and checkpoint retention are explicit trust assumptions. An old checkpoint can only anchor its own known prefix; a DB rolled back with its internal log cannot self-detect all missing later events.

## Remaining blockers / unsupported cases

The minimal single-deployment ledger and bounded offline verification are implemented and engineering-tested. **Full B4/B5 deployment or universal profile qualification remains unclaimed.** External checkpoint/authoritative history operations, persistent real key custody, independent security review, multi-platform SQLite/filesystem behavior and actual channel/provider/custody/relayer behavior remain unvalidated operational concerns.

Unsupported inputs fail explicitly: general legacy verification/migration; native tool attestation suites; compromised-key RFC3161 exception validation; subjective outcome evaluators; arbitrary resource grammars; parallel/Merkle proofs; heterogeneous relayers; cross-deployment concurrency/duplicate physical fulfillment. The single-relayer path verifies only an attributable pinned-relayer assertion, not native chain finality. The reference supports only pinned exact evidence requirements and exact-artifact-digest success criteria; unknown application policies do not silently pass. These limits do not broaden supported scientific or real-world outcome claims.

Issues #4–#8 remain open; original issue bodies/discussions are retained. #7 remains UNKNOWN/deferred and #8 six remaining translations deferred. No live tools, external adapters, scientific experiments, contributor contact or announcement. No historical contributor is claimed to have reviewed or endorsed the implementation. New code is Apache-2.0; prose remains CC-BY-4.0 under existing scopes.
