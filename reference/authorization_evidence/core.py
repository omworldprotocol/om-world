"""Strict offline bytes, canonicalization and signature primitives. Apache-2.0."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

PROFILE = 'omworld.authorization-evidence.v1-draft'
SUITE = 'Ed25519-RFC8032-pure-over-sha256-digest'
SCHEMA_DIGEST = 'sha256:8ef5fce458644199c1b40fbea650ccb7a94991cf7f847170e70cb32148e625c0'

class Rejected(Exception):
    def __init__(self, category, detail):
        self.category, self.detail = category, detail
        super().__init__(detail)

def fail(category, detail):
    raise Rejected(category, detail)

def require(condition, category, detail):
    if not condition:
        fail(category, detail)

def strict_json(raw):
    def pairs(xs):
        result = {}
        for key, value in xs:
            require(key not in result, 'INVALID', 'duplicate JSON member')
            result[key] = value
        return result
    def constant(_):
        fail('INVALID', 'non-I-JSON numeric constant')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=constant)
        canonical(value)  # Also rejects unsafe integers, lone surrogates and nonfinite numbers.
        return value
    except Rejected:
        raise
    except (ValueError, UnicodeError, TypeError) as exc:
        fail('INVALID', 'JSON/canonical form: ' + str(exc))

def canonical(value):
    try:
        return rfc8785.dumps(value)
    except (ValueError, TypeError, UnicodeError) as exc:
        fail('INVALID', 'JCS: ' + str(exc))

def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()

def object_id(value):
    return digest(canonical({k: v for k, v in value.items() if k not in ('id', 'signature')}))

def signing_digest(value):
    return hashlib.sha256(canonical({k: v for k, v in value.items() if k != 'signature'})).digest()

def instant(value):
    try:
        require(isinstance(value, str) and value.endswith('Z'), 'INVALID', 'UTC Z time required')
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        fail('INVALID', 'invalid timestamp')

def check_time(start, end, at):
    require(instant(start) < instant(end), 'INVALID', 'empty temporal interval')
    require(instant(start) <= instant(at) < instant(end), 'UNAUTHORIZED', 'outside validity interval')

def identity_bytes(actor):
    try:
        require(isinstance(actor, str) and actor.startswith('ed25519:') and len(actor) == 72,
                'UNSUPPORTED', 'only exact ed25519 identities supported')
        raw = bytes.fromhex(actor[8:])
        require(actor[8:] == raw.hex() and len(raw) == 32, 'INVALID', 'key encoding')
        return raw
    except ValueError:
        fail('INVALID', 'key encoding')

def verify_signature(value, actor, store):
    sig = value.get('signature', {})
    require(sig.get('scheme') == SUITE, 'UNSUPPORTED', 'signature suite')
    raw = store.bytes(sig.get('key_ref', {}))
    require(raw == identity_bytes(actor), 'INVALID', 'signer actor/key mismatch')
    require(sig['key_ref'].get('media_type') == 'application/octet-stream', 'INVALID', 'key media type')
    try:
        encoded = bytes.fromhex(sig['value'])
        require(len(encoded) == 64 and encoded.hex() == sig['value'], 'INVALID', 'signature encoding')
        Ed25519PublicKey.from_public_bytes(raw).verify(encoded, signing_digest(value))
    except (InvalidSignature, ValueError, KeyError):
        fail('INVALID', 'Ed25519 signature')

class Store:
    """Explicit bytes only. Never resolves URLs, executes data or performs network I/O."""
    def __init__(self, artifacts, schema):
        self.artifacts = dict(artifacts)
        self.schema = schema
        from jsonschema import Draft202012Validator, FormatChecker
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def bytes(self, ref):
        require(isinstance(ref, dict) and isinstance(ref.get('digest'), str), 'INVALID', 'artifact reference')
        raw = self.artifacts.get(ref['digest'])
        require(raw is not None, 'UNAVAILABLE', 'missing artifact ' + ref['digest'])
        require(isinstance(raw, bytes) and digest(raw) == ref['digest'], 'INVALID', 'artifact digest mismatch')
        return raw

    def artifact(self, ref, kind=None):
        raw = self.bytes(ref)
        require(ref.get('media_type') == 'application/json', 'INVALID', 'JSON media type')
        value = strict_json(raw)
        require(raw == canonical(value), 'INVALID', 'dependency JSON bytes are not JCS')
        if kind:
            self.validate_object(value, kind)
        return value

    def validate_object(self, value, kind=None):
        require(isinstance(value, dict), 'INVALID', 'object required')
        require(value.get('profile') == PROFILE, 'UNSUPPORTED', 'profile')
        if kind:
            require(value.get('object_type') == kind, 'INVALID', 'object type mismatch')
        errors = sorted(self.validator.iter_errors(value), key=lambda e: str(e.path))
        require(not errors, 'INVALID', 'closed schema: ' + (errors[0].message if errors else ''))
        require(object_id(value) == value['id'], 'INVALID', 'object id mismatch')
        return value

    def resolve(self, ref, kind=None):
        require(isinstance(ref, dict) and ref.get('profile') == PROFILE,
                'UNSUPPORTED', 'object ref profile')
        require(set(ref) == {'profile', 'object_type', 'id'}, 'INVALID', 'object ref shape')
        kind = kind or ref['object_type']
        # Object IDs address payloads, not full signed bytes. Find exact exported candidate(s).
        candidates = []
        for raw in self.artifacts.values():
            try:
                value = strict_json(raw)
            except Rejected:
                continue
            if isinstance(value, dict) and value.get('id') == ref['id']:
                candidates.append((raw, value))
        require(bool(candidates), 'UNAVAILABLE', 'object bytes not exported ' + ref['id'])
        unique = {raw for raw, _ in candidates}
        require(len(unique) == 1, 'INVALID', 'ambiguous signed object bytes for one id')
        raw, value = candidates[0]
        require(raw == canonical(value), 'INVALID', 'object bytes are not JCS')
        require(value.get('object_type') == ref['object_type'], 'INVALID', 'ref type')
        return self.validate_object(value, kind)

    @classmethod
    def directory(cls, folder, schema, max_bytes=64 * 1024 * 1024):
        folder = Path(folder).resolve()
        index = strict_json((folder / 'export.json').read_bytes())
        require(set(index) == {'bundle_ref', 'artifacts'}, 'INVALID', 'export index shape')
        artifacts, total = {}, 0
        for expected, name in index['artifacts'].items():
            require(isinstance(name, str), 'INVALID', 'artifact filename')
            path = (folder / name).resolve()
            require(path.is_relative_to(folder) and path.is_file(), 'INVALID', 'artifact path escape')
            total += path.stat().st_size
            require(total <= max_bytes, 'UNAVAILABLE', 'export byte limit')
            raw = path.read_bytes()
            require(digest(raw) == expected, 'INVALID', 'export index digest')
            artifacts[expected] = raw
        return cls(artifacts, schema), index['bundle_ref']
