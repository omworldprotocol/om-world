"""Single-deployment SQLite ledger. Local authority API, not a network service. Apache-2.0."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .core import canonical, digest, strict_json, require, signing_digest, PROFILE, SUITE

class Ledger:
    """Call only with limits admitted by the offline verifier. The local DB/key are trusted.

    A caller-held external checkpoint is required for rollback/omitted-tail detection.
    This API cannot prove that an external action occurred or provide distributed exactly-once.
    """
    def __init__(self, path, deployment, signing_key, checkpoint=None):
        self.deployment, self.key = deployment, signing_key
        self.db = sqlite3.connect(str(path), timeout=30, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(k TEXT PRIMARY KEY,v TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,asset TEXT NOT NULL,
          network TEXT NOT NULL,ceiling TEXT NOT NULL,reserved TEXT NOT NULL,spent TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reservations(invocation TEXT PRIMARY KEY,nonce TEXT NOT NULL UNIQUE,
          payload TEXT NOT NULL,state TEXT NOT NULL,consumed TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS authority_nonces(scope TEXT PRIMARY KEY,object_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,payload BLOB NOT NULL,digest TEXT NOT NULL);
        ''')
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        self.public = 'ed25519:' + signing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        with self.transaction():
            for k, v in [('deployment', deployment), ('authority', self.public)]:
                self.db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', (k, v))
                require(self.db.execute('SELECT v FROM metadata WHERE k=?', (k,)).fetchone()[0] == v,
                        'INVALID', 'ledger identity changed')
        self.audit(checkpoint)

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def _append(self, action, payload):
        row = self.db.execute('SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        event = {'format': 'omworld.local-ledger.v1', 'deployment': self.deployment,
                 'authority': self.public, 'sequence': 0 if row is None else row[0] + 1,
                 'previous': None if row is None else row[1], 'action': action, 'payload': payload}
        event['signature'] = self.key.sign(signing_digest(event)).hex()
        raw = canonical(event)
        self.db.execute('INSERT INTO events VALUES (?,?,?)', (event['sequence'], raw, digest(raw)))

    def reserve(self, invocation, nonce_scope, accounts, asset, network, amount, authority_nonces=None, checkpoint=None):
        """accounts: exact {signed-object-id: integer ceiling}; nonce scope includes actor/profile/type.

        Shared Intent/Consent/Acceptance accounts prevent per-Acceptance budget reset.
        Amount is the actual maximum callable spend including any fee charged on this call.
        """
        require(type(amount) is int and amount >= 0 and isinstance(accounts, dict) and accounts, 'INVALID', 'reservation amount/accounts')
        require(all(isinstance(x, str) and x for x in [invocation, nonce_scope, asset, network] + list(accounts)),
                'INVALID', 'nonempty identifiers required')
        require(all(type(v) is int and v >= 0 for v in accounts.values()), 'INVALID', 'integer ceilings')
        authority_nonces = {} if authority_nonces is None else dict(authority_nonces)
        require(all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in authority_nonces.items()),
                'INVALID', 'authority nonce bindings')
        payload = {'authority_nonces': dict(sorted(authority_nonces.items())), 'invocation': invocation, 'nonce': nonce_scope, 'accounts': {k: str(v) for k, v in sorted(accounts.items())},
                   'asset': asset, 'network': network, 'amount': str(amount)}
        with self.transaction():
            self.audit(checkpoint)
            old = self.db.execute('SELECT payload,state FROM reservations WHERE invocation=?', (invocation,)).fetchone()
            if old:
                require(json.loads(old[0]) == payload, 'INVALID', 'invocation reused with changed reservation')
                return old[1]  # Retry returns existing state, never authorizes action a second time.
            require(self.db.execute('SELECT 1 FROM reservations WHERE nonce=?', (nonce_scope,)).fetchone() is None,
                    'UNAUTHORIZED', 'nonce replay')
            for scope, object_id in authority_nonces.items():
                old_binding = self.db.execute('SELECT object_id FROM authority_nonces WHERE scope=?', (scope,)).fetchone()
                require(old_binding is None or old_binding[0] == object_id, 'UNAUTHORIZED', 'authority nonce reused for different object')
                self.db.execute('INSERT OR IGNORE INTO authority_nonces VALUES (?,?)', (scope, object_id))
            for account, ceiling_text in payload['accounts'].items():
                ceiling = int(ceiling_text)
                row = self.db.execute('SELECT asset,network,ceiling,reserved,spent FROM accounts WHERE id=?', (account,)).fetchone()
                if row is None:
                    self.db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?)',
                                    (account, asset, network, str(ceiling), '0', '0'))
                    row = (asset, network, str(ceiling), '0', '0')
                require(row[:3] == (asset, network, str(ceiling)), 'INVALID', 'account currency/ceiling changed')
                require(int(row[3]) + int(row[4]) + amount <= ceiling, 'UNAUTHORIZED', 'cumulative budget exceeded')
                self.db.execute('UPDATE accounts SET reserved=? WHERE id=?', (str(int(row[3]) + amount), account))
            self.db.execute('INSERT INTO reservations VALUES (?,?,?,?,?)',
                            (invocation, nonce_scope, canonical(payload).decode(), 'reserved', '0'))
            self._append('reserve', payload)
        return 'new_reservation'  # Only this response may precede a first external action; no action supplied here.

    def finish(self, invocation, action, amount=0):
        require(action in ('consume', 'release'), 'INVALID', 'ledger transition')
        require(type(amount) is int and amount >= 0 and (action != 'release' or amount == 0), 'INVALID', 'final amount')
        with self.transaction():
            self.audit()
            row = self.db.execute('SELECT payload,state,consumed FROM reservations WHERE invocation=?', (invocation,)).fetchone()
            require(row is not None, 'INVALID', 'unknown reservation')
            payload, state, old = json.loads(row[0]), row[1], int(row[2])
            if state != 'reserved':
                require(state == action and old == amount, 'INVALID', 'second finalization differs')
                return state
            require(amount <= int(payload['amount']), 'UNAUTHORIZED', 'consume above reservation')
            for account in payload['accounts']:
                r, s = self.db.execute('SELECT reserved,spent FROM accounts WHERE id=?', (account,)).fetchone()
                self.db.execute('UPDATE accounts SET reserved=?,spent=? WHERE id=?',
                                (str(int(r) - int(payload['amount'])), str(int(s) + amount), account))
            self.db.execute('UPDATE reservations SET state=?,consumed=? WHERE invocation=?', (action, str(amount), invocation))
            self._append(action, {'invocation': invocation, 'amount': str(amount)})
        return action

    def export(self):
        with self.transaction():
            self.audit()
            events = [strict_json(bytes(x[0])) for x in self.db.execute('SELECT payload FROM events ORDER BY seq')]
            return {'events': events, 'checkpoint': self._checkpoint()}

    def _checkpoint(self):
        row = self.db.execute('SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        result = {'format': 'omworld.local-checkpoint.v1', 'deployment': self.deployment,
                  'authority': self.public, 'sequence': -1 if row is None else row[0],
                  'head': None if row is None else row[1]}
        result['signature'] = self.key.sign(signing_digest(result)).hex()
        return result

    def audit(self, checkpoint=None):
        """Audit a consistent snapshot; reuse but never commit/rollback the caller's transaction.

        A standalone deferred read transaction pins its snapshot on the first SELECT. WAL
        writers can still commit; all following reads retain that same snapshot. Inside
        reserve/finish/export, reuse their existing transaction (no nested BEGIN).
        """
        if self.db.in_transaction:
            return self._audit_snapshot(checkpoint)
        self.db.execute('BEGIN')
        try:
            result = self._audit_snapshot(checkpoint)
            self.db.execute('COMMIT')
            return result
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    def _audit_snapshot(self, checkpoint=None):
        """Caller owns a read/write transaction covering every query below."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public[8:]))
        def signed(value):
            require(value['authority'] == self.public and value['deployment'] == self.deployment,
                    'INVALID', 'log authority/deployment')
            try:
                pub.verify(bytes.fromhex(value['signature']), signing_digest(value))
            except (ValueError, InvalidSignature):
                require(False, 'INVALID', 'log/checkpoint signature')
        accounts, reservations, used, heads, authority_nonces = {}, {}, set(), {}, {}
        previous = None
        for sequence, row in enumerate(self.db.execute('SELECT seq,payload,digest FROM events ORDER BY seq')):
            seq, raw, h = row
            raw = bytes(raw)
            value = strict_json(raw)
            signed(value)
            require(seq == sequence == value['sequence'] and h == digest(raw)
                    and value['previous'] == previous, 'INVALID', 'log continuity')
            previous = h
            heads[seq] = h
            x = value['payload']
            if value['action'] == 'reserve':
                require(x['invocation'] not in reservations and x['nonce'] not in used,
                        'INVALID', 'log replay')
                used.add(x['nonce'])
                for scope, object_id in x['authority_nonces'].items():
                    require(scope not in authority_nonces or authority_nonces[scope] == object_id, 'INVALID', 'log authority nonce')
                    authority_nonces[scope] = object_id
                reservations[x['invocation']] = [x, 'reserved', 0]
                for a, ceiling_text in x['accounts'].items():
                    ceiling = int(ceiling_text)
                    account = accounts.setdefault(a, [x['asset'], x['network'], ceiling, 0, 0])
                    require(account[:3] == [x['asset'], x['network'], ceiling], 'INVALID', 'log account')
                    account[3] += int(x['amount'])
                    require(account[3] + account[4] <= ceiling, 'INVALID', 'log overspend')
            else:
                require(value['action'] in ('consume', 'release') and x['invocation'] in reservations,
                        'INVALID', 'log transition')
                reservation = reservations[x['invocation']]
                require(reservation[1] == 'reserved' and 0 <= int(x['amount']) <= int(reservation[0]['amount']),
                        'INVALID', 'log finalization')
                require(value['action'] != 'release' or int(x['amount']) == 0, 'INVALID', 'log release')
                for a in reservation[0]['accounts']:
                    accounts[a][3] -= int(reservation[0]['amount'])
                    accounts[a][4] += int(x['amount'])
                reservation[1:] = [value['action'], int(x['amount'])]
        actual_a = {a: [asset, net, int(c), int(r), int(s)] for a, asset, net, c, r, s in self.db.execute('SELECT * FROM accounts')}
        actual_r = {}
        for i, nonce, raw, state, c in self.db.execute('SELECT * FROM reservations'):
            payload = json.loads(raw)
            require(nonce == payload['nonce'], 'INVALID', 'materialized nonce differs from log')
            actual_r[i] = [payload, state, int(c)]
        require(dict(self.db.execute('SELECT scope,object_id FROM authority_nonces')) == authority_nonces,
                'INVALID', 'authority nonce state differs from log')
        require(actual_a == accounts and actual_r == reservations, 'INVALID', 'materialized ledger state differs from log')
        if checkpoint is not None:
            signed(checkpoint)
            require(checkpoint['sequence'] >= 0 or checkpoint['head'] is None, 'INVALID', 'checkpoint')
            require(checkpoint['sequence'] == -1 or heads.get(checkpoint['sequence']) == checkpoint['head'],
                    'UNAVAILABLE', 'caller-held checkpoint not present: rollback/omitted tail')
        return True
