"""Independently located, durable local high-water store. Apache-2.0.

The directory must be protected and managed outside the ledger rollback domain.
Local code cannot prove that an operator did not restore both stores together.
"""
import json
import os
import tempfile
import stat
from contextlib import contextmanager
from pathlib import Path
import fcntl
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from .core import require, canonical, strict_json, signing_digest, identity_bytes

class CheckpointStore:
    def __init__(self, directory, ledger_path, deployment, authority, storage_id):
        requested = Path(directory)
        require(not requested.is_symlink(), 'INVALID', 'checkpoint directory symlink')
        self.directory = requested.resolve()
        self.ledger_path = Path(ledger_path).resolve()
        require(not self.directory.is_relative_to(self.ledger_path.parent), 'INVALID', 'checkpoint store inside ledger rollback directory')
        require(not self.ledger_path.parent.is_relative_to(self.directory), 'INVALID', 'ledger directory inside checkpoint rollback directory')
        require(all(isinstance(v, str) and v for v in (deployment, authority, storage_id)), 'INVALID', 'store binding')
        self.deployment, self.authority, self.storage_id = deployment, authority, storage_id
        identity_bytes(authority)
        self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.path = self.directory / 'high-water.json'
        self.lock_path = self.directory / 'high-water.lock'
        require(not self.path.is_symlink() and not self.lock_path.is_symlink(), 'INVALID', 'checkpoint file symlink')

    @contextmanager
    def locked(self):
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(self.lock_path, flags, 0o600)
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode), 'INVALID', 'lock not regular file')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _checkpoint(self, value):
        require(isinstance(value, dict) and set(value) == {'format','deployment','authority','sequence','head','signature'},
                'INVALID', 'checkpoint shape')
        require(value['format'] == 'omworld.local-checkpoint.v1'
                and value['deployment'] == self.deployment and value['authority'] == self.authority,
                'INVALID', 'checkpoint authority/deployment')
        require(type(value['sequence']) is int and value['sequence'] >= -1, 'INVALID', 'checkpoint sequence')
        require((value['sequence'] == -1 and value['head'] is None)
                or (value['sequence'] >= 0 and isinstance(value['head'], str) and value['head'].startswith('sha256:') and len(value['head']) == 71),
                'INVALID', 'checkpoint head')
        try:
            signature = bytes.fromhex(value['signature'])
            require(len(signature) == 64 and signature.hex() == value['signature'], 'INVALID', 'checkpoint signature encoding')
            Ed25519PublicKey.from_public_bytes(identity_bytes(self.authority)).verify(signature, signing_digest(value))
        except (ValueError, TypeError, InvalidSignature):
            require(False, 'INVALID', 'checkpoint signature')

    def _load(self):
        require(self.path.exists() and not self.path.is_symlink(), 'UNAVAILABLE', 'independent checkpoint missing; no automatic rebootstrap')
        value = strict_json(self.path.read_bytes())
        require(isinstance(value, dict) and set(value) == {'format','storage_id','generation','checkpoint','sources'},
                'INVALID', 'anchor envelope shape')
        require(value['format'] == 'omworld.local-anchor.v1' and value['storage_id'] == self.storage_id
                and type(value['generation']) is int and value['generation'] >= 0
                and isinstance(value['sources'], dict), 'INVALID', 'anchor storage binding')
        self._checkpoint(value['checkpoint'])
        return value

    def _write(self, value):
        require(not self.path.is_symlink(), 'INVALID', 'checkpoint target symlink')
        fd, name = tempfile.mkstemp(prefix='.high-water-', dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
        finally:
            if os.path.exists(name):os.unlink(name)

    def _ledger_binding(self, ledger):
        require(Path(ledger.db.execute('PRAGMA database_list').fetchone()[2]).resolve() == self.ledger_path,
                'INVALID', 'wrong ledger path')
        require(ledger.deployment == self.deployment and ledger.public == self.authority,
                'INVALID', 'wrong ledger identity')

    def initialize_empty(self, ledger):
        """Explicit ceremony only; cannot hide missing anchors on a used ledger."""
        with self.locked():
            require(not self.path.exists(), 'INVALID', 'checkpoint already initialized')
            self._ledger_binding(ledger)
            with ledger.transaction():
                ledger.audit();checkpoint = ledger._checkpoint()
                require(checkpoint['sequence'] == -1, 'UNAVAILABLE', 'cannot bootstrap nonempty ledger')
            value = {'format':'omworld.local-anchor.v1','storage_id':self.storage_id,
                     'generation':0,'checkpoint':checkpoint,'sources':{}}
            self._write(value)
            return value

    def read(self):
        with self.locked():return self._load()

    def _advance(self, ledger, value, sources=None):
        self._ledger_binding(ledger)
        with ledger.transaction():
            ledger.audit(value['checkpoint'])
            checkpoint = ledger._checkpoint()
        require(checkpoint['sequence'] >= value['checkpoint']['sequence'], 'INVALID', 'checkpoint regression')
        if checkpoint['sequence'] == value['checkpoint']['sequence']:
            require(checkpoint['head'] == value['checkpoint']['head'], 'INVALID', 'same-height fork')
        new = {**value, 'generation':value['generation'] + 1, 'checkpoint':checkpoint,
               'sources':value['sources'] if sources is None else sources}
        self._write(new)
        return new

    def advance(self, ledger):
        with self.locked():return self._advance(ledger, self._load())

    def recover(self, ledger):
        """Validate/anchor committed state only; never re-execute or release a reservation."""
        with self.locked():
            value = self._advance(ledger, self._load())
            pending = [r[0] for r in ledger.db.execute("SELECT invocation FROM reservations WHERE state='reserved'")]
            return {'state':'RECOVERED_NO_ACTION','checkpoint':value['checkpoint'],
                    'pending_reservations':pending,'sources_preserved':True}
