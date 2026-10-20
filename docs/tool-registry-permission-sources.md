# Tool Registry — permission sources and open design questions

> **Non-normative editorial appendix.** Related: [#6](https://github.com/omworldprotocol/om-world/issues/6), which remains open. This compares design options and responsibility boundaries; it does not select a permission-source policy, amend existing rules, or define a runtime authorization algorithm. Review scenarios are paper cases, not executed tests. No implementation or security qualification is established.

Baseline: [OM World 4a1793babe349c1578cc0956d6eececbc565966b](https://github.com/omworldprotocol/om-world/tree/4a1793babe349c1578cc0956d6eececbc565966b).

Pinned sources:
- [T — Tool Registry](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/docs/tool-registry.md): Registration, operation_class, confirmation, Discovery, Deprecation, Open questions.
- [M — Agent Mandate](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/docs/agent-mandate.md): scope tokens, provider rotation, Identity model, Scope narrowing, Planned v0.2 additions.
- [R — responsibility appendix merged in PR #22](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/docs/agent-mandate-responsibilities.md): responsibility table, field differences, scenarios A08–A11. R is non-normative: its merge did not select a permission policy.
- [I — Intent Schema](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/docs/intent-schema.md): constraints, executor, attestation, Canonicalization.
- [P — Execution Proof](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/docs/execution-proof.md): evidence and verifier boundaries.

Labels: **C** = explicit current design-draft text, not deployed behavior; **S** = editorial recommendation or candidate safety objective, not adopted; **U** = unresolved design requiring a separately reviewable decision. A future accepted editorial note can document U without resolving it.

See the [non-normative joint decision inventory](authorization-permission-decisions.md) for linked authorization, permission-source and version-binding options. All decisions remain UNDECIDED; no option or protocol rule is adopted, and issues #4/#6 remain open.


## 1. Current text and responsibility boundaries

| Topic | C: existing text | S: interpretation/recommendation | U: not specified by this draft |
|---|---|---|---|
| Tool metadata | T includes tool_id, semantic version, provider, interface, boundary, operation_class, confirmation and stateful. | Metadata describes the tool; it is not principal consent or Agent acceptance. | Who attests the accuracy of classification, registration immutability, per-operation versus whole-tool granularity and trust in a dishonest registrant. |
| Operation class | T lists read/write/destructive/admin; says highest invoked class is declared in mandate.tools_declared and higher-class invocation violates mandate. | Compare actual operations/resources and declared coverage; do not infer safety from the name. | Complete ordering/coverage relation, especially admin versus destructive, and encoding in M's token table (tool_id/scope/expiry only). |
| Confirmation | T automatic: without human confirmation; human-in-loop: planned invocation presented to principal before execution; restricted: blocked for autonomous agents, requires explicit out-of-band principal approval. | Keep all three definitions distinct. “Automatic” does not remove other authority constraints. Presentation and affirmative approval are not interchangeable evidence. | Whether presentation requires affirmative approval for human-in-loop, freshness, actor, payload binding, reuse and approval-record format. Do not silently strengthen the current definition to a new protocol rule. |
| Permission source | T explicitly leaves registration-defined versus deployment-defined operation_class/confirmation open. | Compare alternatives and effects before selecting any. | No adopted override, precedence, effective-permission formula or policy revision schema. |
| Principal / Agent | I has principal signature and constraints; M acceptance is signed by Agent. R distinguishes principal authority, Agent acceptance, operational-key delegation and concrete-action checks. | Deployment configuration and Agent self-signature alone do not demonstrate extra principal consent. | Typed constraint composition and activation binding remain unresolved as recorded in R. |
| Credentials | M requires chain expiry/scope validation, monotonic narrowing and structural plus action checks. | Permission-source policy must account for action resource, operations and time; a matching token string is insufficient. | Scope grammar/strictness, registry scope mapping and revocation propagation. No new credential mechanism here. |
| Rotation / lifetime | M permits ordinary endpoint rotation; material trust-property changes are re-consent events. T deprecated entries remain valid for existing mandates until expiry. | Preserve the distinction between metadata changes, reduced service availability, mandate validity and authority to perform a specific call. | Version selection, changed policy against old mandates, emergency blocking and the exact re-consent boundary. Deprecation is not a blanket guarantee that every later call succeeds. |
| Discovery / evidence | T describes filtered search and check_permissions; same query + same registry state yields same ranking. P provides evidence claims, not runtime honesty. | Reachability/search results and post-hoc signatures do not themselves establish prior authorization. | How deployment state enters discovery reproducibility and what policy snapshot/evidence a verifier receives. |

## 2. Options compared — no option selected

The following are candidate design shapes, not defaults. Registration metadata and principal authorization remain distinct in every option.

| Dimension | A — Registration values fixed for an entry | B — Deployment-defined, versioned policy | C — Registration baseline + tightening-only deployment restrictions |
|---|---|---|---|
| Source of operation/confirmation | Candidate: fixed at registration; changed classifications require a distinct tool entry. This tracks the specific historical proposal. | Candidate: deployment supplies the effective classification/confirmation with a distinguishable policy revision; registry surfaces schema and deployment identity. | Candidate: registration supplies baseline; deployment may restrict the eligible action set or add requirements, without making a previously excluded action eligible. |
| Benefit | Stable reference across deployments of the same entry; simpler historical lookup if entries remain accessible. | Expresses operator-specific boundaries and changing deployment needs. | Retains a common baseline while allowing stricter local controls. |
| Main risk | Stable metadata can still be wrong. New entries can fragment discovery and alias the same interface. Immutability alone does not prove action coverage. | Same tool_id can imply different effective behavior; mutable policy may silently change what principal/Agent relied on. | “Stricter” has no complete current definition. Confirmation modes and operation classes cannot simply be sorted numerically. |
| Existing mandate | Candidate: retain its original entry; a new entry does not automatically inherit its authorization. Whether/version how resolution is bound remains U. | Candidate: record which policy revision the mandate/action relied on. Upgrade, continued use or renewed consent is a separate choice. | Candidate: a restriction may block a call without granting new power. Whether old mandates remain usable, need acknowledgement or are suspended remains U. |
| Version changes | New tool_id is the comment's proposed policy for stricter classification. Relation to T.version, immutable versions and retention must still be designed. | Distinguish tool version from deployment policy revision. A reproducible signed/committed reference is a candidate requirement, not an existing field. | Distinguish baseline revision from local restriction revision; no live-policy substitution should be assumed safe. Binding and effective dates remain U. |
| Confirmation | Each entry fixes its declared mode; approval format and treatment of existing mandates still unresolved. | Deployment defines the mode, requiring transparency about exact mode and revision used. This option alone does not legitimate weakening principal requirements. | Candidate: requirements accumulate rather than disappear. Whether presentation plus out-of-band approval is needed cannot be answered by an invented linear mode ordering. |
| Evidence needed for later review | Exact entry/version, invocation, principal constraints, Agent scopes and applicable confirmation evidence. | Same, plus attributable deployment-policy revision and activation/effective-time evidence. | Same, plus baseline/restriction snapshots and explanation of why permitted actions did not expand. |
| Unresolved decision | Identifier/version semantics; authoritative registrant; correction/emergency path; old-entry discovery and aliasing. | Policy authority and schema; binding into mandate/proof; conflicts, rollback and consent. | Non-expansion predicate; conflict semantics; version binding; application to outstanding mandates and fail behavior. |

**S — suggested next step:** first publish an editorial distinction/gap inventory, not a choice of A/B/C. For a later protocol proposal, evaluate “no silent expansion of the principal-authorized action set” and attributable/versioned policy evidence as candidate safety objectives. Prefer comparison in terms of allowed concrete actions and required evidence over a `max(operation_class)` formula. This recommendation selects no override rule, signature input, field or identifier.

A future definition of C would need to show that its permitted concrete actions do not exceed the baseline and principal/Mandate constraints. This is an informal review objective, not a normative set-intersection algorithm: the sets, comparability, unknown cases and encodings are not defined. Re-labelling destructive behavior as read would be an accuracy failure, not a restriction. Likewise, adding a confirmation requirement may block use under an old workflow; it does not automatically establish principal approval of a new workflow.

## 3. Historical proposal and #4 dependencies

The [initial #6 update](https://github.com/omworldprotocol/om-world/issues/6#issuecomment-4456080462) records security metadata and lazy discovery contributions, with feedback credited there to sirkirby. [Kawacukennedy's proposal](https://github.com/omworldprotocol/om-world/issues/6#issuecomment-4817560998) recommends tool-defined defaults and deployment overrides; its concrete suggested prose fixes operation_class and confirmation for an entry and uses a new tool_id for stricter classification. The distinction between the broad “override” description and the concrete new-entry proposal should be retained, not conflated with C's same-entry restriction layer. It also suggests a verifier MUST rule; that text is **not adopted** here. Its external production claims were not independently revalidated.

The comment's inequality between mandate permission and tool classification is not a complete comparison predicate. It cannot establish the intended direction of coverage or handle non-comparable classes without further definitions. Original wording, discussion and contribution remain preserved in the snapshots and linked record.

[PR #22](https://github.com/omworldprotocol/om-world/pull/22) provides these dependencies without resolving them:

- R responsibility rows: registry/provider metadata, principal authorization, Agent acceptance and actual invocation are different responsibilities.
- R field differences: operation_class has no explicit location in M's three-field token table; no new token field is introduced by this draft.
- R scenarios A08–A11: endpoint/trust changes, discovery without consent, conflicting classifications and confirmation evidence.
- R unresolved authority composition, strict narrowing and credential revocation remain unresolved. Old-mandate treatment cannot silently resolve them as part of registry wording.

## 4. Paper acceptance scenarios

These are documentation acceptance cases, not executable vectors or results. C outcomes apply only to the stated check; S is a candidate review objective; U is an unresolved result. No full invocation is labelled authorized merely because one check passes.

| ID | Case | C baseline / limits | S review target and U decision |
|---|---|---|---|
| P01 | Registered tool/version and deployment policy agree; current mandate covers concrete resource/action; all stated checks evidenced | C: scope/action checks, metadata and confirmation meanings exist. | Enumerate relied-on objects and evidence. U: composition/encoding prevents claiming a fully interoperable authorization algorithm. |
| P02 | Registry says read but deployment/tool actually performs a transfer | C: T defines transfer as destructive. | Record semantic classification conflict; do not accept the read label as evidence. U: source precedence, classification disputes and enforcement mechanism. |
| P03 | Existing mandate targets an entry; a stricter variant is registered with a new tool_id | C: M token names tool_id. A's new-entry behavior is only a proposal. | Do not assume old authorization transfers to the new ID. U: explicit rebinding/consent and version resolution. |
| P04 | Same tool_id resolves to a new tool version while an old mandate is outstanding | C: T has version; M token has no explicit version. | Identify old and new semantics/metadata. U: pinning, compatibility, policy timing and renewal. No automatic “latest” selection chosen. |
| P05 | Deployment policy changes during a mandate's lifetime | C: no adopted policy revision field. | Compare policy at acceptance and action time; preserve both references. U: grandfathering, re-consent, blocking and evidence binding. |
| P06 | Old mandate sees a new local deny rule under candidate C | C: C not adopted; mandate validity and invocation availability differ. | A denial can reduce availability without granting authority. U: effective time, notification, old-call treatment and appeal. Do not declare the mandate universally revoked. |
| P07 | Deployment tries to change restricted to automatic | C: restricted requires explicit out-of-band principal approval; source precedence is open. | Candidate C should not remove an approval requirement. U: formal rule; do not adopt C through this example or treat approval as obtained. |
| P08 | Automatic baseline gains human-in-loop presentation | C: T's human-in-loop definition requires planned invocation presentation before execution. | Keep presentation evidence separate from approval. U: whether affirmative approval is also required and how an old workflow binds the new requirement. |
| P09 | Restricted invocation has no out-of-band principal approval | C: cannot satisfy T's restricted definition. | Record the missing evidence; U: approval record representation, recipient, payload binding and freshness. A post-hoc proof is not prior approval. |
| P10 | Human-in-loop invocation was presented but principal gave no affirmative response | C: text says present before executing, not a fully specified approval handshake. | Mark the gap explicitly. A recommendation to await approval is S, not a newly adopted current rejection rule. |
| P11 | Local policy labels admin “stricter than” destructive, using numeric max | C: definitions describe different mutation effects; no complete order supplied. | Require concrete coverage reasoning. U: comparability/order and composite tools; do not fabricate numeric precedence. |
| P12 | New version only changes endpoint versus changes operator/jurisdiction/trust | C: M distinguishes ordinary rotation and re-consent for material trust changes. | Identify which trust properties changed. U: policy predicate and evidence of unchanged properties; version bump alone proves neither. |
| P13 | Tool is deprecated while mandate has not expired | C: T says existing mandates remain valid until expiry. | Keep that statement intact. U: interaction with tightened policies, security compromise or unavailable service; no unconditional execution guarantee or emergency exception invented. |
| P14 | Policy/tool revision cannot be retrieved or is unknown | C: no adopted registry-policy unknown-version error. P's UNSUPPORTED_SPEC_VERSION is a proof-version rule. | S: do not claim authorization is established from missing evidence. U: formal fail behavior/error. Do not copy proof-version rejection into registry as new normative law. |
| P15 | Search returns same query/registry state but different local policy | C: reproducibility is stated for same registry state; filtering is documented. | State whether deployment policy participates in result state/filtering. U: reproducible policy snapshot and ranking semantics; no current guarantee across hidden config changes. |
| P16 | Provider changes confirmation without changing operation_class | C: fields are distinct. | Check each independently. U: source authority, immutability, effective date and consent; a class match cannot settle confirmation. |
| P17 | Approval was given for a different action, amount, resource, version or time | C: scope/action and restricted approval obligations exist, but full approval binding is absent. | S: surface the mismatch instead of claiming demonstrated consent. U: exact binding and replay rules, not implemented here. |
| P18 | Same scope string exists in parent and child, but resource/expiry expands | C: M covering checks and monotonic narrowing; name membership insufficient. | Preserve those current obligations; U: scope grammar and strictness remain R's unresolved design. |

## 5. Unresolved decision inventory and acceptance limits

1. Source of classification/confirmation and authority to register/correct them.
2. Tool-wide versus operation-level classification; scope grammar/operation coverage; admin/destructive comparability.
3. Tool version, policy revision, tool_id, effective date and signed/committed references; representation is not selected.
4. Existing mandate handling across policy changes, deprecation, compromises and availability failures.
5. Confirmation presentation versus approval, actor, concrete-action binding, freshness and replay.
6. Versioned policy evidence required for discovery and verifier review; failure behavior when unavailable.
7. Whether A, B, C or another shape is adopted; governance process and decision record. No rough consensus claimed.
8. T's other open questions (off-chain verification at scale and composition/aliasing) stay open; this draft cannot complete the whole Registry design.

Document acceptance requires each table/scenario to distinguish C/S/U, preserve the original restricted/human-in-loop meanings, reference R without promoting it to law, and expose the old-mandate/version gaps. It also requires unchanged original source bytes, attribution and license scope, and no claim of tests, deployment, interoperability, external approval or implementation. Merging this editorial record leaves the listed protocol questions undecided. Issue #6 remains open.

## Attribution and licensing

© OM World Protocol contributors, licensed under CC-BY-4.0. Source: https://github.com/omworldprotocol/om-world at the pinned revision above. This adaptation and new editorial prose are provided under the same CC-BY-4.0 documentation license; full text: [LICENSE-DOCS](../LICENSE-DOCS). Changes: permission-source comparison, responsibility/gap analysis, recommendations and paper scenarios. Original contributor copyright is retained; no license or brand rights are expanded.

The original [CONTRIBUTORS.md](https://github.com/omworldprotocol/om-world/blob/4a1793babe349c1578cc0956d6eececbc565966b/CONTRIBUTORS.md), source attributions and linked #6 comments remain the record of actual contributions. The scope-token/memory work and root/delegation/commerce reviews cited by R remain attributed there. This draft does not add reviewer roles, obtain contributor consent, appoint maintainers or claim the named contributors accept these recommendations. It does not imply OM World contributors participate in or endorse MSEC. No external implementation was copied or newly verified.
