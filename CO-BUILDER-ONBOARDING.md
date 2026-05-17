# Co-builder Onboarding Playbook

> Operational checklist for editors. Run when a candidate accepts an invitation to become a Genesis Co-builder.

This is the *how*. For the *why* — role definitions, rights, obligations — see [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md).

The goal of this playbook is **consistency**: every Co-builder gets the same recognition surface, same expectations, same touchpoints — regardless of when they joined or who ran the onboarding.

---

## When to run this playbook

Trigger: a candidate accepts an explicit invitation to a Co-builder role (typically L2 Co-author, but L1 Reviewer and L3 Steward use the same playbook with a small subset of steps).

Acceptance must be **explicit and in writing** (a GitHub comment, email, or signed message). "Sounds good" is enough; silence is not.

---

## Pre-flight (before any public steps)

1. **Confirm the role offered matches what they accepted.** Re-read their acceptance message. If they said yes to "co-author" but you offered both "co-author + reviewer," confirm both are accepted before proceeding.
2. **Confirm the spec contributions** you will cite. List the specific sections/commits their work shaped. If any are ambiguous (e.g., "they pushed back but the resolution went a different direction"), do not list those — only list what genuinely landed.
3. **Confirm preferred handles.** GitHub handle is the default; ask if they want X, personal site, or email also linked.
4. **Confirm preferred communication channel** for pre-publication coordination. Default is GitHub; offer private (email / Signal) without insisting.
5. **Confirm any reference implementations** they want linked. If they shared interface code or example implementations during the dialogue, confirm they're OK with it being publicly cited from our spec.

---

## Public steps (in order)

Each step has a check column — leave blank until the step is done. Do not skip steps; if a step does not apply (e.g., L1 Reviewer has no spec-section attribution), mark it `n/a` with one-line reason.

### 1. CONTRIBUTORS.md entry

- [ ] Add the Co-builder under the correct primitive's Co-authors subsection, following the [kawacukennedy template](CONTRIBUTORS.md#co-authors)
- [ ] Include **concrete citations**: spec section names + commit SHAs that landed their contributions (not generic "thanks to X")
- [ ] Include their joined-date (`Joined YYYY-MM-DD`)
- [ ] Note their freeze-review obligation with the upcoming target date
- [ ] If they have a reference implementation, link it here too

### 2. Spec file Contributors section

- [ ] Add or update the `## Contributors` section at the bottom of the spec file(s) they shaped
- [ ] One line per contribution: handle + role + concrete-citation summary
- [ ] If multiple Co-builders contribute to the same spec, list in joined-date order (oldest first)

### 3. Reference implementation link (if applicable)

- [ ] Add a `## Reference implementations` section to the relevant spec file if not already present
- [ ] Link to the specific commit, comment URL, gist, or tagged release that pins the version (not `main` — pin to immutable URL)
- [ ] Attribute clearly: "Shared by [@handle] as a reference shape for implementations to adopt or adapt"

### 4. Personal welcome thread in Genesis Builders Discussion

