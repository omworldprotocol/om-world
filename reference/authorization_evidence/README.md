# Offline authorization/evidence reference

Bounded implementation of `omworld.authorization-evidence.v1-draft` revision 2, pinned to the exact schema digest. Python 3.11+; no tool invocation, model call, network resolver, chain client or production service. Existing SDK/runtime and legacy formats are untouched.

Code is Apache-2.0 under the existing repository license. This README is CC-BY-4.0. Deterministic fixture keys, signatures, approvals, channel claims and outcomes are **synthetic engineering data**, not actual consent, participation, payment or delivery.

## Install and verify

Use a dedicated environment; `requirements.lock` freezes the tested direct/transitive versions (not platform wheel hashes):

```sh
python3 -m venv .venv-offline
.venv-offline/bin/pip install -r reference/authorization_evidence/requirements.lock
.venv-offline/bin/python -m unittest discover -s reference/authorization_evidence/tests -t . -v
```

Full independent checks require Node.js and OpenSSL `pkeyutl` with Ed25519 support. Missing independent engines fail the tests, rather than silently skip. No test connects to external services.

The read-only CLI accepts an export directory with `export.json`: `{ "bundle_ref": <profile Ref>, "artifacts": { "sha256:<digest>": "relative-file" } }`. Actual bytes must match digests. No path may escape the directory, no URLs are fetched, and the default total byte limit is 64 MiB. JSON dependencies must be RFC8785 canonical bytes; duplicate members, non-I-JSON numbers and unknown schema fields fail.

```sh
.venv-offline/bin/python -m reference.authorization_evidence \
  --export /absolute/path/to/export \
  --schema docs/profiles/authorization-evidence-v1-draft.schema.md \
  --schema-digest sha256:INDEPENDENTLY_PINNED_CANONICAL_SCHEMA_DIGEST \
  --principal ed25519:INDEPENDENTLY_CONFIGURED_PUBLIC_KEY \
  --now 2026-10-21T00:05:00Z --history-as-of 2026-10-21T00:05:00Z
```

Arguments above are descriptive placeholders. Never take the principal, schema pin or history freshness assertion from an untrusted export. The CLI checks evidence/authority but returns `VERIFIED_WITH_BUDGET_PENDING`, never “ready to execute.” Hash identity, signature attribution and reported physical events are distinct.

## B4: single-deployment ledger

`Ledger(path, deployment, Ed25519PrivateKey, checkpoint=None)` uses SQLite WAL + FULL synchronous transactions. Monetary values are arbitrary-precision integer decimal strings in DB and signed log. API callers are local trusted authority code, not remote clients; possession of the DB and authority key is a trust boundary. Each reservation atomically records all shared Intent/Acceptance/Consent/delegation accounts, invocation and authority nonce bindings and a signed event. It reserves maximum spend **including fees**; actual final spend must include all charged fees and fit that reservation. There is no price oracle or automatic currency conversion.

`reserve` returns `new_reservation` once; retry returns the existing reserved/consumed/released state, not permission to execute again. `finish(..., 'consume', actual_integer)` finalizes spending and releases unused reservation. `finish(..., 'release')` releases a definitely unused reservation. No automatic timeout release: unknown external action status remains reserved and requires explicit authority adjudication. No external action API is supplied.

`export()` provides a signed implementation-local checkpoint/log. `audit(checkpoint)` replays signatures, sequence/hash linkage, account/nonce/reservation state and compares materialized tables. **The implementation-local event format includes multiple shared accounts and is not a wire-format BudgetEvent substitution.** The profile's BudgetProfile specifies the authority and policy; its optional BudgetEvent references do not establish runtime atomicity. The live local authority API and independently held checkpoint supply B4 state. Legacy/profile schema is unchanged.

The checkpoint must be retained outside the rollback domain under independent caller control. It is a minimum prefix anchor; a caller holding an older checkpoint can detect loss only up to that checkpoint, not every later suffix. A DB/log rolled back together cannot detect itself without an external newer anchor. Atomicity is local to a single SQLite writer domain, not cross-host exactly-once. No distributed ledger, key vault, anti-root-compromise or physical outcome guarantee is claimed.

`admit(store, trust, request, index, ledger, checkpoint)` reruns pre-call authority checks (not a completed-proof check), ensures ledger authority/deployment matches the principal-consented BudgetProfile, audits the independent checkpoint and reserves that one invocation. It returns `RESERVED_NO_ACTION` or `ALREADY_RECORDED_NO_ACTION`; it does not execute. Admission of a multi-invocation plan is **per invocation**, not all-or-nothing batch. Do not reserve future steps then infer they executed. Direct `reserve` expects already verified limits; use `admit` for untrusted exports.

