import copy
import json
import tempfile
import unittest
from pathlib import Path
from ..core import Store, Rejected, canonical, digest, strict_json, object_id
from ..verifier import Verifier, Trust
from ..admission import admit
from ..ledger import Ledger
from .fixtures import Fixture, NOW

class VerifierTests(unittest.TestCase):
    def result(self,f):return Verifier(f.store(),f.trust).verify(f.ref(f.bundle))
    def test_valid_pure(self):self.assertEqual(self.result(Fixture()).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_valid_chained_stateful_and_config(self):
        self.assertEqual(self.result(Fixture(context=True,calls=2,chained=True)).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_valid_human_approval(self):self.assertEqual(self.result(Fixture(confirmation='human-in-loop')).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_valid_restricted_channel(self):self.assertEqual(self.result(Fixture(confirmation='restricted')).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_valid_delegated_key(self):self.assertEqual(self.result(Fixture(delegated=True)).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_pinned_relayer_claim_only(self):self.assertEqual(self.result(Fixture(relay=True)).category,'VERIFIED_WITH_BUDGET_PENDING')
    def test_expired_delegation(self):self.assertEqual(self.result(Fixture(delegated=True,expired_delegation=True)).category,'UNAUTHORIZED')
    def test_no_consent(self):
        f=Fixture();f.replace_bundle(consent_refs=[]);self.assertEqual(self.result(f).category,'INVALID')
    def test_wrong_principal_consent(self):self.assertEqual(self.result(Fixture(bad_consent=True)).category,'UNAUTHORIZED')
    def test_independent_trust_anchor(self):
        f=Fixture();f.trust.principal=f.actors[2];self.assertEqual(self.result(f).category,'UNAUTHORIZED')
    def test_schema_pin(self):
        f=Fixture();f.trust.schema_digest='sha256:'+'00'*32;self.assertEqual(self.result(f).category,'UNSUPPORTED')
    def test_stale_history_checkpoint(self):
        f=Fixture();f.trust.history_as_of='2026-10-21T00:01:00Z';self.assertEqual(self.result(f).category,'UNAVAILABLE')
    def test_missing_bytes(self):
        f=Fixture();f.artifacts.pop(f.bundle['aggregate_proof_ref']['digest']);self.assertEqual(self.result(f).category,'UNAVAILABLE')
    def test_digest_tamper(self):
        f=Fixture();f.artifacts[f.bundle['aggregate_proof_ref']['digest']]=b'{}';self.assertEqual(self.result(f).category,'INVALID')
    def test_reordered_steps(self):
        f=Fixture(calls=2);f.replace_bundle(step_bindings=list(reversed(f.bundle['step_bindings'])));self.assertEqual(self.result(f).category,'INVALID')
    def test_duplicate_invocation(self):
        f=Fixture(calls=2);f.replace_bundle(invocation_refs=[f.bundle['invocation_refs'][0]]*2);self.assertEqual(self.result(f).category,'INVALID')
    def test_missing_step_binding(self):
        f=Fixture();f.replace_bundle(step_bindings=[]);self.assertEqual(self.result(f).category,'INVALID')
    def test_swapped_contexts_same_tool(self):
        f=Fixture(context=True,calls=2);b=copy.deepcopy(f.bundle['step_bindings']);b[0]['context_refs'],b[1]['context_refs']=b[1]['context_refs'],b[0]['context_refs'];f.replace_bundle(step_bindings=b);self.assertEqual(self.result(f).category,'EVIDENCE_MISMATCH')
    def test_orphan_context(self):
        f=Fixture(context=True);f.replace_bundle(context_refs=[]);self.assertEqual(self.result(f).category,'INVALID')
    def test_wrong_input_pair(self):
        f=Fixture(calls=2);b=copy.deepcopy(f.bundle['step_bindings']);b[0]['input_ref']=b[1]['input_ref'];f.replace_bundle(step_bindings=b);self.assertEqual(self.result(f).category,'INVALID')
    def test_changed_plan(self):
        f=Fixture();proof=copy.deepcopy(f.proof);proof['plan']['ordered_actions']=[];f.replace_proof(proof);self.assertEqual(self.result(f).category,'INVALID')
    def test_chain_break(self):
        f=Fixture(calls=2,chained=True);proof=copy.deepcopy(f.proof);proof['steps'][1]['prev_hash']='sha256:'+'00'*32;f.replace_proof(proof);self.assertEqual(self.result(f).category,'INVALID')
    def test_slice_is_not_aggregate(self):
        f=Fixture(calls=2);proof=copy.deepcopy(f.proof);proof['steps']=proof['steps'][:1];f.replace_proof(proof);self.assertEqual(self.result(f).category,'INVALID')
    def test_unknown_aggregate_version(self):
        f=Fixture();proof=copy.deepcopy(f.proof);proof['spec_version']='999';f.replace_proof(proof);self.assertEqual(self.result(f).category,'UNSUPPORTED')
    def test_unsupported_attestation_never_green(self):
        f=Fixture();proof=copy.deepcopy(f.proof);proof['steps'][0]['attestation']={'unknown':'claim'};f.replace_proof(proof);self.assertEqual(self.result(f).category,'UNSUPPORTED')
    def test_approval_missing(self):
        f=Fixture(confirmation='restricted');f.replace_bundle(approval_refs=[]);self.assertEqual(self.result(f).category,'UNAUTHORIZED')
    def test_closed_bundle_fields(self):
        f=Fixture();f.replace_bundle(allow_all=True);self.assertEqual(self.result(f).category,'INVALID')
    def test_ambiguous_object_signature_wrapper(self):
        f=Fixture();x=copy.deepcopy(f.acceptance);x['signature']['value']='00'*64;f.json(x);self.assertEqual(self.result(f).category,'INVALID')
    def test_ledger_integration_and_replay(self):
        f=Fixture()
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'l.db','test',f.keys[0]);checkpoint=ledger.export()['checkpoint']
            try:
                r=admit(f.store(),f.trust,f.request(),0,ledger,checkpoint)
                self.assertEqual(r.category,'RESERVED_NO_ACTION')
                self.assertEqual(admit(f.store(),f.trust,f.request(),0,ledger,checkpoint).category,'ALREADY_RECORDED_NO_ACTION')
                ledger.finish(f.bundle['invocation_refs'][0]['id'],'consume',6)
                self.assertTrue(ledger.audit())
            finally:ledger.close()
    def test_wrong_ledger_authority(self):
        f=Fixture()
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'l.db','test',f.keys[2])
            try:self.assertEqual(admit(f.store(),f.trust,f.request(),0,ledger,ledger.export()['checkpoint']).category,'UNAUTHORIZED')
            finally:ledger.close()
    def test_checkpoint_required_for_admission(self):
        f=Fixture()
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'l.db','test',f.keys[0])
            try:self.assertEqual(admit(f.store(),f.trust,f.request(),0,ledger,None).category,'UNAVAILABLE')
            finally:ledger.close()
    def test_strict_json(self):
        for raw in [b'{"x":1,"x":2}',b'{"n":NaN}',b'{"n":9007199254740992}',b'"\\ud800"']:
            with self.subTest(raw=raw),self.assertRaises(Rejected):strict_json(raw)
    def test_export_path_escape(self):
        f=Fixture()
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'export.json').write_text(json.dumps({'bundle_ref':f.ref(f.bundle),'artifacts':{'sha256:'+'00'*32:'../escape'}}))
            with self.assertRaises(Rejected):Store.directory(folder,f.schema)
    def test_invalid_acceptance_signature_not_only_digest(self):
        f=Fixture();raw=canonical(f.acceptance);f.artifacts.pop(digest(raw))
        value=copy.deepcopy(f.acceptance);value['signature']['value']='00'*64;f.json(value)
        self.assertEqual(self.result(f).category,'INVALID')
    def test_unknown_intent_evidence_policy_not_ignored(self):
        f=Fixture();value=copy.deepcopy(f.intent)
        # Same object id but changed content cannot masquerade as valid bytes.
        raw=canonical(value);f.artifacts.pop(digest(raw));value['evidence_requirements_ref']=f.json({'unknown_allow':True});f.json(value)
        self.assertEqual(self.result(f).category,'INVALID')
    def test_cli_export_offline(self):
        import subprocess,sys
        f=Fixture()
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);index={}
            for i,(h,raw) in enumerate(f.artifacts.items()):
                name=str(i)+'.bin';(folder/name).write_bytes(raw);index[h]=name
            (folder/'export.json').write_text(json.dumps({'bundle_ref':f.ref(f.bundle),'artifacts':index}))
            schema=Path(__file__).resolve().parents[3]/'docs/profiles/authorization-evidence-v1-draft.schema.md'
            r=subprocess.run([sys.executable,'-m','reference.authorization_evidence','--export',str(folder),
                '--schema',str(schema),'--schema-digest',f.trust.schema_digest,'--principal',f.trust.principal,
                '--now',f.trust.now,'--history-as-of',f.trust.history_as_of],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['category'],'VERIFIED_WITH_BUDGET_PENDING')
    def test_semantic_verification_has_no_socket_calls(self):
        from unittest.mock import patch
        f=Fixture(context=True,confirmation='restricted')
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            self.assertEqual(self.result(f).category,'VERIFIED_WITH_BUDGET_PENDING')

    def test_preflight_requires_no_execution_proof_or_output(self):
        f=Fixture();request=f.request()
        f.artifacts.pop(f.bundle['aggregate_proof_ref']['digest'])
        for binding in f.bundle['step_bindings']:f.artifacts.pop(binding['output_ref']['digest'])
        r=Verifier(f.store(),f.trust).authorize(request)
        self.assertEqual(r.category,'AUTHORIZED_WITH_BUDGET_PENDING')
    def test_completed_bundle_cannot_be_admitted_as_new_request(self):
        f=Fixture();self.assertEqual(Verifier(f.store(),f.trust).authorize(f.bundle).category,'INVALID')
    def test_preflight_independent_active_intent_checkpoint(self):
        f=Fixture();f.trust.active_intent_ids=frozenset()
        self.assertEqual(Verifier(f.store(),f.trust).authorize(f.request()).category,'UNAVAILABLE')
    def test_preflight_stale_checkpoint(self):
        f=Fixture();f.trust.history_as_of='2026-10-21T00:03:00Z'
        self.assertEqual(Verifier(f.store(),f.trust).authorize(f.request()).category,'UNAVAILABLE')
