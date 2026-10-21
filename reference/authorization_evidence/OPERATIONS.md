# Local checkpoint, authorization status and time contract

**Scope:** single-deployment offline reference. This is the caller/operator contract, not a new live service, adapter, key vault or claim that independent storage/real status sources are already deployed. Existing schema, legacy formulas and public profile identifiers remain unchanged. No API invokes an action.

## State and transaction ownership

`reserve(checkpoint=...)` verifies the supplied independently held prefix, audits state, binds nonces, updates all ceilings/reservations and appends its signed event under **one BEGIN IMMEDIATE transaction**. The production-facing `admit` path requires a checkpoint and uses this operation; it no longer checks a prefix in a separate read before reserving. Direct low-level reserve without a checkpoint remains a trusted local authority API and does not promise rollback protection.

Standalone `audit` owns a deferred read transaction. Its first SELECT pins a SQLite snapshot for every log/account/reservation/nonce/checkpoint query. Concurrent WAL writers may commit without mixing their newer tables with an older log. Success commits only that read transaction; errors roll it back. If the connection already has a transaction, audit reuses it and neither commits nor rolls it back. Caller controls the outer lifetime; no nested BEGIN or mutation is added by audit.

Ledger connections and Verifier instances are local per-thread/per-request objects; do not share a mutable Verifier mode or a SQLite connection across threads. Multiple independent Ledger connections may serialize writes to the same protected local DB. Single deployment still does not mean distributed exactly-once or external action atomicity.

## What must be retained

| Record | Owner and storage | Required binding / trust |
|---|---|---|
| SQLite DB and live WAL | Ledger authority; protected local transactional storage | deployment ID, fixed authority key, accounts/nonces/reservations and complete signed events; use a consistent SQLite backup rather than copying an arbitrary DB file without its active WAL |
| Signing key | Same configured ledger authority; access restricted to local authority process | Pinned public identity/deployment; never place private key in export/checkpoint/test receipts or untrusted request |
| Independent ledger checkpoint | Relying party/operator, **outside the DB/backup rollback domain** | Signature, authority, deployment, sequence/head; retain the newest accepted high-water checkpoint and its update provenance independently |
| Principal/schema configuration | Relying party's trusted configuration | Exact principal public key, supported profile/revision and canonical schema digest; never import trust anchors from the untrusted export |
| Active Intent status | Relying party's authoritative cancellation/status snapshot | Actual source identity, exact active Intent IDs, source revision/hash, effective/as-of time and acquisition provenance; absence of a cancellation in an incomplete source is not evidence of active status |
| Key/delegation history | Relying party's authoritative identity-history checkpoint and exported signed events | Completeness/freshness as-of time, roots/keys/event sources; the history_as_of input is an independently established assertion, not a timestamp the export can choose |
| Verification clock | Relying party's trusted clock/operation context | UTC instant and explicit source/freshness policy; user-supplied JSON time is not independent proof of wall time |

The code verifies the supplied checkpoint/signatures and declared relations. It **does not provision** non-rollback storage, a remote status oracle, clock synchronization or history completeness. Those are preconditions that must be established operationally; otherwise return unavailable/stop admission, never fabricate an active set or fresh timestamp.

## Update order and crash windows

1. Obtain current trusted active-Intent/history/clock inputs; authenticate them against the configured sources. In preflight, history_as_of must equal now and the exact Intent ID must be in the independently supplied active set. Preserve the source snapshot/provenance with the request audit record. Do not relabel an old history with a new time.
2. Verify pre-call request and call `admit` with the newest independently accepted ledger checkpoint. A stale checkpoint only proves its own old prefix; the library cannot decide whether a newer checkpoint was concealed. The caller must not deliberately substitute an older accepted anchor.
3. Reserve commits DB state/nonces/signed event atomically. `RESERVED_NO_ACTION` means **no action executed**. Export the consistent signed checkpoint after that commit. Persist/update it outside the rollback domain before any hypothetical execution handoff. No such handoff/tool is implemented here.
4. Independent checkpoint persistence should authenticate the record, reject decreasing sequence or conflicting same-sequence head, write/flush temporary bytes, atomically replace, and flush the directory (or equivalent durable storage transaction). Preserve predecessor/checkpoint provenance. This persistence policy is a requirement for the caller's store, not a hidden facility implemented by `Ledger.export`.
5. DB and external checkpoint store do not share a distributed transaction. If the process crashes after DB commit but before external anchor persistence, leave reservation and nonce committed; there must have been no execution handoff. On recovery validate the previous trusted prefix against recovered DB, inspect complete current history, and advance the anchor with provenance. Do not automatically execute or release the existing reservation. If action occurrence is uncertain, explicit authorized adjudication is required.
6. Following an actual, separately authorized action, record known final spend with consume or definitely-unused cancellation with release. Include all charged fees within the reservation. Then persist a new independent checkpoint. Unknown outcomes remain reserved; there is no timeout-based automatic release or retry of the external action. Consume/release reconciliation is a local authority decision, not proof of physical outcome.

## Restore and refusal rules

- New checkpoint missing from a restored DB: fail closed (`UNAVAILABLE`), quarantine the restored state and recover a complete DB/WAL/backup containing the trusted prefix. Do not “fix” it by generating a new empty checkpoint, resetting authority nonces or lowering the externally stored high-water mark.
- DB restored ahead of an older trusted checkpoint: auditing that prefix can succeed, but it does not prove all later suffixes survived. Compare with the independently retained newest anchor and recovery provenance before service resumes. Without an independently newer anchor, unknown omitted tails are a trust limitation, not a detectable condition the library can invent.
- Corrupt signature/hash/state or conflicting checkpoint head: refuse and preserve bytes. A checkpoint proves only a signed prefix under the configured authority; it does not reconstruct missing spent balances or establish external action occurrence.
- Authority/deployment key change: do not reopen/rename the old DB under a different identity. Key/deployment migration needs a separately reviewed transition contract, preserved old anchors and evidence; no automatic migration is delivered.
- Cancellation/revocation/status changes, stale source or uncertain clock: invalidate cached preflight authority and refresh from trusted sources. Re-check immediately before any future action handoff; no offline result grants indefinite future authority. The reference supplies no handoff and cannot guarantee freshness of a dishonest caller-supplied now.
- Restore status/history from an old backup: do not assert it is current by editing as-of timestamps. Recover current source-owned records or keep unavailable. Keep source revision, effective events and acquisition times distinct.

## Engineering evidence and limits

The original 69 tests remain byte-for-byte unchanged. Six added regressions cover the exact log→table interleaving while a writer commits, caller-owned transaction reuse, failure cleanup, nested failure ownership, checkpoint check inside the reserve transaction, and rejection without partial nonce/reservation state for a bad checkpoint. The interleaving is coordinated by Events/SQLite trace callbacks, not arbitrary sleeps; the reader observes the earlier complete snapshot and then the committed newer state after its snapshot closes.

Tests use synthetic local keys/state only. They do not qualify actual storage hardware, power-loss durability, independent checkpoint operations, clocks, real cancellation/history sources, live tools, payment or scientific outcomes. Native tool attestation, timestamp exceptions, subjective evaluators, parallel/heterogeneous relay, arbitrary patterns and cross-deployment guarantees remain unsupported. #4–#8 remain open; no contributor participation or endorsement is inferred.

© OM World Protocol contributors. This prose is CC-BY-4.0 under its explicit documentation notice; reference code remains Apache-2.0 under the existing repository license. No brand rights are granted.
