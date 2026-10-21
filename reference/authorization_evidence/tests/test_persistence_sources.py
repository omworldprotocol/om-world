"""Synthetic engineering regressions; no real source/service evidence. Apache-2.0."""
import copy
import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from ..core import SCHEMA_DIGEST,signing_digest,Rejected
from ..ledger import Ledger
from ..checkpoints import CheckpointStore
from ..sources import Source,SourcePolicy,SourceBinder
from ..persistent import persistent_admit
from .fixtures import Fixture,NOW

class PersistenceSources(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'ledger').mkdir();self.path=self.root/'ledger/state.db'
        self.f=Fixture();self.l=Ledger(self.path,'test',self.f.keys[0])
        self.a=CheckpointStore(self.root/'anchor',self.path,'test',self.l.public,'test-anchor')
        self.a.initialize_empty(self.l)
        self.keys={r:Ed25519PrivateKey.from_private_bytes(bytes([i])*32) for i,r in enumerate(('status','history','clock'),11)}
        sources={r:Source('test-'+r,'ed25519:'+k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex(),60,'synthetic_test') for r,k in self.keys.items()}
        self.policy=SourcePolicy(self.f.actors[0],SCHEMA_DIGEST,**sources,allow_synthetic=True)
        self.now=NOW;self.b=SourceBinder(self.policy,lambda:self.now)
        store=self.f.store();request=self.f.request();manifest=store.resolve(request['dependency_manifest_ref'],'DependencyManifest');identity=store.artifact(manifest['identity_profile_ref'],'IdentityProfile')
        payloads={'status':{'active_intent_ids':[self.f.intent['id']]},'history':{'identity_profile_digest':manifest['identity_profile_ref']['digest'],'key_event_digests':[x['digest'] for x in identity['key_event_refs']]},'clock':{'time_basis':'UTC-source-attestation'}}
        self.r={r:{'format':'omworld.offline-source.v1','role':r,'source_id':sources[r].source_id,'authority':sources[r].authority,'revision':1,'principal':self.policy.principal,'schema_digest':SCHEMA_DIGEST,'evidence_kind':'synthetic_test','as_of':NOW,'issued_at':NOW,'expires_at':'2026-10-21T00:06:00Z','payload':payloads[r]} for r in sources}
        self.sign()
    def tearDown(self):
        self.l.db.close();self.tmp.cleanup()
    def sign(self):
        for r,v in self.r.items():v['signature']=self.keys[r].sign(signing_digest(v)).hex()
    def run_admit(self,binder=True):
        return persistent_admit(self.f.store(),self.b if binder else None,self.f.request(),0,self.l,self.a,self.r)
    def no_reservation(self):
        self.assertEqual(self.l.db.execute('SELECT count(*) FROM reservations').fetchone()[0],0)
    def refuse(self):
        result=self.run_admit();self.assertNotIn(result.category,('TEST_RESERVED_NO_ACTION','TEST_ALREADY_RECORDED_NO_ACTION'));self.no_reservation();return result
    def test_success_reopen_idempotent(self):
        self.assertEqual(self.run_admit().category,'TEST_RESERVED_NO_ACTION')
        before=self.a.read();self.assertGreaterEqual(before['checkpoint']['sequence'],0)
        self.l.db.close();self.l=Ledger(self.path,'test',self.f.keys[0])
        self.assertEqual(self.run_admit().category,'TEST_ALREADY_RECORDED_NO_ACTION')
        self.assertEqual(before['checkpoint'],self.a.read()['checkpoint'])
    def test_no_source_configuration(self):
        self.assertEqual(self.run_admit(False).category,'UNAVAILABLE');self.no_reservation()
    def test_synthetic_default_refused(self):
        self.b=SourceBinder(replace(self.policy,allow_synthetic=False),lambda:self.now);self.refuse()
    def test_expired(self):
        self.now='2026-10-21T00:06:00Z';self.refuse()
    def test_stale(self):
        self.b=SourceBinder(replace(self.policy,clock=replace(self.policy.clock,max_age_seconds=0)),lambda:'2026-10-21T00:05:01Z');self.refuse()
    def test_future(self):
        self.now='2026-10-21T00:04:59Z';self.refuse()
    def test_wrong_signature(self):
        self.r['status']['signature']='00'*64;self.refuse()
    def test_wrong_source(self):
        self.r['status']['source_id']='unconfigured';self.sign();self.refuse()
    def test_wrong_principal(self):
        self.r['history']['principal']=self.f.actors[1];self.sign();self.refuse()
    def test_wrong_schema(self):
        self.r['clock']['schema_digest']='sha256:'+'0'*64;self.sign();self.refuse()
    def test_missing_role(self):
        del self.r['clock'];self.refuse()
    def test_misaligned_context(self):
        self.r['clock']['as_of']='2026-10-21T00:04:59Z';self.sign();self.refuse()
    def test_wrong_history_commitment(self):
        self.r['history']['payload']['identity_profile_digest']='sha256:'+'0'*64;self.sign();self.refuse()
    def test_missing_history_events(self):
        self.r['history']['payload']['key_event_digests']=[];self.sign();self.refuse()
    def test_malformed_payload_not_persisted(self):
        self.r['status']['payload']['active_intent_ids']='not-a-list';self.sign();self.refuse();self.assertEqual(self.a.read()['sources'],{})
    def test_cancellation_highwater_survives_denial(self):
        old=copy.deepcopy(self.r);self.r['status']['revision']=2;self.r['status']['payload']['active_intent_ids']=[];self.sign();self.refuse()
        self.assertEqual(self.a.read()['sources']['status']['receipt']['revision'],2)
        self.r=old;self.assertEqual(self.refuse().category,'UNAVAILABLE')
    def test_same_revision_fork(self):
        self.run_admit();self.r['status']['payload']['active_intent_ids']=[];self.sign()
        self.assertEqual(self.run_admit().category,'INVALID')
    def test_asof_regression(self):
        self.run_admit();self.r['clock']['revision']=2;self.r['clock']['as_of']='2026-10-21T00:04:59Z';self.sign()
        self.assertEqual(self.run_admit().category,'UNAVAILABLE')
    def test_expiry_during_admission(self):
        calls=[0]
        def wall():
            calls[0]+=1
            return NOW if calls[0]<3 else '2026-10-21T00:06:00Z'
        self.b=SourceBinder(self.policy,wall);self.refuse()
    def test_wall_bounds_after_snapshot(self):
        self.now='2026-10-21T00:05:01Z'
        with patch.object(self.b,'current_bounds',side_effect=Rejected('UNAUTHORIZED','expired finite authorization')):self.refuse()
    def test_missing_anchor_no_rebootstrap(self):
        self.a.path.unlink()
        with self.assertRaises(Rejected):self.a.read()
        self.refuse()
    def test_bootstrap_used_ledger_refused(self):
        self.l.reserve('i','n',{'a':10},'TEST','offline',1);self.a.path.unlink()
        with self.assertRaises(Rejected):self.a.initialize_empty(self.l)
    def test_duplicate_bootstrap_refused(self):
        with self.assertRaises(Rejected):self.a.initialize_empty(self.l)
    def test_nested_storage_refused(self):
        with self.assertRaises(Rejected):CheckpointStore(self.root/'ledger/anchor',self.path,'test',self.l.public,'x')
    def test_symlink_refused(self):
        (self.root/'link').symlink_to(self.root/'anchor',target_is_directory=True)
        with self.assertRaises(Rejected):CheckpointStore(self.root/'link',self.path,'test',self.l.public,'x')
    def test_atomic_replace_failure_preserves_anchor(self):
        old=self.a.path.read_bytes()
        with patch('os.replace',side_effect=OSError('injected replace failure')):
            with self.assertRaises(OSError):self.a.advance(self.l)
        self.assertEqual(self.a.path.read_bytes(),old)
    def test_commit_anchor_gap_recovery(self):
        write=self.a._write;count=[0]
        def failure(value):
            count[0]+=1
            if count[0]==2:raise OSError('injected post-commit anchor write failure')
            return write(value)
        with patch.object(self.a,'_write',side_effect=failure):self.assertEqual(self.run_admit().category,'WAITING_ANCHOR_NO_ACTION')
        self.assertEqual(self.a.read()['checkpoint']['sequence'],-1)
        result=self.a.recover(self.l);self.assertEqual(result['state'],'RECOVERED_NO_ACTION');self.assertEqual(len(result['pending_reservations']),1)
        self.assertGreaterEqual(self.a.read()['checkpoint']['sequence'],0)
    def test_database_rollback_rejected(self):
        backup=sqlite3.connect(self.root/'backup.db');self.l.db.backup(backup)
        self.run_admit();anchor=self.a.path.read_bytes();backup.backup(self.l.db);backup.close()
        with self.assertRaises(Rejected):self.a.recover(self.l)
        self.assertEqual(anchor,self.a.path.read_bytes())
    def test_corrupt_signature_refused(self):
        value=self.a.read();value['checkpoint']['signature']='00'*64;self.a._write(value)
        with self.assertRaises(Rejected):self.a.recover(self.l)
    def test_storage_identity_refused(self):
        other=CheckpointStore(self.root/'anchor',self.path,'test',self.l.public,'other')
        with self.assertRaises(Rejected):other.read()

    def test_expiry_after_writer_lock_before_write(self):
        original=self.l.audit
        def audited(checkpoint=None):
            result=original(checkpoint)
            if self.l.db.in_transaction:self.now='2026-10-21T00:06:00Z'
            return result
        with patch.object(self.l,'audit',side_effect=audited):self.refuse()
    def test_finite_plan_expiry_wall_recheck(self):
        store=self.f.store();request=self.f.request()
        acceptance=store.resolve(request['acceptance_ref'],'Acceptance')
        plan=store.resolve(acceptance['plan_ref'],'Plan')
        plan['ordered_actions'][0]['action']['expires_at']=NOW
        original=store.resolve
        def resolve(ref,kind):return plan if kind=='Plan' else original(ref,kind)
        with patch.object(store,'resolve',side_effect=resolve):
            with self.assertRaises(Rejected):self.b.current_bounds(store,request,0,NOW)
    def test_file_fsync_failure_no_budget_write(self):
        old=self.a.path.read_bytes()
        with patch('os.fsync',side_effect=OSError('injected fsync failure')):self.refuse()
        self.assertEqual(self.a.path.read_bytes(),old)
    def test_directory_fsync_uncertain_after_commit(self):
        import os
        original=os.fsync;calls=[0]
        def fsync(fd):
            calls[0]+=1
            if calls[0]==4:raise OSError('injected directory fsync uncertainty')
            return original(fd)
        with patch('os.fsync',side_effect=fsync):self.assertEqual(self.run_admit().category,'WAITING_ANCHOR_NO_ACTION')
        self.assertEqual(len(self.a.recover(self.l)['pending_reservations']),1)
