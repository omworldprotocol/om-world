"""Synthetic signed fixtures only; never evidence of a real approval, tool or outcome."""
import copy
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from ..core import PROFILE, SUITE, canonical, digest, object_id, signing_digest, Store
from ..verifier import Trust

START='2026-10-21T00:00:00Z'
ACCEPT='2026-10-21T00:01:00Z'
CONSENT='2026-10-21T00:02:00Z'
CALL='2026-10-21T00:03:00Z'
NOW='2026-10-21T00:05:00Z'
END='2026-10-22T00:00:00Z'

def schema():
    path=Path(__file__).resolve().parents[3]/'docs/profiles/authorization-evidence-v1-draft.schema.md'
    return json.loads(path.read_text().split('```json\n')[1].split('```')[0])

class Fixture:
    def __init__(self, context=False, calls=1, confirmation='automatic', bad_consent=False,
                 delegated=False, expired_delegation=False, chained=False, relay=False):
        self.artifacts={}
        self.objects={}
        self.keys=[Ed25519PrivateKey.from_private_bytes(bytes([i])*32) for i in range(1,5)]
        self.actors=['ed25519:'+k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex() for k in self.keys]
        self.keyrefs=[self.blob(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw),'application/octet-stream') for k in self.keys]
        principal,agent,channel,operational=self.actors
        self.action={'tool_id':'test.tool','version':'1.0.0','operation':'read','resources':['test.resource'],
                     'valid_from':START,'expires_at':END,'max_call_budget':self.money(10)}
        self.limits={'allow':[copy.deepcopy(self.action)],'deny':[],'total_budget':self.money(100)}
        interface=self.json({'interface':'synthetic'})
        behavior=self.object('ToolBehavior',operations=[{'operation':'read','classes':['read'],
                              'context_mode':'external-state' if context else 'pure'}],interface_bytes_ref=interface)
        tool=self.object('ToolEntry',0,tool_id='test.tool',version='1.0.0',provider=principal,registrar=principal,
                         interface_ref=interface,behavior_ref=self.json(behavior),operation_classes=['read'],confirmation=confirmation,
                         boundary='local',stateful=context,valid_from=START)
        restriction=self.object('RestrictionProfile',extra_confirmation='none',not_before=START,expires_at=END)
        policy=self.object('DeploymentPolicy',0,operator=principal,revision='1',baseline_refs=[self.ref(tool)],
                           deny_rules=[],extra_requirements_ref=self.json(restriction),valid_from=START)
        registry=self.object('RegistrySnapshot',0,entry_refs=[self.ref(tool)],registrar_key=principal,snapshot_at=START)
        events=[]
        for i in range(4):
            root=agent if i==3 else self.actors[i]
            event=self.object('KeyEvent',1 if i==3 else i,root=root,key=self.actors[i],state='active',effective_at=START,issuer=root)
            events.append(self.json(event))
        delegation_refs=[]
        if delegated:
            parent=copy.deepcopy(self.limits);parent['total_budget']=self.money(200)
            delegation=self.object('Delegation',1,issuer_root=agent,issuer_key=agent,subject_key=operational,
                 parent_refs=[],action_limits=parent,issued_at=START,expires_at=CONSENT if expired_delegation else END)
            delegation_refs=[self.json(delegation)]
        identity=self.object('IdentityProfile',suite=SUITE,principal_keys=[principal],agent_root_keys=[agent],
                 registrar_keys=[principal],operator_keys=[principal],provisioner_keys=[principal],custodian_keys=[principal],
                 relayer_keys=[principal],delegation_artifact_refs=delegation_refs,key_event_refs=events)
        confirm=self.object('ConfirmationProfile',human_in_loop='principal-affirmative-per-invocation',
                 restricted='principal-out-of-band-per-invocation',channel_authority_keys=[channel],channel_receipt_refs=[],approval_reuse='forbidden')
        evidence=self.object('EvidenceProfile',mapping='linear-bijection-stepbindings-v1',payload_encoding='RFC8785-JCS-IJSON',
                 hash_encoding='sha256-colon-lowerhex',subjective_evaluator_keys=[],subjective_result_refs=[])
        budget=self.object('BudgetProfile',mode='single-deployment-atomic-reservation-required',deployment_id='test',
                 ledger_authority_keys=[principal],ledger_protocol='reserve-before-call-consume-or-release-v1',ledger_event_refs=[],cross_deployment='unsupported')
        if relay:
            rule=self.object('FinalityRule',chain_id='test-chain-a',basis='pinned-relayer-asserted-finality',minimum_confirmations=2,maximum_age_seconds=600)
            receipt=self.object('RelayReceipt',0,relayer=principal,source_chain='test-chain-a',destination_chain='test-chain-b',
                 canonical_payload_ref=interface,finality_rule_ref=self.json(rule),observed_at=CALL,confirmations=2)
            relayobj=self.object('RelayProfile',mode='single-trust-path',source_chain='test-chain-a',destination_chain='test-chain-b',
                 relayer_key=principal,finality_rule_ref=self.json(rule),freshness_seconds=600,receipt_refs=[self.json(receipt)])
        else:
            relayobj=self.object('RelayProfile',mode='none')
        access=self.object('CustodyAccessProfile',authorized_reader_keys=[principal],export='complete-bytes-manifest-v1',
                 retention_until=END,challenge_ends_at=END,appeal_ends_at=END)
        accessref=self.json(access)
        custody=self.object('CustodyProfile',0,custodian=principal,evidence_classes=['synthetic'],retention_until=END,
                 access_policy_ref=accessref,export_policy_ref=accessref,mirror_refs=[],challenge_appeal_policy_ref=accessref)
        manifest=self.object('DependencyManifest',registry_snapshot_ref=self.json(registry),tool_entry_refs=[self.ref(tool)],
                 deployment_policy_refs=[self.ref(policy)],identity_profile_ref=self.json(identity),confirmation_profile_ref=self.json(confirm),
                 custody_profile_ref=self.ref(custody),evidence_profile_ref=self.json(evidence),budget_profile_ref=self.json(budget),relay_profile_ref=self.json(relayobj))
        inputs=[self.json({'synthetic_input':i}) for i in range(calls)]
        outputs=[self.json({'synthetic_output':i}) for i in range(calls)]
        plan=self.object('Plan',ordered_actions=[{'action':copy.deepcopy(self.action),'input_ref':x} for x in inputs],expected_artifact_descriptions=['synthetic'])
        intent=self.object('Intent',0,principal=principal,body='synthetic offline fixture only',constraints=self.limits,
                 success_criteria_ref=self.json({'kind':'exact-artifact-digests','digests':[o['digest'] for o in outputs]}),
                 evidence_requirements_ref=self.json({'profile':PROFILE,'evidence_profile_ref':self.json(evidence)}),nonce='intent',issued_at=START,expires_at=END)
        acceptance=self.object('Acceptance',3 if delegated else 1,intent_ref=self.ref(intent),agent_root=agent,
                 signer_key_ref=self.keyrefs[3 if delegated else 1],delegation_refs=delegation_refs,plan_ref=self.ref(plan),
                 dependency_manifest_ref=self.ref(manifest),action_limits=self.limits,fee_quote=self.money(1),deadline=END,
                 nonce='accept',issued_at=ACCEPT,expires_at=END)
        consent=self.object('Consent',0,principal=channel if bad_consent else principal,acceptance_ref=self.ref(acceptance),
                 dependency_manifest_ref=self.ref(manifest),action_limits=self.limits,nonce='consent',issued_at=CONSENT,expires_at=END)
        invs=[];bindings=[];steps=[];approvals=[];ctxrefs=[]
        previous=digest(canonical(plan))
        for i in range(calls):
            inv=self.object('Invocation',acceptance_ref=self.ref(acceptance),plan_index=i,tool_entry_ref=self.ref(tool),
                 deployment_policy_ref=self.ref(policy),operation='read',resource='test.resource',input_ref=inputs[i],budget=self.money(10),nonce=str(i),issued_at=CONSENT)
            invs.append(inv)
            refs=[]
            step={'tool_id':'test.tool','input_hash':inputs[i]['digest'],'output_hash':outputs[i]['digest'],'timestamp':CALL}
            if context:
                cfg=self.object('Configuration',0,config_bytes_ref=self.json({'config':i}),provisioner=principal,effective_from=START,effective_until=END)
                ctx=self.object('ContextManifest',pre_state_refs=[self.json({'state':i})],retrieval_procedure_refs=[self.json({'procedure':'exact'})],
                    configuration_refs=[self.ref(cfg)],provenance_refs=[self.json({'claim':'synthetic pre-state'})],observed_at=CONSENT)
                refs=[self.ref(ctx)];ctxrefs+=refs;step['context_hash']=digest(canonical(ctx))
            if chained:
                step['prev_hash']=previous
                previous=digest(canonical({k:v for k,v in step.items() if k!='prev_hash'}))
            steps.append(step)
            bindings.append({'step_index':i,'invocation_ref':self.ref(inv),'context_refs':refs,'input_ref':inputs[i],
                             'output_ref':outputs[i],'step_digest':digest(canonical(step))})
            if confirmation!='automatic':
                approval=self.object('InvocationApproval',0,principal=principal,acceptance_ref=self.ref(acceptance),invocation_ref=self.ref(inv),
                    dependency_manifest_ref=self.ref(manifest),approval_mode='out_of_band' if confirmation=='restricted' else 'affirmative',
                    channel_evidence_ref=self.json(confirm),nonce='approval'+str(i),issued_at=CONSENT,expires_at=END)
                approvals.append(approval)
                self.object('ChannelReceipt',2,principal=principal,invocation_ref=self.ref(inv),mode=approval['approval_mode'],channel_id='synthetic-test-channel',
                    authority=channel,observed_at='2026-10-21T00:02:30Z',approval_signing_digest='sha256:'+signing_digest(approval).hex())
        proof={'spec_version':'0','intent_id':intent['id'],'mandate_id':acceptance['id'],'plan':plan,'steps':steps,
               'artifacts':[o['digest'] for o in outputs],'success_claim':{'artifact_digests':[o['digest'] for o in outputs]}}
        proof=self.sign(proof,3 if delegated else 1)
        proofref=self.json(proof)
        exported=[{'digest':h,'media_type':'application/json'} for h,raw in self.artifacts.items() if raw.startswith(b'{')]
        self.bundle=self.object('EvidenceBundle',intent_ref=self.ref(intent),acceptance_ref=self.ref(acceptance),consent_refs=[self.ref(consent)],
                 approval_refs=[self.ref(a) for a in approvals],dependency_manifest_ref=self.ref(manifest),invocation_refs=[self.ref(x) for x in invs],
                 context_refs=ctxrefs,aggregate_proof_ref=proofref,exported_evidence_refs=exported,step_bindings=bindings)
        self.schema=schema();self.trust=Trust(principal,digest(canonical(self.schema)),NOW,NOW,frozenset([intent["id"]]))
        self.proof=proof;self.acceptance=acceptance;self.intent=intent

    def money(self,n):return {'asset':'TEST','network':'offline','amount':str(n)}
    def blob(self,raw,media):
        h=digest(raw);self.artifacts[h]=raw;return {'digest':h,'media_type':media}
    def json(self,value):return self.blob(canonical(value),'application/json')
    def ref(self,v):return {'id':v['id'],'object_type':v['object_type'],'profile':v['profile']}
    def sign(self,v,key):
        v=dict(v);v.pop('signature',None);v['signature']={'scheme':SUITE,'key_ref':self.keyrefs[key],'value':self.keys[key].sign(signing_digest(v)).hex()};return v
    def object(self,kind,signer=None,**fields):
        v={'profile':PROFILE,'object_type':kind,**fields};v['id']=object_id(v)
        if signer is not None:v=self.sign(v,signer)
        self.json(v);self.objects[v['id']]=v;return v
    def replace_bundle(self,**fields):
        self.artifacts.pop(digest(canonical(self.bundle)),None)
        v=dict(self.bundle);v.update(fields);v.pop('id');v['id']=object_id(v);self.bundle=v;self.json(v)
    def replace_proof(self,proof):
        proof=self.sign(proof,1);ref=self.json(proof);bindings=copy.deepcopy(self.bundle['step_bindings'])
        for step,binding in zip(proof['steps'],bindings):binding['step_digest']=digest(canonical(step))
        self.replace_bundle(aggregate_proof_ref=ref,step_bindings=bindings)
    def store(self):return Store(self.artifacts,self.schema)

    def request(self):
        result = {k:copy.deepcopy(self.bundle[k]) for k in ['intent_ref','acceptance_ref','consent_refs','approval_refs','dependency_manifest_ref','invocation_refs']}
        result['exported_evidence_refs'] = [self.json(v) for v in self.objects.values() if v['object_type'] == 'ChannelReceipt']
        return result
