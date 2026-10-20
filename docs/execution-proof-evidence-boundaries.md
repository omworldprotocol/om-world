# Issue #5 — Execution Proof evidence boundaries and open design questions

> **Non-normative editorial appendix.** Related: [#5](https://github.com/omworldprotocol/om-world/issues/5), which remains open. This inventories current text, editorial suggestions and unresolved design. It does not amend a schema, hashing/signature formula, permission policy or protocol version. All scenarios are paper reviews, not executed tests. No implementation or security qualification is established.

## Sources and reading labels

Pinned baseline: [3cc831b013661b8fd91107e13876deadd276b4a9](https://github.com/omworldprotocol/om-world/tree/3cc831b013661b8fd91107e13876deadd276b4a9).

- [P — Execution Proof](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/execution-proof.md).
- [M — Agent Mandate](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/agent-mandate.md); [I — Intent Schema](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/intent-schema.md).
- [R — #4 responsibility appendix, PR #22](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/agent-mandate-responsibilities.md).
- [T — Tool Registry](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/tool-registry.md); [Q — #6 permission-source appendix, PR #23](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/docs/tool-registry-permission-sources.md).

**C** = explicit current design-draft text, not current service behavior or proven security. **S** = proposed editorial clarification or review objective, not an adopted protocol rule. **U** = an unresolved mechanism, contradiction or design choice. R and Q are merged non-normative records; their merge did not resolve authority, permissions or identifiers. Version labels in P's open questions are historical design intentions, not evidence of a freeze/release.

## 1. Evidence and responsibility boundaries

| Boundary | C: existing source | S: minimal clarification | U: design left open |
|---|---|---|---|
| Authorization / acceptance / proof | R separates principal authorization, Agent acceptance, delegated signing and concrete action. P is an Agent's aggregate fulfillment claim. | A proof attributes claims and supports evaluation; it is not a substitute for prior principal consent. Q's unselected permission-source options cannot be assumed by a proof verifier. | Scope/operation mapping, policy revision binding, activation binding and delegated proof-signature wording. |
| Snapshot custody | P requires context commitments for stateful evidence and explicitly lists provider, snapshot oracle, or Agent with provider co-signature as storage/service candidates. | Separate commitment, possession, availability, reproducibility and truth. A real hash proves none of the latter by itself. | Custodian, retention, authenticated retrieval, access rights, costs, export, availability failure and dispute consequences. No custodian selected. |
| Tool state and context_hash | P Step table broadly requires stateful context; specific rule covers read against stateful backend; Canonicalization covers database/live fetch/prior session state. | Explain that transport (HTTP) and mutation class (read) do not establish input-determined output. Surface the tension with the earlier “HTTP APIs” stateless example. | Exact coverage for stateful writes, hidden state and context structure; reconcile general/specific wording explicitly rather than infer a new rule. |
| Retrieval reproducibility | P binds corpus, retrieval procedure and returned evidence; procedure includes model/version, transforms, filters, top_k and scoring. | Replay claim is conditional on appropriate bytes, procedure and execution assumptions being available. Corpus hash alone is insufficient. | Exact serialization across the three layers; output duplication/binding; nondeterminism, environment and privacy restrictions. |
| Startup configuration | P Open questions compares context_hash, new env_hash, and out-of-step signed configuration evidence; current lean is the third, with provisioner-signed env_attestation as a reference. | Mark these as candidate/version-boundary discussion, not a current OM World field or completed test. | Canonicalization's general external-state language versus config-out-of-step lean; trust in provisioner, config binding/freshness and profile selection. |
| Cross-domain / cross-chain | I multi is ALL by dimension; P still asks to formalize combination rules. P leans toward relayer deployment pattern for v0.2 and reserves a heterogeneous-relayer primitive candidate for v0.3. | Distinguish data/runtime evidence composition from transporting evidence between chains; preserve exact-JCS-byte commitment and attributable relayer obligations as current draft text. | Complete aggregation rules, relay trust/finality/freshness, failure handling and any new field. No proof_relay_contract field adopted. |
| Parallel composition | P describes sequential prev_hash; parallel/Merkle is out of v0.2 scope and a v0.3+ fork point. | Keep fan-out/join separate from current linear mode; distinguish reference shape from a usable encoding. | Sort by hash versus deterministic step ID, duplicate leaves, tree construction/domain separation, join semantics and version signalling. No Merkle algorithm selected. |
| Aggregate / chaining | P requires complete aggregate, disallows sliced envelopes, permits adjacent records as dispute evidence and defines step hash excluding prev_hash. | Distinguish local-link checking from full aggregate verification. Adjacent evidence is not an authorized truncated proof. | Excluding prev_hash means predecessor ancestry is not recursively committed by that step hash; aggregate signature and full traversal are separate checks. Do not change hash input under an editorial correction. |
| Identity / key history | P has identity binding and Active/Rotated/Compromised checks; M has root-to-operational-key chains. P also describes a single-trust-domain identity exception. | Record which identity model applies; do not silently generalize the single-domain exception to adversarial deployments. | Operational-key reconciliation and how registry key-history checks apply to the single-domain exception remain incomplete. |

### Snapshot custody options — no assignment made

| Candidate from P | Potential benefit | Evidence / trust questions still needed |
|---|---|---|
| Tool provider stores/serves | Close to the state source | Authentic historical root, retention, independent export, provider outage/equivocation, access and privacy. |
| Dedicated snapshot oracle | Separates execution provider from evidence service | Oracle identity/trust, authenticated ingestion, freshness, retention/cost and failure concentration. |
| Agent with provider co-signature | Agent can retain an export | What provider actually signed, completeness, timestamp, provider honesty and independent retrieval. |

S: a future custody profile should describe owner, evidence location, retention and access assumptions, and what cannot be established if evidence is missing. These are review requirements proposed here, not fields added to P. Privacy-driven deletion can remove replay material; a deletion-event claim and preserved commitments do not recreate the deleted bytes or independently prove physical erasure. P's deletion profile is not a legal-compliance conclusion; legal sufficiency is outside this review.

## 2. Identifier and commitment differences

| Surface | C: current text | U / proposed disposition |
|---|---|---|
| intent_id | M and P refer to I.id; I Fields calls id UUID, Canonicalization computes SHA-256. | Record representation conflict; do not choose UUID/hash, conversion or new ID formula. R already flags this. |
| mandate_id | Present in P envelope, absent from M Fields. | Need identifier/resolution and signed-object binding decision; no ad hoc UUID or digest. |
| plan_hash | M commits to a plan hash; P anchors first chained step to mandate plan_hash described as precommitted in intent record; I Fields lacks plan_hash. | Clarify source location, signer and timing before claiming an end-to-end authorization chain. No new Intent field or preimage here. |
| executor commitment | I recommends activation-time binding while principal signs Intent canonical content. | R's post-signing mutation/binding gap remains U; do not silently mutate an already signed object. |
| Proof signature | P specifies SHA-256(JCS(envelope_without_signature)); M supports operational-key delegation. | Preserve formula. Clarify root attribution versus operational signer and deployment exception through separate design review. |
| prev_hash / step_hash | P formula excludes prev_hash; first link uses plan commitment. | Preserve current formula, but qualify local-link versus complete-history claims. Reincluding prev_hash would be a protocol change requiring explicit version/design, not an editorial fix. |
| tool_id / version / policy | P step names tool_id; T has version, operation_class and confirmation; M token lacks explicit version/class field. | Q identifies unresolved source, version and permission composition. No policy_hash, registry version or approval field introduced. |
| protocol / payment_carrier | M composition says proof provenance should record these separately; P envelope/step tables do not define them. | Inventory as an additional cross-document gap; do not insert unspecified extension fields or assume encoding. |
| proof_id / settlement_reference / evidenceHash | Historical #5 fields are not current envelope fields; related-work evidenceHash is not automatically output_hash. | Retain merged PR #17/#18 limitations: content identity, supporting evidence, tool output, publisher and claimed buyer are distinct. No alias mapping selected. |

## 3. Potential follow-up clarifications — not adopted

| ID | Target | Smallest suggested documentation change | Explicit ceiling |
|---|---|---|---|
| E01 | P near Purpose / navigation | Link a non-normative evidence-boundary/gap appendix to R and Q. | Do not replace normative definitions or claim #4/#6 decisions. |
| E02 | context_hash subsection | Identify the HTTP/live-fetch inconsistency and explain input-determined output versus externally dependent output, citing the existing Canonicalization rule. | For direct prose repair, avoid claiming every HTTP call is reproducible; exact stateful-write/config profile stays U. No new context format. |
| E03 | Snapshot replay wording | Qualify replay as conditional on snapshot + procedure + evidence availability and relevant deterministic behavior; list custody alternatives as open. | No retention promise, custodian appointment, privacy guarantee or new verification status. |
| E04 | Config / cross-chain / parallel boundary note | Label current leans, out-of-scope items and future candidates; state that promised test vectors/freeze targets are not verified deliveries. | No env_hash, relay field, Merkle proof or new version adopted. |
| E05 | Chaining / binding gap note | Link ID/plan/operational-signature differences; separate adjacent dispute evidence from a complete proof and local consistency from full chain assurance. | No change to hash formulas, aggregate signature input, signed-object mutation or acceptance algorithm. |
| E06 | Related work / provenance | Preserve original contributions and merged limits; treat external systems as references, not verified adapters or interchangeable cryptographic suites. | No blanket revalidation of all older interop claims; no contributor endorsement or consent inferred. |

Recommended order: first record E01/E05 gaps in a non-normative appendix; review E02/E03 wording repairs explicitly against both conflicting source passages; add E04 boundary labels. New identifiers, hash changes, custody rules and parallel/cross-chain mechanisms require separately scoped design decisions. This appendix records these possible follow-ups without applying direct normative-body repairs or choosing such decisions.

## 4. Paper review / acceptance scenarios

C outcomes mean only that the relevant source states a rule. S/U outcomes expose interpretation or missing design; no case is an executed pass/fail measurement or complete authorization verdict.

| ID | Scenario | Current textual basis and expected documentation disposition |
|---|---|---|
| V01 | Pure transform, every output-determining input captured | C: context_hash may be absent under Canonicalization. Do not generalize to transport type. |
| V02 | HTTP live fetch changes with time despite same request | C: Canonicalization treats live fetch as external state; earlier HTTP stateless example conflicts. S: expose/repair example. U: exact evidence profile and replay availability. |
| V03 | Stateful memory read lacks context_hash | C: specific rule calls it unattested. Do not invent a universal invalid-envelope verdict or automatic slash outcome from this paper case. |
| V04 | context_hash is null, empty string or empty/zero placeholder | C: omit differs from null, and empty/placeholder encodings are invalid. Do not replace absent optional fields with null. |
| V05 | Context root exists but snapshot cannot be obtained | C: custody open. S: replay not established from root alone; distinguish unavailable evidence from proven false claim. U: enforcement/dispute status. |
| V06 | Corpus same, embedding version/filter/top_k/scoring differs | C: retrieval-procedure commitment matters. S: cannot claim equivalent retrieval from corpus equality. U: exact multi-layer preimage. |
| V07 | Same corpus/procedure but nondeterministic ranking differs | C: P recognizes nondeterministic ranking disputes. S: state assumptions and evidence; no guarantee of universal exact replay. U: tolerance/semantic success criteria. |
| V08 | Provider, oracle or Agent+co-signature serves snapshot | C: all are listed candidates. U: none selected; record provenance, availability, freshness and trust assumptions before choosing a custody profile. |
| V09 | Otherwise pure tool reads startup feature flags | C: config candidates/current lean in Open questions; Canonicalization broad external-state rule creates tension. U: placement/profile; do not automatically add env_hash. |
| V10 | Provisioner signs env_attestation but config bytes are unavailable | C: provisioner signature is reference shape for candidate path. S: attribution alone does not reconstruct configuration; U: content binding/trust and handling missing bytes. |
| V11 | Stateful write or session state not captured by input/prev_hash | C: broad table/Canonicalization versus read-specific rule needs reconciliation. U: required snapshot timing/format for each operation; do not invent a state-transition proof. |
| V12 | zkTLS data evidence plus TEE runtime evidence | C: I multi uses ALL by dimension, P combination question remains. S: retain role distinction, no interchangeable signatures or automatic integration qualification. |
| V13 | Origin chain A, execution/settlement chain B, single relayer | C: v0.2 lean is deployment relayer pattern; exact verified JCS bytes and stable relayer attribution obligations remain. U: concrete finality/freshness/trust path. |
| V14 | Relay path uses heterogeneous relayers | C: primitive is future v0.3 candidate. U: trust composition and schema. Do not accept proof_relay_contract as current field. |
| V15 | Relayer signs a derived digest without identifiable verified payload bytes | C: conflicts with P exact-byte commitment requirement. U: encoding/availability details; do not design substitute signature scheme. |
| V16 | Fan-out/join encoded as Merkle root in current linear prev_hash | C: parallel out of v0.2 scope. U: ordering/tree/join/version; do not label this a currently valid profile. |
| V17 | Two implementations sort parallel leaves by hash versus step ID | C: candidate wording mentions both. U: ordering ambiguity; do not choose one or claim interoperability from the reference expression. |
| V18 | Only adjacent steps supplied as a complete proof | C: full aggregate required; adjacent records may be dispute evidence, not a replacement envelope. S: state distinction explicitly. |
| V19 | Earlier ancestry changed but adjacent payload hashes remain consistent | C: step hash excludes prev_hash; aggregate signature covers the full envelope. S: a local link does not prove full ancestry; whole-envelope signature/traversal are separate. U: any future stronger chain design. No exploit experiment or hash formula change. |
| V20 | Proof mandate_id or initial plan anchor cannot be resolved to a signed source | U: M/I/P binding gap already in R. Do not invent ID/preimage or infer authorization from Agent's plan claim. |
| V21 | Operational key differs from root executor | C: M requires delegation-chain validation; P same-identity wording needs alignment. U: exact proof credential binding; no automatic root-address equality rejection that ignores M. |
| V22 | Single-domain routing identity treated as sufficient in adversarial market | C: P exception is conditional. S: do not generalize it; U: complete profile and key-state implications. |
| V23 | Unknown proof spec_version | C: reject UNSUPPORTED_SPEC_VERSION, no silent downgrade. This is a proof-version rule, not a new rule for missing registry policy versions. |
| V24 | Old mandate references changed registry/policy version | U: Q leaves old-mandate and policy binding open. P signature alone cannot settle which policy applied or establish prior confirmation. |
| V25 | Key rotated versus compromised | C: P distinguishes normal rotation and compromise; compromised acceptance requires valid trusted RFC3161 timestamp predating compromise. S: do not equate key possession, time claim and validity history. No timestamp test performed. |
| V26 | Snapshot raw bytes removed for privacy; only commitment/deletion evidence remains | C: deletion profile preserves evidence history, not raw replay bytes. S: no replay/physical-erasure/compliance guarantee from signed claim alone; U: post-deletion dispute evidence policy. |
| V27 | Buyer-side claim has evidenceHash and EAS publication | C: merged related-work limitations distinguish evidence/output, publisher/buyer key and publication/payment/delivery. S: do not copy fields as automatic mapping or call demo a real outcome. |

## 5. Acceptance limits and remaining decisions

Editorial review of this appendix requires: C/S/U separation; explicit links to both merged appendices; all requested boundaries and binding gaps covered; no changed source bytes, new fields/hash rules or permission policy; paper cases never represented as runtime results. The minimum revision table is proposed work, not applied text. Merging this editorial record does not close #5, freeze specifications or qualify any implementation.

Remaining protocol decisions include custody/retention/access/failure policy; precise context structure and operation coverage; configuration profile; multi/cross-chain trust and composition; parallel encoding; identifier and plan-binding resolution; delegated identity/profile alignment. Other open questions such as privacy-preserving inputs and subjective outcome evaluation remain visible; related-work citations do not resolve them. No rough consensus or external reviewer approval is claimed.

## Attribution and licensing

© OM World Protocol contributors, licensed under CC-BY-4.0. Source: https://github.com/omworldprotocol/om-world at the pinned baseline. This adaptation and new editorial prose are under the same CC-BY-4.0 documentation license; full text: [LICENSE-DOCS](../LICENSE-DOCS). Changes: boundary and difference tables, minimal editorial proposals and paper scenarios. Original copyright, licenses and brand exclusions remain unchanged.

Original P Contributors and [CONTRIBUTORS.md](https://github.com/omworldprotocol/om-world/blob/3cc831b013661b8fd91107e13876deadd276b4a9/CONTRIBUTORS.md) remain authoritative attribution records: Trusteedxyz (canonicalization/key history/aggregate/relayer work), Tyche Institute (threat-model boundary), attestplane (independent verification and deletion profile), ark-forge/proof-spec (canonicalization/context/config/parallel questions), and the source's other cited contributions remain intact. The #5 discussion and PR #17/#18 contributions by kawacukennedy and holistis are preserved, with their later merged evidence limitations. R/Q source attribution remains in those appendices. This summary does not appoint reviewers, claim contributor agreement/current participation, or imply endorsement of MSEC. External implementations and legal conclusions were not revalidated; no external material beyond these source records was imported.
