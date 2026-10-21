"""Deterministic F1 regressions. Synthetic local state only; no sleep-based scheduling."""
import tempfile
import threading
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ..ledger import Ledger
from ..core import Rejected
from ..admission import admit
from .fixtures import Fixture

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'ledger.db'
        self.key=Ed25519PrivateKey.from_private_bytes(bytes([1])*32)
        self.reader=Ledger(self.path,'test',self.key)
    def tearDown(self):
        self.reader.close();self.temp.cleanup()

    def test_writer_commits_between_log_and_materialized_read(self):
        self.reader.reserve('before','before',{'shared':10},'TEST','offline',1)
        checkpoint=self.reader.export()['checkpoint']
        ready=threading.Event();between=threading.Event();committed=threading.Event()
        errors=[];observed=[];armed=[True]
        def writer():
            ledger=None
            try:
                ledger=Ledger(self.path,'test',self.key);ready.set()
                if not between.wait(10):raise AssertionError('reader never reached deterministic barrier')
                ledger.reserve('during','during',{'shared':10},'TEST','offline',2)
            except BaseException as exc:errors.append(exc)
            finally:
                if ledger:ledger.close()
                committed.set()
        thread=threading.Thread(target=writer);thread.start()
        self.assertTrue(ready.wait(10))
        def trace(sql):
            if sql=='SELECT * FROM accounts' and armed[0]:
                armed[0]=False;observed.append('materialized-read')
                between.set()
                if not committed.wait(10):errors.append(AssertionError('writer could not commit during read snapshot'))
        self.reader.db.set_trace_callback(trace)
        try:
            # The writer has committed before the account SELECT executes. A correct read
            # snapshot still sees the old signed log and old materialized tables together.
            self.assertTrue(self.reader.audit(checkpoint))
        finally:
            self.reader.db.set_trace_callback(None);between.set();thread.join(10)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[]);self.assertEqual(observed,['materialized-read'])
        self.assertFalse(self.reader.db.in_transaction)
        self.assertEqual(len(self.reader.export()['events']),2)
        self.assertEqual(self.reader.db.execute('SELECT reserved FROM accounts').fetchone()[0],'3')
        self.assertTrue(self.reader.audit(checkpoint))

    def test_nested_audit_reuses_outer_transaction(self):
        self.reader.reserve('before','before',{'shared':10},'TEST','offline',1)
        trace=[];self.reader.db.set_trace_callback(trace.append)
        try:
            with self.reader.transaction():
                self.assertTrue(self.reader.audit())
                self.assertTrue(self.reader.db.in_transaction)
                self.assertNotIn('COMMIT',trace)
        finally:self.reader.db.set_trace_callback(None)
        self.assertEqual(sum(s.startswith('BEGIN') for s in trace),1)
        self.assertFalse(self.reader.db.in_transaction)

    def test_failed_standalone_audit_releases_own_read_transaction(self):
        self.reader.reserve('before','before',{'shared':10},'TEST','offline',1)
        self.reader.db.execute("UPDATE accounts SET reserved='0'")
        with self.assertRaises(Rejected):self.reader.audit()
        self.assertFalse(self.reader.db.in_transaction)
        self.reader.db.execute("UPDATE accounts SET reserved='1'")
        self.assertTrue(self.reader.audit())

    def test_failed_nested_audit_does_not_end_caller_transaction(self):
        self.reader.reserve('before','before',{'shared':10},'TEST','offline',1)
        self.reader.db.execute('BEGIN IMMEDIATE')
        try:
            self.reader.db.execute("UPDATE accounts SET reserved='0'")
            with self.assertRaises(Rejected):self.reader.audit()
            self.assertTrue(self.reader.db.in_transaction)
        finally:self.reader.db.execute('ROLLBACK')
        self.assertTrue(self.reader.audit())

    def test_admission_checks_checkpoint_inside_reservation_transaction(self):
        f=Fixture();checkpoint=self.reader.export()['checkpoint'];original=self.reader.audit;observed=[]
        def audit(checkpoint=None):
            if checkpoint is not None:observed.append(self.reader.db.in_transaction)
            return original(checkpoint)
        self.reader.audit=audit
        result=admit(f.store(),f.trust,f.request(),0,self.reader,checkpoint)
        self.assertEqual(result.category,'RESERVED_NO_ACTION')
        self.assertEqual(observed,[True])

    def test_bad_checkpoint_rolls_back_reservation_and_nonce(self):
        f=Fixture();checkpoint=self.reader.export()['checkpoint'];checkpoint['head']='sha256:'+'00'*32
        result=admit(f.store(),f.trust,f.request(),0,self.reader,checkpoint)
        self.assertEqual(result.category,'INVALID')
        self.assertEqual(self.reader.db.execute('SELECT count(*) FROM reservations').fetchone()[0],0)
        self.assertEqual(self.reader.db.execute('SELECT count(*) FROM authority_nonces').fetchone()[0],0)
        self.assertFalse(self.reader.db.in_transaction)