- [ ] Create a thread titled `Welcome @{handle} — Genesis {Role} of {Primitive}` in the [Genesis Builders category](https://github.com/omworldprotocol/om-world/discussions/categories/genesis-builders)
- [ ] @-mention them so they get notified
- [ ] Include: one paragraph on what they contributed (with commit links), a note on their forward role (review window, freeze obligation), and an invitation to introduce themselves to other Builders
- [ ] Keep it short — this is a record + a signal, not a press release

### 5. Reply on the original outreach thread

- [ ] Post a final reply on the outside-repo issue/discussion that started the dialogue
- [ ] Confirm role(s) accepted
- [ ] Link to: CONTRIBUTORS.md entry, spec changes commit, personal welcome thread
- [ ] Give the next concrete touchpoint (e.g., "freeze candidate draft will arrive ~YYYY-MM-DD with a 1-week review window")
- [ ] Confirm the communication-channel preference (default GitHub, ask if they want private)
- [ ] Note that Litepaper acknowledgment lands at v0.2 ship and you'll confirm handles before publication

### 6. CRM update

- [ ] Update their row's `status` to `committed`
- [ ] Add a note in their CRM entry summarizing what they accepted (e.g., "Both offers accepted: Co-author + Reviewer")
- [ ] Update the funnel totals (running counts of `committed`)

### 7. Optional: announcement on a higher-traffic channel

- [ ] If the Co-builder consents and the moment is meaningful (first ever Co-builder, primitive freeze, etc.), consider a short post on the OM World X account or a Genesis update
- [ ] Do not do this without explicit consent — many builders prefer the quieter recognition path

---

## After-onboarding maintenance

These are not part of the initial playbook but should be on the editor's calendar:

| When | Action |
|------|--------|
| 2 weeks before each freeze they're listed as reviewer for | Ping with freeze-candidate draft + 1-week review window |
| Every 60 days, if they have been silent | Light check-in ping. Default to no follow-up if they don't respond after one ping. After 60 days of silence, status moves to `inactive` per GENESIS-BUILDERS.md lifecycle. |
| When the Litepaper v0.2 (or later) is being prepared | Confirm handle spelling and any preferred alternate handles |
| When their reference implementation moves (new repo, tagged release, archived) | Update the spec's reference-implementation link |
| When they post something in the Genesis Builders Discussion | React or reply — keep the channel feeling alive |

---

## Worked examples

Use these as references when onboarding the next Co-builder. The two are
intentionally different tiers (Co-author vs Reviewer) so the playbook
shape is visible across the spectrum.

### kawacukennedy — Genesis Co-author of the Intent Schema (2026-05-17)

| Step | Artifact |
|------|----------|
| 1. CONTRIBUTORS.md entry | [intent-schema co-authors section](CONTRIBUTORS.md#co-authors) |
| 2. Spec file Contributors | [intent-schema.md#contributors](docs/intent-schema.md#contributors) |
| 3. Reference implementation | [IVerifierRouter Solidity interface](https://github.com/kawacukennedy/kuberna-labs/issues/4#issuecomment-4466850557) linked from [intent-schema.md#reference-implementations](docs/intent-schema.md#reference-implementations) |
| 4. Personal welcome thread | [discussions/11](https://github.com/omworldprotocol/om-world/discussions/11) |
| 5. Reply on original outreach thread | [kuberna-labs#4 comment](https://github.com/kawacukennedy/kuberna-labs/issues/4#issuecomment-4470133726) |
| 6. CRM update | done |

### Trusteedxyz — Genesis Reviewer of the Execution Proof (2026-05-17)

| Step | Artifact |
|------|----------|
| 1. CONTRIBUTORS.md entry | [Genesis Reviewers → Execution Proof](CONTRIBUTORS.md#execution-proof) |
| 2. Spec file Contributors | [execution-proof.md#contributors](docs/execution-proof.md#contributors) |
| 3. Reference implementation | [Trust-Receipt-Verifier](https://github.com/Trusteedxyz/Trust-Receipt-Verifier) linked from [execution-proof.md#related-work](docs/execution-proof.md#related-work) |
| 4. Personal welcome thread | [discussions/12](https://github.com/omworldprotocol/om-world/discussions/12) |
| 5. Reply on original outreach thread | [Trust-Receipt-Verifier#3 comment](https://github.com/Trusteedxyz/Trust-Receipt-Verifier/issues/3#issuecomment-4470921921) |
| 6. CRM update | done |

Notes from this example: the original outreach was a single issue (no PR-as-vehicle complications); the Reviewer accepted in the same reply that brought a new round of substantive contributions; tier-boundary language was included in the confirmation reply so the contributor sees the path to Co-author without pressure.

---

## Editing this playbook

If you discover a step is missing, redundant, or out of order — propose the change in a PR. The playbook should evolve as we learn what consistent onboarding actually requires. Major changes that affect what Co-builders can expect should also update [GENESIS-BUILDERS.md](GENESIS-BUILDERS.md).
