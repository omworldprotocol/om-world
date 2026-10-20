# Agent Mandate — responsibility and open design questions

> **Non-normative editorial appendix.** This document distinguishes existing design text, editorial interpretations and unresolved questions for [issue #4](https://github.com/omworldprotocol/om-world/issues/4). It does not amend the wire format, signing rules, scope invariant, permission policy or protocol version. The issue remains open. Review scenarios are not executed tests; no deployment or security qualification is established.

Source baseline: [OM World be26d31744493f5d12dc2492e6768571c10a34b1](https://github.com/omworldprotocol/om-world/tree/be26d31744493f5d12dc2492e6768571c10a34b1). Section references below refer only to that revision:

- [I: Intent Schema](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/docs/intent-schema.md): Fields, executor, Canonicalization.
- [M: Agent Mandate](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/docs/agent-mandate.md): Purpose, Fields, scope tokens, Identity model, Executor constraint, Composition, Scope narrowing, Open questions.
- [T: Tool Registry](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/docs/tool-registry.md): Registration, Discovery, Deprecation, Open questions.
- [P: Execution Proof](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/docs/execution-proof.md): Envelope, Step record, Canonicalization, Key revocation states, Verifier responsibilities.
- [L: Intent Lifecycle](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/docs/intent-lifecycle.md): Transitions, Timeouts, Replay & double-fulfillment.

See the [non-normative joint decision inventory](authorization-permission-decisions.md) for linked authorization, permission-source and version-binding options. All decisions remain UNDECIDED; no option or protocol rule is adopted, and issues #4/#6 remain open.


## Reading labels

- **C — Current draft text:** explicitly stated in the pinned source. “Current” means documented design, not deployed behavior or proven security.
- **E — Editorial interpretation:** explanatory prose exposing a distinction in the existing drafts. It is not a new normative requirement, field or choice of unresolved mechanism.
- **U — Unresolved design:** the cited drafts do not fully specify the relevant mechanism or relationship. Listing the question does not resolve it or establish a pass/reject algorithm or consensus.

## 1. Responsibility table

| Stage | Responsible party / signed object | C: what the source actually states | E: editorial interpretation | U: remaining decision |
|---|---|---|---|---|
| Principal authorization | Principal signs Intent; I Fields/Canonicalization | `principal`, `body`, optional `constraints`, expiry and signature describe the user-issued intent. Optional `attestation` fixes acceptable evidence. | Principal authorization and Agent acceptance are separate responsibilities. An Agent signature alone does not establish principal consent to extra authority. | Constraints are loosely typed. Missing constraints, policy composition, consent evidence and complete revocation propagation are not a fully specified authorization algorithm. |
| Executor selection / activation | Agent signs `executor.commitment` over intent ID + agent ID; I executor | Creation-time and recommended activation-time binding are described. Once executor is bound, M requires the root identity to match. | Acceptance binds accountability to an agent; it must not be described as principal signing the Agent Mandate. | How activation-time data binds to an already principal-signed Intent without changing its signed/hash input is not closed. No signed-object mutation or new activation artifact is selected here. |
| Agent acceptance | Agent signs Mandate canonical hash; M Purpose/Fields | `intent_id`, `agent`, `plan_hash`, `bond`, `fee_quote`, `tools_declared`, `deadline`, `signature`; commitment to attempt fulfillment. | A fee quote, bond or self-imposed deadline is an offered commitment, not permission to override principal limits. | Mandate canonical preimage/exclusion and identifier are not completely specified; no new formula supplied. Relationship among budget, quote and charges needs a decision. |
| Delegated signing | Root identity issues scoped delegation to operational signing keys; M Identity/Scope narrowing | Verifier walks chain to `agent`, validates expiry/scope and monotonic narrowing, with both issuance and concrete-action checks. Executor match applies to root identity. | Key delegation is distinguishable from appointing a different executor and from assigning a sub-task. Possession of a key alone is not the documented authority check. | Credential wire format, chain reference/storage, effective revocation, exact covering predicate and strict-subset semantics remain incomplete. Planned `executor.delegates` is not a current v0 field. |
| Tool discovery/resolution | Registry/provider exposes metadata; invoking Agent chooses a resolved tool | M tokens refer to tool_id/scope/expiry; endpoint rotation is deployment detail. Material trust changes require re-consent. T exposes operation/confirmation/stateful attributes. | Reachability and discovery do not themselves demonstrate authorization; URI rotation and trust-policy change are different cases. | Operation-class encoding in M, version pinning, authority of registration versus deployment overrides, and the precise re-consent boundary depend on #6. |
| Concrete action | Operational signer/runtime attempts a particular invocation; principal supplies confirmation where required | M requires runtime scope satisfaction as well as issuance narrowing. T defines human-in-loop and restricted confirmation modes, and calls above the declared class are mandate violations. | Review the concrete resource, operation and time, not just matching scope names. A post-execution proof does not substitute for required prior consent. | No complete permission-composition algorithm, action receipt schema or approval evidence binding is selected. Unknown permissions cannot be labelled authorized by this draft. |
| Execution claim / review | Agent signs aggregate Proof; tool may attest steps; verifier evaluates | P verifies identity, plan, attestations, key state and success criteria; no runtime-honesty guarantee. Stateful evidence has context requirements. | Distinguish an authorization check, attribution to a signer, and evidence of an outcome. Hash presence does not guarantee snapshot availability or truth. | Proof-to-Mandate identifier resolution, plan-commitment location and delegated proof-signature wording need alignment; custody remains #5. |
| Cancellation / expiry / key retirement | Principal, Agent, or registry according to distinct source sections | L allows principal signed cancel before IN_FLIGHT; M describes agent cancellation and expiry; P distinguishes Active/Rotated/Compromised signing keys. | Principal cancellation, agent withdrawal, credential expiry and key compromise are different events. | No universal revocation event/schema or propagation latency is defined. Do not infer that cancelling one object instantly invalidates every downstream credential. |

## 2. Field and semantic differences

The original issue's possible-field list remains historical and is not a schema to implement. The following is a gap inventory, not a field-renaming instruction.

| Historical brief / cross-document concept | Current location or absence | Label and disposition |
|---|---|---|
| `mandate_id` | Absent from M Fields; referenced by P envelope | U: define identity/resolution in a separate design decision; do not add an arbitrary UUID or hash. |
| `intent_id` | M Fields; I `id` is described as UUID in Fields but computed as SHA-256 in Canonicalization | C/U: reference exists; representation inconsistency in I needs its own explicit disposition, not a silent identifier conversion. |
| `originator`, `authorized_agent` | I `principal`; M `agent`; optional I `executor.agent_id` | E: describe conceptual relationship only. These are not automatic wire aliases; root versus operational signer matters. |
| `allowed_actions`, `forbidden_actions`, `tool_permissions`, `data_permissions` | I constraints loosely covers allowed tools; M scope token has tool_id/scope/expiry; memory namespace interface is prose | U: no complete deny precedence, resource grammar or typed data-permission object is supplied. Do not declare all original fields delivered. |
| `budget_limit` | I constraints budget concept; M `fee_quote` and `bond` | E/U: price ceiling, principal budget and slashable stake are distinct; no automatic equivalence or budget enforcement algorithm. |
| `time_limit`, `timestamp` | I issued_at/expires_at; M deadline and token expiry (default deadline); no M timestamp field | C/U: preserve current expiry defaults; exact cross-object effective bound/conflict behavior needs alignment. |
| `revocation_rules` | M delegated credentials; P key states; L cancel/expire paths | U: no single current Mandate revocation field. Retiring a key and cancelling intent are not aliases. |
| `logging_requirements`, `proof_requirements` | P steps/aggregate, I success_criteria/attestation | E/U: cross-reference existing surfaces; do not insert these historical fields into M. Evidence and logging alone do not grant permission. |
| `signature` | I principal signature; M Agent signature; operational signer chains to root | C/U: role distinction is explicit, but full M signing preimage and proof delegation validation wording need disposition. Do not choose a suite or canonical hash formula here. |
| `plan_hash` | M Fields/Plan commitment; P first chained step references a value precommitted in intent record, while I Fields lacks plan_hash | U: identify owner, location and prior binding before claiming a closed commitment path. No formula/location change in this artifact. |
| `operation_class` | T says highest class declared in mandate.tools_declared; M token table contains only tool_id/scope/expiry | U (#6): decide explicit encoding or mapping. No assumed total order across admin/destructive or invented token field. |
| `carrier`, `executor.delegates` | M Planned v0.2 additions | C: planned only. U: where delegates lives across M and I, compatibility and approval rules require design. No v0 acceptance of these fields is asserted. |
| Multi-agent mandate / sub-mandate | M Open questions, despite current operational-key delegation text | E/U: preserve open scope; root-key delegation is not proof that co-execution/sub-task delegation is solved. |

## 3. Documentation review scenarios

No signatures, calls, verifiers or experiments were executed. “Expected review result” is an interpretation of the cited draft or an explicit unresolved result, not an implementation verdict. A satisfied individual check does not establish complete invocation authority.

| ID | Paper scenario | Basis | Expected review result / necessary evidence |
|---|---|---|---|
| A01 | Principal-signed Intent, matching root executor, Agent acceptance, valid scoped chain and action inside stated coverage | C: I executor, M Executor/Scope | Listed identity/scope checks can be satisfied; inspect all signatures/objects and bounds. End-to-end authority remains U where composition/encoding is unspecified. |
| A02 | Agent signs extra payment authority never granted by principal | E: principal/Agent distinction; U: constraint composition | Do not label principal-authorized merely because Agent signed. Exact rejection algorithm/error is not specified here. |
| A03 | Mandate root differs from the bound executor | C: M Executor constraint | Current draft says invalid/rejected. Delegated operational address must be traced to root rather than directly compared as root. |
| A04 | Child token repeats a scope name but covers a wider resource or operation | C: M Scope narrowing | Scope-name membership alone insufficient; widening violates invariant. Concrete predicate grammar remains U. |
| A05 | A child credential has expired although parent/Mandate remains in time | C: M chain expiry validation | Expired link fails chain validation. Planned carrier-specific minimum expiry formula remains planned, not adopted v0 behavior. |
| A06 | Action lies outside a valid narrowed scope | C: M issuance/runtime split | Structural chain validity does not satisfy runtime coverage; concrete-action check fails. |
| A07 | Child authority equals parent, or keeps operation/resource but narrows only time | C/U: “strict subset” | Record U until scope dimensions and strictness are defined. Do not silently accept equality or alter the wording. |
| A08 | Endpoint changes with same capability versus new operator/jurisdiction/trust posture | C: M provider rotation | Ordinary deployment rotation distinguished from material trust change requiring re-consent. Evidence of unchanged trust must be identified; detailed deployment-policy boundary is U. |
| A09 | Tool is reachable/public and returned by search, but no corresponding permission evidence is shown | E responsibility table; T Discovery | Discovery alone cannot establish authorization. Missing evidence/result remains unknown, not an invented execution approval. |
| A10 | Registry class differs from deployment policy or token scope; admin versus destructive | U: T permission source, M token gap | No accepted mapping/order/override rule. Escalate as #6 design question; do not choose by numeric max or silently broaden authority. |
| A11 | Tool requires human-in-loop or restricted confirmation but no prior principal approval is evidenced | C: T confirmation | Cannot meet documented prior-confirmation requirement. Approval record format/binding remains U. Later proof is not prior consent. |
| A12 | Activation adds executor into a previously signed Intent | C: I Canonicalization; U activation binding | Changed signed/hash input cannot simply be assumed to retain old signature/ID. Record required binding design, no new object/formula selected. |
| A13 | Proof references mandate_id or anchors plan_hash with no unambiguous source | U: M/P/I gap | Documentation cannot claim resolved binding. Require explicit design disposition before interoperable acceptance criteria can be stated. |
| A14 | Principal cancels before IN_FLIGHT; key is separately rotated/compromised | C: L transitions, P key states; U propagation | Apply only the separately documented event meanings. Do not treat rotation as compromise or infer complete downstream revocation. Post-IN_FLIGHT principal cancellation not specified by the same transition. |
| A15 | Delegate key signs a valid-looking proof, but root path is absent | C: M Identity; U P wording alignment | Cannot demonstrate required delegation path. Clarify reconciliation with P's same-identity rule; no new verifier implementation claimed. |
| A16 | Another agent is assigned a sub-task using the current operational-key chain | C/U: M Open questions | Do not conclude sub-mandates/co-execution implemented. Requires separate design. |
| A17 | Stateful memory step includes context_hash but snapshot cannot be obtained | C: P Threat model/Open questions | Hash does not prove availability or truth; replay cannot be established from hash alone. Custody responsibility remains #5. |

## 4. Editorial review checklist

- All responsibility rows identify the actor, object, current source and unresolved boundary.
- Historical possible fields are compared with actual tables; planned fields are never presented as current v0 fields.
- Each scenario states whether it has a current textual rule, editorial interpretation or unresolved design. No synthetic PASS or runtime measurements.
- No new wire fields, hash algorithms, signature suite, authorization composition, revocation scheme or delegation mechanism is adopted.
- Editorial interpretations do not resolve any U item; original source definitions, discussion, attribution and licenses are preserved.
- Merging this editorial appendix records the distinctions and unresolved questions. It does not close #4, freeze a version, qualify an implementation or resolve #5/#6.

## Attribution and licensing

© OM World Protocol contributors, licensed under CC-BY-4.0. Source: https://github.com/omworldprotocol/om-world at the fixed revision above. This adaptation and new editorial prose are provided under the same CC-BY-4.0 documentation license; full text: [LICENSE-DOCS](../LICENSE-DOCS). Changes made here: responsibility and gap tables, clearly marked editorial interpretations, review scenarios and acceptance checklist. Contributors retain copyright in their contributions.

The existing [CONTRIBUTORS.md](https://github.com/omworldprotocol/om-world/blob/be26d31744493f5d12dc2492e6768571c10a34b1/CONTRIBUTORS.md) remains authoritative for historical attribution. Relevant source provenance includes the [original #4 update](https://github.com/omworldprotocol/om-world/issues/4#issuecomment-4456078254) (scope tokens, memory binding and context_hash), the Mandate's cited aeoess/agent-passport-system review for root identity/narrowing, and the existing Nolpak14 attribution for commerce-axis decomposition and planned additions. Kawacukennedy's Intent executor-binding contribution remains attributed in the original record. This summary does not appoint new authors/reviewers, claim their agreement with this appendix, or imply participation/endorsement in MSEC. External works are referenced through existing source attributions; their current implementations were not audited or copied here. Original contributor and license files are unmodified.