## B5: supported semantics and explicit refusals

Supported: strict bytes/schema/JCS and IDs, fixed pure Ed25519-over-SHA256 signature input, principal/role trust, mandatory Consent, finite scope and deny checks, delegation and time checks, typed dependencies, exact approvals and attributable channel receipts, state/config evidence binding, linear flat/chained proof association, artifact-digest outcomes, per-invocation atomic admission, and a pinned single-relayer assertion profile. Key-history freshness/time inputs are explicit relying-party assumptions, not proven by signed timestamps alone.

The implementation requires Intent.evidence_requirements bytes to be exactly `{ "profile": "omworld.authorization-evidence.v1-draft", "evidence_profile_ref": <pinned manifest EvidenceProfile ArtifactRef> }`. Other application evidence policies are `UNSUPPORTED`; no unknown policy is ignored. Success criteria support only `{ "kind": "exact-artifact-digests", "digests": [...] }` equal to aggregate artifact refs, with matching `success_claim.artifact_digests` and exported bytes. Subjective evaluator profiles are unsupported, not silently accepted. Every applicable identity history must be supplied and fit caller's independently trusted history-as-of checkpoint.

Parent deny preservation is intentionally conservative: equivalent but differently encoded deny sets may be rejected. Strict narrowing uses an exact finite witness search for this resource/time/upper-budget grammar, not token membership or reordered set differences. Root-signed delegation establishes its finite scope; nested delegation narrows, and Acceptance/actions fit the final credential. Unavailable, conflicting or unsupported dependency semantics do not produce green authorization.

Explicitly unsupported: tool-native attestation suites (zkTLS/TEE/etc.), RFC3161 compromised-key exception validation, subjective outcome evaluation, parallel/Merkle proofs, heterogeneous relay paths, arbitrary scope patterns, cross-deployment concurrency/duplicate physical fulfillment, legacy general-purpose verification or migration. Compromised/revoked keys return unavailable instead of accepting without a trusted sidecar. A relayer/channel/provider/custodian signature remains an attributable claim, not native chain finality or human gesture truth. No live adapter exists. This bounded implementation does not close #4–#8 or qualify every profile capability.

## Tests and independent evidence

Fixtures build signed synthetic exports; they are not the only evidence. Independent checks use the published [RFC8032 §7.1](https://www.rfc-editor.org/rfc/rfc8032#section-7.1) Ed25519 test vector, [RFC8785 Appendix B](https://www.rfc-editor.org/rfc/rfc8785#appendix-B) finite-number vectors, Node/V8 independently computed canonical bytes/object IDs and OpenSSL verification of the profile's 32-byte digest signature input. RFC vector data retain their original source attribution. No RFC implementation code was copied. Node cross-check covers the tested corpus, not every possible JSON value or a certified implementation.

Ledger tests include contention for the last unit, authority nonce replay, multiple shared ceilings, oversized integers, conflicting finalization, crash-before/after-commit recovery, materialized nonce/state tampering, log tampering and caller-held checkpoint rollback detection. Semantic tests cover consent, roles, approval, chain/context swaps, closed schemas, missing bytes, replay and explicit unsupported cases. Test success is bounded engineering evidence, not runtime honesty, service adoption or scientific discovery.

## Pre-call request versus historical proof

Pre-call request is an implementation-local object with exactly intent_ref, acceptance_ref, consent_refs, approval_refs, dependency_manifest_ref, invocation_refs and exported_evidence_refs. Invocation list covers the fixed plan; exported evidence needs channel receipts, not future tool outputs or execution proofs. It deliberately is not an EvidenceBundle or a new profile wire object. Pass it to `Verifier.authorize` or `admit`; passing a completed EvidenceBundle as a fresh request fails. The caller must independently set `Trust.active_intent_ids` and history_as_of equal to now, reflecting an authoritative cancellation/status checkpoint. A bundle cannot self-declare that it is currently active. These trust assertions are explicit local inputs, not a live status service implemented here.

The CLI can inspect a request using `--authorization-request /absolute/request.json --active-intent sha256:...` with the same export bytes/schema/trust flags. It remains read-only and does not reserve funds. Ledger reservation uses the Python `admit` API and an independently held ledger checkpoint. Neither return value asserts actual tool execution. The historical proof verifier and pre-call admission serve different temporal purposes; no after-the-fact proof manufactures pre-call permission.
