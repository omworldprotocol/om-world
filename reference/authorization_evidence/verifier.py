"""Bounded revision-2 offline semantic verification. Apache-2.0."""
from dataclasses import dataclass, field
from .core import (PROFILE, SCHEMA_DIGEST, Store, Rejected, require, canonical, digest, object_id,
                   signing_digest, verify_signature, instant, check_time, identity_bytes)
from .policy import allowed, narrow, money, money_le, within

@dataclass
class Trust:
    principal: str
    schema_digest: str
    now: str
    history_as_of: str  # Independently supplied key-history freshness checkpoint, not bundle data.
    active_intent_ids: frozenset = frozenset()  # Independent current cancellation/status checkpoint.

@dataclass
class Result:
    category: str
    detail: str
    layers: list = field(default_factory=list)
    reservations: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)

class Verifier:
    def __init__(self, store, trust):
        self.s, self.t = store, trust
        self.layers = []
        self.grants = []
        self.sigchecks = []

    def signed(self, value, actor):
        verify_signature(value, actor, self.s)
        self.sigchecks.append(actor)

    def dependency(self, ref, kind):
        return self.s.artifact(ref, kind)

    def in_roles(self, actor, role):
        require(actor in self.identity[role], 'UNAUTHORIZED', 'untrusted role ' + role)

    def check_key(self, actor, root, at):
        # Key events are rooted in an independently consented identity profile. Root key bootstrap
        # remains a relying-party trust decision; signatures cannot prove their own freshness.
        events = []
        for ref in self.identity['key_event_refs']:
            event = self.dependency(ref, 'KeyEvent')
            require(event['issuer'] == event['root'], 'INVALID', 'key event issuer')
            verify_signature(event, event['root'], self.s)
            if event['root'] == root and event['key'] == actor:
                events.append(event)
        require(events, 'UNAVAILABLE', 'key history missing')
        require(instant(self.t.history_as_of) >= instant(at), 'UNAVAILABLE', 'key-history checkpoint stale')
        require(all(instant(e['effective_at']) <= instant(self.t.history_as_of) for e in events),
                'INVALID', 'event after supplied history checkpoint')
        relevant = [e for e in events if instant(e['effective_at']) <= instant(at)]
        require(relevant, 'UNAVAILABLE', 'key not active at claimed time')
        require(len({e['effective_at'] for e in events}) == len(events), 'INVALID', 'ambiguous key events')
        relevant.sort(key=lambda e: instant(e['effective_at']))
        require(relevant[-1]['state'] == 'active', 'UNAUTHORIZED', 'key not active at action')
        # Conservative: no compromised-key RFC3161 sidecar parser is shipped. Never accept it as green.
        require(not any(e['state'] in ('compromised', 'revoked') for e in events),
                'UNAVAILABLE', 'compromised/revoked history: timestamp/history adjudication unsupported')
        return True

    def valid(self, value, at):
        check_time(value['issued_at'], value['expires_at'], at)
        require(instant(value['issued_at']) <= instant(self.t.now), 'INVALID', 'future issuance')

    def authorize(self, request):
        """Pre-call material only; never accepts a completed proof as new action authority."""
        self.authorization_request = request
        try:
            return self.verify(None)
        finally:
            self.authorization_request = None

    def verify(self, bundle_ref):
        self.layers, self.grants, self.sigchecks = [], [], []
        try:
            require(digest(canonical(self.s.schema)) == self.t.schema_digest == SCHEMA_DIGEST,
                    'UNSUPPORTED', 'schema digest not pinned revision-2 schema')
            identity_bytes(self.t.principal)
            require(instant(self.t.history_as_of) <= instant(self.t.now), 'INVALID', 'future history checkpoint')
            auth = getattr(self, 'authorization_request', None) is not None
            if auth:
                bundle = self.authorization_request
                require(isinstance(bundle, dict) and set(bundle) == {'intent_ref','acceptance_ref','consent_refs','approval_refs','dependency_manifest_ref','invocation_refs','exported_evidence_refs'}, 'INVALID', 'local authorization request shape')
                require(self.t.history_as_of == self.t.now, 'UNAVAILABLE', 'pre-call status/history checkpoint must be current')
            else:
                bundle = self.s.resolve(bundle_ref, 'EvidenceBundle')
            intent = self.s.resolve(bundle['intent_ref'], 'Intent')
            acceptance = self.s.resolve(bundle['acceptance_ref'], 'Acceptance')
            require(acceptance['intent_ref'] == bundle['intent_ref'], 'INVALID', 'acceptance Intent mismatch')
            if auth:
                require(intent['id'] in self.t.active_intent_ids, 'UNAVAILABLE', 'independent active-Intent checkpoint required')
            require(intent['principal'] == self.t.principal, 'UNAUTHORIZED', 'independent principal trust anchor')
            self.signed(intent, self.t.principal)
            manifest = self.s.resolve(bundle['dependency_manifest_ref'], 'DependencyManifest')
            require(acceptance['dependency_manifest_ref'] == bundle['dependency_manifest_ref'],
                    'INVALID', 'acceptance manifest mismatch')
            require(len(bundle['consent_refs']) == 1, 'UNAUTHORIZED', 'exactly one Consent required')
            consent = self.s.resolve(bundle['consent_refs'][0], 'Consent')
            require(consent['principal'] == self.t.principal
                    and consent['acceptance_ref'] == bundle['acceptance_ref']
                    and consent['dependency_manifest_ref'] == bundle['dependency_manifest_ref'],
                    'UNAUTHORIZED', 'Consent binding')
            self.signed(consent, self.t.principal)
            for limits in [intent['constraints'], acceptance['action_limits'], consent['action_limits']]:
                for rule in limits['allow'] + limits['deny']:
                    require(instant(rule['valid_from']) < instant(rule['expires_at']), 'INVALID', 'empty action interval')
                    require(len(rule['resources']) == len(set(rule['resources'])), 'INVALID', 'duplicate resources')
            narrow(acceptance['action_limits'], intent['constraints'])
            narrow(consent['action_limits'], acceptance['action_limits'])
            require(money_le(acceptance['fee_quote'], intent['constraints']['total_budget'])
                    and money_le(acceptance['fee_quote'], acceptance['action_limits']['total_budget']),
                    'UNAUTHORIZED', 'fee quote ceiling')
            require(instant(intent['issued_at']) <= instant(acceptance['issued_at'])
                    <= instant(consent['issued_at']), 'INVALID', 'authority issuance order')
            self.layers.append('principal-consent-binding')
            self.identity = self.dependency(manifest['identity_profile_ref'], 'IdentityProfile')
            require(self.t.principal in self.identity['principal_keys'], 'UNAUTHORIZED', 'principal role')
            root = acceptance['agent_root']
            self.in_roles(root, 'agent_root_keys')
            signer = self.agent_signer(acceptance, manifest)
            self.signed(acceptance, signer)
            require(acceptance['signer_key_ref'] == acceptance['signature']['key_ref'], 'INVALID', 'acceptance key refs differ')
            registry = self.dependency(manifest['registry_snapshot_ref'], 'RegistrySnapshot')
            self.in_roles(registry['registrar_key'], 'registrar_keys')
            self.signed(registry, registry['registrar_key'])
            require(instant(registry['snapshot_at']) <= instant(acceptance['issued_at']), 'INVALID', 'late registry')
            require(set(self.refid(x) for x in manifest['tool_entry_refs'])
                    <= set(self.refid(x) for x in registry['entry_refs']), 'INVALID', 'entry outside registry')
            confirmation = self.dependency(manifest['confirmation_profile_ref'], 'ConfirmationProfile')
            require(confirmation['channel_receipt_refs'] == [], 'INVALID', 'pinned profile receipt cycle')
            require(root not in confirmation['channel_authority_keys'] and signer not in confirmation['channel_authority_keys'],
                    'UNAUTHORIZED', 'agent cannot be channel authority')
            evidence = self.dependency(manifest['evidence_profile_ref'], 'EvidenceProfile')
            require(not evidence['subjective_evaluator_keys'] and not evidence['subjective_result_refs'],
                    'UNSUPPORTED', 'subjective evaluator profile not implemented')
            budget = self.dependency(manifest['budget_profile_ref'], 'BudgetProfile')
            require(not budget['ledger_event_refs'], 'UNSUPPORTED', 'wire BudgetEvent history unsupported; use local authoritative ledger/checkpoint')
            relay = self.dependency(manifest['relay_profile_ref'], 'RelayProfile')
            require(not auth or relay['mode'] == 'none', 'UNSUPPORTED', 'pre-call cross-chain action admission unsupported')
            custody = self.s.resolve(manifest['custody_profile_ref'], 'CustodyProfile')
            self.in_roles(custody['custodian'], 'custodian_keys')
            self.signed(custody, custody['custodian'])
            require(custody['access_policy_ref'] == custody['export_policy_ref'] == custody['challenge_appeal_policy_ref'],
                    'INVALID', 'custody policy references differ')
            access = self.dependency(custody['access_policy_ref'], 'CustodyAccessProfile')
            require(access['retention_until'] == custody['retention_until']
                    and instant(access['retention_until']) >= max(instant(access['challenge_ends_at']), instant(access['appeal_ends_at'])),
                    'INVALID', 'custody retention')
            require(self.t.principal in access['authorized_reader_keys'], 'UNAUTHORIZED', 'principal custody access')
            self.layers.append('typed-dependencies')
            plan = self.s.resolve(acceptance['plan_ref'], 'Plan')
            if auth:
                invrefs = bundle['invocation_refs']
                require(isinstance(invrefs, list) and len(invrefs) == len(plan['ordered_actions']) > 0, 'INVALID', 'authorization plan coverage')
                require(len({self.refid(x) for x in invrefs}) == len(invrefs), 'INVALID', 'duplicate invocation')
                steps = [{'timestamp': self.t.now, 'tool_id': self.s.resolve(self.s.resolve(x, 'Invocation')['tool_entry_ref'], 'ToolEntry')['tool_id']} for x in invrefs]
                bindings = [None] * len(invrefs)
            else:
                proof = self.s.artifact(bundle['aggregate_proof_ref'])
                required = {'spec_version','intent_id','mandate_id','plan','steps','artifacts','success_claim','signature'}
                require(isinstance(proof, dict) and set(proof) == required, 'INVALID', 'aggregate shape')
                require(proof['spec_version'] == '0', 'UNSUPPORTED', 'aggregate version')
                require(proof['intent_id'] == intent['id'] and proof['mandate_id'] == acceptance['id']
                        and proof['plan'] == plan, 'INVALID', 'aggregate binding')
                self.signed(proof, signer)
                require(proof['signature']['key_ref'] == acceptance['signer_key_ref'], 'INVALID', 'aggregate signer differs')
                steps, bindings, invrefs = proof['steps'], bundle['step_bindings'], bundle['invocation_refs']
                require(len(steps) == len(bindings) == len(invrefs) == len(plan['ordered_actions']) > 0,
                        'INVALID', 'step bijection lengths')
                require(len({self.refid(x) for x in invrefs}) == len(invrefs), 'INVALID', 'duplicate invocation')
            contexts, nonces, grants = set(), set(), []
            chained = any('prev_hash' in step for step in steps)
            previous = digest(canonical(plan))
            previous_time = None
            approvals = [self.s.resolve(x, 'InvocationApproval') for x in bundle['approval_refs']]
            require(len({a['id'] for a in approvals}) == len(approvals), 'INVALID', 'duplicate approval')
            used_approvals = set()
            exported = {}
            for ref in bundle['exported_evidence_refs']:
                raw = self.s.bytes(ref)
                exported[ref['digest']] = raw
            for i, (step, binding, invref, template) in enumerate(zip(steps, bindings, invrefs, plan['ordered_actions'])):
                require(auth or (binding['step_index'] == i and binding['invocation_ref'] == invref),
                        'INVALID', 'step binding order')
                inv = self.s.resolve(invref, 'Invocation')
                at = step['timestamp']
                require(previous_time is None or instant(at) >= instant(previous_time), 'INVALID', 'nonsequential step times')
                previous_time = at
                require(inv['plan_index'] == i and inv['acceptance_ref'] == bundle['acceptance_ref'], 'INVALID', 'plan index/acceptance')
                require(instant(consent['issued_at']) < instant(at) <= instant(self.t.now), 'INVALID', 'action time order')
                require(instant(inv['issued_at']) <= instant(at), 'INVALID', 'invocation after call')
                for obj in (intent, acceptance, consent):
                    self.valid(obj, at)
                for credential in self.credentials:
                    self.valid(credential, at)
                require(instant(at) <= instant(acceptance['deadline']), 'UNAUTHORIZED', 'deadline')
                nonce = root + '/' + PROFILE + '/Invocation/' + inv['nonce']
                require(nonce not in nonces, 'UNAUTHORIZED', 'invocation nonce replay')
                nonces.add(nonce)
                tool, behavior = self.tool(inv, manifest, at)
                expected = template['action']
                require(inv['input_ref'] == template['input_ref']
                        and inv['resource'] in expected['resources']
                        and expected['tool_id'] == tool['tool_id'] and expected['version'] == tool['version']
                        and expected['operation'] == inv['operation']
                        and instant(expected['valid_from']) <= instant(at) < instant(expected['expires_at'])
                        and money_le(inv['budget'], expected['max_call_budget']), 'UNAUTHORIZED', 'plan template coverage')
                require(step['tool_id'] == tool['tool_id'], 'INVALID', 'step tool')
                for limits in [intent['constraints'], acceptance['action_limits'], consent['action_limits']] + self.delegated_limits:
                    require(allowed(limits, tool, inv, at), 'UNAUTHORIZED', 'concrete action outside authority')
                policy = self.s.resolve(inv['deployment_policy_ref'], 'DeploymentPolicy')
                require(inv['deployment_policy_ref'] in manifest['deployment_policy_refs']
                        and inv['tool_entry_ref'] in policy['baseline_refs'], 'INVALID', 'policy baseline')
                self.in_roles(policy['operator'], 'operator_keys'); self.signed(policy, policy['operator'])
                require(instant(policy['valid_from']) <= instant(at), 'UNAUTHORIZED', 'policy not active')
                require(not any(within(x, tool, inv, at)
                                for x in policy['deny_rules']), 'UNAUTHORIZED', 'deployment deny')
                restriction = self.dependency(policy['extra_requirements_ref'], 'RestrictionProfile')
                check_time(restriction['not_before'], restriction['expires_at'], at)
                needed = ('out_of_band' if tool['confirmation'] == 'restricted' or restriction['extra_confirmation'] == 'out_of_band'
                          else 'affirmative' if tool['confirmation'] == 'human-in-loop' or restriction['extra_confirmation'] == 'affirmative'
                          else None)
                self.approval(invref, bundle, confirmation, approvals, used_approvals, needed, exported, at)
                if not auth:
                    self.step(step, binding, inv, behavior, contexts, exported, at)
                if chained:
                    require(step.get('prev_hash') == previous, 'INVALID', 'chain link')
                    previous = digest(canonical({k: v for k, v in step.items() if k != 'prev_hash'}))
                else:
                    require('prev_hash' not in step, 'INVALID', 'mixed chain mode')
                for credential in self.credentials:
                    self.check_key(credential['issuer_key'], root, at)
                    self.check_key(credential['subject_key'], root, at)
                for actor in [self.t.principal, root, signer, tool['registrar'], policy['operator'], custody['custodian']]:
                    self.check_key(actor, root if actor == signer else actor, at)
                accounts = {intent['id']: money(intent['constraints']['total_budget'])[2],
                            acceptance['id']: money(acceptance['action_limits']['total_budget'])[2],
                            consent['id']: money(consent['action_limits']['total_budget'])[2]}
                for limits in self.delegated_limits:
                    # Each credential's own object ID is added below via credential_accounts.
                    require(money_le(inv['budget'], limits['total_budget']), 'UNAUTHORIZED', 'credential budget')
                accounts.update(self.credential_accounts)
                asset, network, amount = money(inv['budget'])
                require(all(money(l['total_budget'])[:2] == (asset, network) for l in
                            [intent['constraints'], acceptance['action_limits'], consent['action_limits']] + self.delegated_limits),
                        'UNSUPPORTED', 'cross-asset budget')
                grants.append({'invocation': inv['id'], 'nonce_scope': nonce, 'accounts': accounts,
                               'asset': asset, 'network': network, 'amount': amount,
                               'deployment_id': budget['deployment_id'], 'ledger_authorities': budget['ledger_authority_keys'],
                               'authority_nonces': {actor + '/' + PROFILE + '/' + obj['object_type'] + '/' + obj['nonce']: obj['id']
                                   for actor, obj in [(self.t.principal, intent), (root, acceptance), (self.t.principal, consent)]
                                   + [(self.t.principal, a) for a in approvals if a['invocation_ref'] == invref]}})
            require(len(used_approvals) == len(approvals), 'INVALID', 'orphan approval')
            require(auth or (contexts == {self.refid(x) for x in bundle['context_refs']}
                    and len(contexts) == len(bundle['context_refs'])), 'INVALID', 'orphan/duplicate context')
            self.layers.append('pre-call-authority' if auth else 'authority-and-step-bijection')
            if not auth:
                self.relay(relay, exported)
            # Budget events are specification artifacts, not sufficient authority state. A real
            # admission is completed only by calling Ledger.reserve with these verified limits.
            require(budget['deployment_id'] and budget['ledger_authority_keys'], 'UNAVAILABLE', 'budget authority')
            for actor in budget['ledger_authority_keys']:
                self.check_key(actor, actor, self.t.now)
            if not auth:
                criteria = self.s.artifact(intent['success_criteria_ref'])
                require(criteria == {'kind': 'exact-artifact-digests', 'digests': proof['artifacts']},
                        'UNSUPPORTED', 'only exact-artifact-digests outcome criteria implemented')
                require(isinstance(proof['artifacts'], list) and all(x in exported for x in proof['artifacts']),
                        'UNAVAILABLE', 'success artifact bytes unavailable')
                require(proof['success_claim'] == {'artifact_digests': proof['artifacts']}, 'EVIDENCE_MISMATCH', 'success claim')
            requirements = self.s.artifact(intent['evidence_requirements_ref'])
            require(requirements == {'profile': PROFILE, 'evidence_profile_ref': manifest['evidence_profile_ref']},
                    'UNSUPPORTED', 'Intent evidence requirements not exact pinned EvidenceProfile')
            # Nonces are unique within each root/type scope; cross-export persistence is
            # enforced at admission for invocation and authority identifiers.
            scoped_nonces = set()
            for actor, obj in [(self.t.principal, intent), (root, acceptance), (self.t.principal, consent)] + [(self.t.principal, a) for a in approvals]:
                token = (actor, obj['object_type'], obj['nonce'])
                require(token not in scoped_nonces, 'UNAUTHORIZED', 'authority/approval nonce reused')
                scoped_nonces.add(token)
            if not auth:
                self.layers.append('artifact-success-criteria')
            self.grants = grants
            return Result('AUTHORIZED_WITH_BUDGET_PENDING' if auth else 'VERIFIED_WITH_BUDGET_PENDING',
                          'pre-call authorization; atomic reservation still required' if auth else 'historical offline evidence checked; never a new execution authorization',
                          self.layers, grants,
                          ['configured principal/history checkpoint', 'pinned role/channel/custody/relayer claims, not physical truth',
                           'exact-artifact outcome only; no runtime honesty or live execution claim'])
        except Rejected as exc:
            return Result(exc.category, exc.detail, list(self.layers))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return Result('INVALID', 'malformed evidence: ' + str(exc), list(self.layers))

    @staticmethod
    def refid(ref):
        return ref['profile'] + '/' + ref['object_type'] + '/' + ref['id']

    def agent_signer(self, acceptance, manifest):
        self.delegated_limits, self.credential_accounts, self.credentials = [], {}, []
        root = acceptance['agent_root']
        parent_key, parent_limits, parent_end = root, acceptance['action_limits'], None
        seen, previous = set(), None
        for ref in acceptance['delegation_refs']:
            require(ref in self.identity['delegation_artifact_refs'], 'INVALID', 'unlisted delegation')
            delegation = self.dependency(ref, 'Delegation')
            require(delegation['id'] not in seen, 'INVALID', 'delegation cycle')
            seen.add(delegation['id'])
            require(delegation['issuer_root'] == root and delegation['issuer_key'] == parent_key,
                    'UNAUTHORIZED', 'delegation path')
            require(delegation['parent_refs'] == ([] if previous is None else [previous]), 'INVALID', 'delegation parent')
            self.signed(delegation, parent_key)
            check_time(delegation['issued_at'], delegation['expires_at'], acceptance['issued_at'])
            if parent_end:
                require(instant(delegation['issued_at']) >= instant(parent_end[0])
                        and instant(delegation['expires_at']) <= instant(parent_end[1]), 'UNAUTHORIZED', 'credential interval widens')
                outer_time_reduced = (instant(delegation['issued_at']) > instant(parent_end[0])
                                      or instant(delegation['expires_at']) < instant(parent_end[1]))
                narrow(delegation['action_limits'], parent_limits, strict=not outer_time_reduced)
            # First credential establishes root-authorized finite scope; Acceptance must fit final scope.
            parent_key, parent_limits = delegation['subject_key'], delegation['action_limits']
            parent_end = delegation['issued_at'], delegation['expires_at']
            self.delegated_limits.append(parent_limits)
            self.credentials.append(delegation)
            self.credential_accounts[delegation['id']] = money(parent_limits['total_budget'])[2]
            previous = ref
        if previous:
            narrow(acceptance['action_limits'], parent_limits)
        raw = self.s.bytes(acceptance['signer_key_ref'])
        require(raw == identity_bytes(parent_key), 'UNAUTHORIZED', 'operational key path')
        return parent_key

    def tool(self, inv, manifest, at):
        require(inv['tool_entry_ref'] in manifest['tool_entry_refs'], 'INVALID', 'tool outside manifest')
        tool = self.s.resolve(inv['tool_entry_ref'], 'ToolEntry')
        self.in_roles(tool['registrar'], 'registrar_keys'); self.signed(tool, tool['registrar'])
        require(instant(tool['valid_from']) <= instant(at), 'UNAUTHORIZED', 'tool not active')
        behavior = self.dependency(tool['behavior_ref'], 'ToolBehavior')
        self.s.bytes(tool['interface_ref'])
        require(tool['interface_ref'] == behavior['interface_bytes_ref'], 'INVALID', 'behavior/interface')
        ops = behavior['operations']
        require(len({x['operation'] for x in ops}) == len(ops), 'INVALID', 'ambiguous operation')
        matches = [x for x in ops if x['operation'] == inv['operation']]
        require(len(matches) == 1 and set(matches[0]['classes']) <= set(tool['operation_classes']),
                'INVALID', 'behavior class declaration')
        require(not tool['stateful'] or matches[0]['context_mode'] == 'external-state',
                'INVALID', 'stateful registration cannot claim pure operation')
        return tool, matches[0]

    def approval(self, invref, bundle, confirmation, approvals, used, needed, exported, at):
        matched = [a for a in approvals if a['invocation_ref'] == invref]
        require(len(matched) <= 1, 'INVALID', 'duplicate call approval')
        require(needed is None or len(matched) == 1, 'UNAUTHORIZED', 'required approval missing')
        for a in matched:
            require(a['principal'] == self.t.principal and a['acceptance_ref'] == bundle['acceptance_ref']
                    and a['dependency_manifest_ref'] == bundle['dependency_manifest_ref'], 'UNAUTHORIZED', 'approval binding')
            require(a['channel_evidence_ref'] == self.manifest_confirmation(bundle), 'INVALID', 'approval channel profile')
            require(needed != 'out_of_band' or a['approval_mode'] == 'out_of_band', 'UNAUTHORIZED', 'restricted channel')
            self.signed(a, self.t.principal); self.valid(a, at)
            receipts = []
            for raw in exported.values():
                try:
                    from .core import strict_json
                    value = strict_json(raw)
                except Rejected:
                    continue
                if isinstance(value, dict) and value.get('object_type') == 'ChannelReceipt' and value.get('invocation_ref') == invref:
                    self.s.validate_object(value, 'ChannelReceipt'); receipts.append(value)
            require(len(receipts) == 1, 'UNAVAILABLE', 'one attributable channel receipt required')
            receipt = receipts[0]
            require(receipt['authority'] in confirmation['channel_authority_keys']
                    and receipt['principal'] == self.t.principal and receipt['mode'] == a['approval_mode']
                    and receipt['approval_signing_digest'] == 'sha256:' + signing_digest(a).hex(),
                    'UNAUTHORIZED', 'channel receipt authority/binding')
            self.signed(receipt, receipt['authority'])
            require(instant(a['issued_at']) <= instant(receipt['observed_at']) < instant(at), 'INVALID', 'channel time')
            self.check_key(receipt['authority'], receipt['authority'], at)
            used.add(a['id'])

    def manifest_confirmation(self, bundle):
        return self.s.resolve(bundle['dependency_manifest_ref'], 'DependencyManifest')['confirmation_profile_ref']

    def step(self, step, binding, inv, behavior, contexts, exported, at):
        fields = {'tool_id','input_hash','output_hash','timestamp'}
        require(fields <= set(step) <= fields | {'context_hash','attestation','prev_hash'}, 'INVALID', 'step shape')
        require(binding['step_digest'] == digest(canonical(step)), 'INVALID', 'complete step digest')
        require(binding['input_ref'] == inv['input_ref'], 'INVALID', 'input association')
        for key, hashkey in [('input_ref','input_hash'), ('output_ref','output_hash')]:
            self.s.artifact(binding[key])
            require(binding[key]['digest'] == step[hashkey] and binding[key]['digest'] in exported,
                    'EVIDENCE_MISMATCH', 'input/output bytes association')
        refs = binding['context_refs']
        if behavior['context_mode'] == 'pure':
            require(not refs and 'context_hash' not in step, 'INVALID', 'pure step context')
        else:
            require(len(refs) == 1, 'UNAVAILABLE', 'external state context missing')
            ctx = self.s.resolve(refs[0], 'ContextManifest')
            require(step.get('context_hash') == digest(canonical(ctx)), 'EVIDENCE_MISMATCH', 'context digest')
            require(instant(ctx['observed_at']) <= instant(at), 'INVALID', 'post-state used as pre-state')
            require(ctx['pre_state_refs'] or ctx['configuration_refs'] or ctx['retrieval_procedure_refs'],
                    'UNAVAILABLE', 'empty dependency context')
            require(digest(canonical(ctx)) in exported, 'UNAVAILABLE', 'context not in export closure')
            for ref in ctx['pre_state_refs'] + ctx['retrieval_procedure_refs'] + ctx['provenance_refs']:
                require(ref['digest'] in exported, 'UNAVAILABLE', 'context dependency bytes missing')
                self.s.bytes(ref)
            for ref in ctx['configuration_refs']:
                cfg = self.s.resolve(ref, 'Configuration')
                self.in_roles(cfg['provisioner'], 'provisioner_keys'); self.signed(cfg, cfg['provisioner'])
                check_time(cfg['effective_from'], cfg['effective_until'], at)
                require(cfg['config_bytes_ref']['digest'] in exported, 'UNAVAILABLE', 'config bytes missing')
                self.s.bytes(cfg['config_bytes_ref'])
                self.check_key(cfg['provisioner'], cfg['provisioner'], at)
            contexts.add(self.refid(refs[0]))
        # Unknown attestation encodings are never silently considered verified.
        require('attestation' not in step, 'UNSUPPORTED', 'tool attestation suites not implemented')

    def relay(self, relay, exported):
        if relay['mode'] == 'none':
            return
        self.in_roles(relay['relayer_key'], 'relayer_keys')
        rule = self.dependency(relay['finality_rule_ref'], 'FinalityRule')
        require(rule['chain_id'] == relay['source_chain'], 'INVALID', 'finality chain')
        require(relay['receipt_refs'], 'UNAVAILABLE', 'relay receipt')
        for ref in relay['receipt_refs']:
            value = self.dependency(ref, 'RelayReceipt')
            require(value['relayer'] == relay['relayer_key'] and value['source_chain'] == relay['source_chain']
                    and value['destination_chain'] == relay['destination_chain']
                    and value['finality_rule_ref'] == relay['finality_rule_ref'], 'INVALID', 'relay path')
            self.signed(value, relay['relayer_key'])
            age = (instant(self.t.now) - instant(value['observed_at'])).total_seconds()
            require(0 <= age <= min(relay['freshness_seconds'], rule['maximum_age_seconds'])
                    and value['confirmations'] >= rule['minimum_confirmations'], 'UNAUTHORIZED', 'relay age/finality claim')
            self.s.artifact(value['canonical_payload_ref'])
            require(value['canonical_payload_ref']['digest'] in exported, 'UNAVAILABLE', 'relay exact bytes')
            self.check_key(relay['relayer_key'], relay['relayer_key'], self.t.now)
