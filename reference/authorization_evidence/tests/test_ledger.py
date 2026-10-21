import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ..ledger import Ledger
from ..core import Rejected

KEY=bytes([1])*32

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'ledger.db'
        self.key=Ed25519PrivateKey.from_private_bytes(KEY);self.l=Ledger(self.path,'test',self.key)
    def tearDown(self):
        self.l.close();self.tmp.cleanup()
    def reserve(self,inv='i',nonce='n',amount=7,account='intent'):
        return self.l.reserve(inv,nonce,{account:10},'TEST','offline',amount)
    def test_total_and_shared_intent_ceiling(self):
        self.assertEqual(self.reserve(), 'new_reservation')
        with self.assertRaises(Rejected):self.reserve('j','m',4)
        self.l.finish('i','consume',3)
        self.assertEqual(self.reserve('j','m',7), 'new_reservation')
        self.assertTrue(self.l.audit())
    def test_idempotent_no_action_retry(self):
        self.reserve();self.assertEqual(self.reserve(),'reserved')
        self.l.finish('i','consume',3);self.assertEqual(self.reserve(),'consume')
        self.assertEqual(self.l.finish('i','consume',3),'consume')
        with self.assertRaises(Rejected):self.l.finish('i','release')
        with self.assertRaises(Rejected):self.l.finish('i','consume',4)
    def test_nonce_replay(self):
        self.reserve()
        with self.assertRaises(Rejected):self.reserve('j','n',1)
    def test_currency_and_immutable_ceiling(self):
        self.reserve()
        with self.assertRaises(Rejected):self.l.reserve('j','m',{'intent':100},'TEST','offline',1)
        with self.assertRaises(Rejected):self.l.reserve('j','m',{'intent':10},'USD','offline',1)
    def test_release_and_overconsume(self):
        self.reserve()
        with self.assertRaises(Rejected):self.l.finish('i','consume',8)
        self.l.finish('i','release');self.assertEqual(self.reserve('j','m',10),'new_reservation')
    def test_multi_account_rollback(self):
        self.reserve(amount=9)
        with self.assertRaises(Rejected):self.l.reserve('j','m',{'another':10,'intent':10},'TEST','offline',2)
        self.assertIsNone(self.l.db.execute('SELECT * FROM accounts WHERE id="another"').fetchone())
        self.assertTrue(self.l.audit())
    def test_integer_budgets_not_sqlite_float_or_overflow(self):
        big=10**40
        self.l.reserve('big','big',{'big':big},'X','local',big-1)
        self.l.finish('big','consume',big-2);self.assertTrue(self.l.audit())
        for bad in [-1,1.5,True]:
            with self.assertRaises(Rejected):self.reserve('bad','bad',bad)
    def test_concurrent_last_unit(self):
        def worker(i):
            ledger=Ledger(self.path,'test',self.key)
            try:return ledger.reserve(str(i),str(i),{'intent':1},'TEST','offline',1)
            except Rejected:return 'denied'
            finally:ledger.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(worker,range(16)))
        self.assertEqual(results.count('new_reservation'),1)
        self.assertTrue(self.l.audit())
    def test_crash_before_commit_rolls_back(self):
        code='''import os,sqlite3,sys
c=sqlite3.connect(sys.argv[1]);c.execute("BEGIN IMMEDIATE")
c.execute("INSERT INTO accounts VALUES ('fake','X','N','1','1','0')")
os._exit(91)'''
        r=subprocess.run([sys.executable,'-c',code,str(self.path)])
        self.assertEqual(r.returncode,91);self.assertTrue(self.l.audit())
    def test_crash_after_commit_preserves_reservation(self):
        code='''import os,sys
from reference.authorization_evidence.ledger import Ledger
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
l=Ledger(sys.argv[1],'test',Ed25519PrivateKey.from_private_bytes(bytes([1])*32))
l.reserve('i','n',{'intent':10},'TEST','offline',7)
os._exit(92)'''
        r=subprocess.run([sys.executable,'-c',code,str(self.path)])
        self.assertEqual(r.returncode,92);self.assertTrue(self.l.audit());self.assertEqual(self.reserve(),'reserved')
    def test_materialized_state_tamper(self):
        self.reserve();self.l.db.execute("UPDATE accounts SET reserved='0'")
        with self.assertRaises(Rejected):self.l.audit()
    def test_signed_event_tamper(self):
        self.reserve();self.l.db.execute("UPDATE events SET digest='sha256:000'")
        with self.assertRaises(Rejected):self.l.audit()
    def test_external_checkpoint_detects_rollback(self):
        backup=Path(self.tmp.name)/'backup.db';target=sqlite3.connect(backup);self.l.db.backup(target);target.close()
        self.reserve();checkpoint=self.l.export()['checkpoint']
        older=Ledger(backup,'test',self.key)
        try:
            with self.assertRaises(Rejected):older.audit(checkpoint)
        finally:older.close()
    def test_checkpoint_wrong_authority(self):
        checkpoint=self.l.export()['checkpoint'];checkpoint['authority']='ed25519:'+'00'*32
        with self.assertRaises(Rejected):self.l.audit(checkpoint)
    def test_reservation_unknown_execution_is_not_auto_released(self):
        self.reserve();self.l.close();self.l=Ledger(self.path,'test',self.key)
        self.assertEqual(self.reserve(),'reserved')
        self.assertEqual(self.l.db.execute('SELECT reserved FROM accounts').fetchone()[0],'7')

    def test_materialized_nonce_tamper(self):
        self.reserve();self.l.db.execute("UPDATE reservations SET nonce='different'")
        with self.assertRaises(Rejected):self.l.audit()
    def test_authority_nonce_binding_across_bundles(self):
        self.l.reserve('a','a',{'shared':10},'X','N',1,{'principal/Intent/nonce':'intent1'})
        with self.assertRaises(Rejected):self.l.reserve('b','b',{'shared':10},'X','N',1,{'principal/Intent/nonce':'intent2'})
        self.assertTrue(self.l.audit())
