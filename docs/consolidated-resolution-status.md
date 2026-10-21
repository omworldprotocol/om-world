# Consolidated disposition of issues #4–#8 — 2026-10-21

This records maintainer-approved design-draft decisions, not implementation or independent conformance. [Profile](profiles/authorization-evidence-v1-draft.md) and [structural schema](profiles/authorization-evidence-v1-draft.schema.md) are separate from legacy. The historical [joint inventory](authorization-permission-decisions.md) remains a record of the earlier UNDECIDED state; the decisions below supersede that state only for the named new profile. Original options and author attributions are preserved, not retroactively rewritten as contributor agreement or community consensus.

| Item | Disposition | Residual condition |
|---|---|---|
| W01 HTTP/stateless | Editorial correction applied: input dependency, not transport, determines statelessness. | No HTTP replay qualification. |
| W02 snapshot replay | Conditional availability/procedure/assumptions stated. | No guaranteed availability/truth. |
| W03 adjacent/full proof | Local check distinguished from full aggregate/history. | Original formulas preserved. |
| D01 authorization/activation | New profile: immutable Intent and separate Agent Acceptance/Consent. | No runtime implementation. |
| D02 IDs/plan | New content-addressed objects; plan committed in Acceptance. | Legacy ID and plan differences remain legacy limitations. |
| D03 coverage | Exact finite operation/resource/time/budget coverage; no numeric class ordering. | General pattern grammars unsupported. |
| D04 permission source | Versioned baseline plus tightening-only deployment restrictions selected. | Registration truth still requires evidence. |
| D05 confirmation | New profile requires affirmative or restricted out-of-band approval. | Legacy presentation semantics unchanged; approval-channel profile needed. |
| D06 keys/revocation | Separate actor/key/event histories and action checks. | Identity-profile evidence and consumer implementation required. |
| D07 dependency versions | Immutable manifest and exact references; no latest migration. | Missing/unsupported dependencies prevent qualification. |
| D08 old mandates | Keep legacy; explicit new objects, no backfilled consent. | Historical validity is not service availability. |
| D09 discovery | Snapshot/policy/filter/ranking inputs explicit; separate authorization. | No search/runtime implementation. |
| D10 proof closure | Outer EvidenceBundle references complete proof and dependencies. | Exact mapping/profile consumer required; no old verifier support claimed. |
| E01 custody | Provider default designated custodian with signed retention/access profile. | No retention service delivered; evidence can remain unavailable. |
| E02 context | Pre-call context manifest, retrieval procedure and result evidence separated. | No replay/conformance experiment. |
| E03 configuration | Provisioner-signed config referenced in new context manifest. | Missing bytes cannot establish replay. |
| E04 multi | Required dimensions all verified under their own suites/trust roots. | No automatic external adapter or field mapping. |
| E05 cross-chain | Bounded single trust-path relay profile only. | Heterogeneous relayers/relay primitive unsupported. |
| E06 parallel | Linear only. | Parallel/Merkle/fan-out/join unsupported, future design. |
| E07 privacy/subjective | Sidecars and attributed evaluator claims, explicit claim ceiling. | No erasure/compliance/physical outcome guarantee. |
| S07 historical call | UNKNOWN; #7 open and activity deferred. | Existing records or separate disposition needed; no scheduling. |
| S08 translation | README pilot delivered; other six documents deferred; #8 open. | No translation expansion authorized. |

All #4–#8 remain open. No issue body or existing discussion is changed by this document. Design-draft decisions are now recorded for 17 items, three bounded editorial repairs are applied, and two scope dispositions remain deferred; **22 implemented capabilities are not claimed**. General delegation/sub-mandates, cross-deployment concurrent budget/double-fulfillment prevention, arbitrary resource-pattern reasoning, runtime honesty and external integration remain outside delivered capability.

## Acceptance and next gate

Checks for this tranche: closed schema/meta-schema/internal refs, exact changed-file allowlist, preserved legacy formulas, original contributor/license Git blobs, links and unchanged issues/comments. These are document/structure checks, not protocol experiments, signature verification, adapters or deployment tests. Structural examples used locally are synthetic shape checks only and not public execution evidence.

Next work is separately scoped conformance/implementation planning if requested. Unknown external profiles, budget ledger, exact identity/approval/relay evidence and unsupported capabilities block any end-to-end qualification. They do not invalidate this bounded design-document delivery. No new PR review by historical contributors, outreach, announcement, meeting, experiments or MSEC research is implied.

© OM World Protocol contributors, CC-BY-4.0. Source history and license scopes remain unchanged.
