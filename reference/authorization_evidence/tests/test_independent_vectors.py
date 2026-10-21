"""Published vectors and independent engines, not self-generated expected outputs.

RFC8032 §7.1 (test 1) and RFC8785 Appendix B. Vector facts retain their IETF source.
"""
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.exceptions import InvalidSignature
from ..core import canonical, signing_digest, object_id
from .fixtures import Fixture

NUMBERS=[
('0000000000000000','0'),('8000000000000000','0'),('0000000000000001','5e-324'),
('8000000000000001','-5e-324'),('7fefffffffffffff','1.7976931348623157e+308'),
('ffefffffffffffff','-1.7976931348623157e+308'),('4340000000000000','9007199254740992'),
('c340000000000000','-9007199254740992'),('4430000000000000','295147905179352830000'),
('44b52d02c7e14af5','9.999999999999997e+22'),('44b52d02c7e14af6','1e+23'),
('44b52d02c7e14af7','1.0000000000000001e+23'),('444b1ae4d6e2ef4e','999999999999999700000'),
('444b1ae4d6e2ef4f','999999999999999900000'),('444b1ae4d6e2ef50','1e+21'),
('3eb0c6f7a0b5ed8c','9.999999999999997e-7'),('3eb0c6f7a0b5ed8d','0.000001'),
('41b3de4355555553','333333333.3333332'),('41b3de4355555554','333333333.33333325'),
('41b3de4355555555','333333333.3333333'),('41b3de4355555556','333333333.3333334'),
('41b3de4355555557','333333333.33333343'),('becbf647612f3696','-0.0000033333333333333333'),
('43143ff3c1cb0959','1424953923781206.2')]

class IndependentVectors(unittest.TestCase):
    def test_rfc8032_published_empty_message(self):
        pub=bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
        signature=bytes.fromhex('e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155'
                                '5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
        Ed25519PublicKey.from_public_bytes(pub).verify(signature,b'')
        with self.assertRaises(InvalidSignature):Ed25519PublicKey.from_public_bytes(pub).verify(signature,b'x')
    def test_rfc8785_published_number_vectors(self):
        for bits,expected in NUMBERS:
            with self.subTest(bits=bits):self.assertEqual(canonical(struct.unpack('>d',bytes.fromhex(bits))[0]).decode(),expected)
    def test_node_independent_canonical_bytes_and_object_id(self):
        self.assertIsNotNone(shutil.which('node'),'independent engine required, not silently skipped')
        f=Fixture(context=True,calls=2)
        samples=[f.intent,f.acceptance,f.proof,{'\u20ac':1,'\r':2,'\ufb33':3,'1':4,'😀':5,'\u0080':6,'ö':7}]
        script=r'''const fs=require('fs'),crypto=require('crypto');
const c=x=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(c).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+c(x[k])).join(',')+'}';
const xs=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(xs.map(x=>({jcs:c(x),id:'sha256:'+crypto.createHash('sha256').update(c(Object.fromEntries(Object.entries(x).filter(([k])=>k!=='id'&&k!=='signature')))).digest('hex')}))));'''
        r=subprocess.run(['node','-e',script],input=json.dumps(samples,ensure_ascii=False),capture_output=True,text=True,check=True)
        for value,result in zip(samples,json.loads(r.stdout)):
            self.assertEqual(canonical(value).decode(),result['jcs']);self.assertEqual(object_id(value),result['id'])
    def test_openssl_independent_profile_signature(self):
        self.assertIsNotNone(shutil.which('openssl'),'independent crypto CLI required, not skipped')
        f=Fixture();value=f.acceptance
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            folder.joinpath('pub.pem').write_bytes(f.keys[1].public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
            folder.joinpath('digest').write_bytes(signing_digest(value))
            folder.joinpath('sig').write_bytes(bytes.fromhex(value['signature']['value']))
            args=['openssl','pkeyutl','-verify','-pubin','-inkey',str(folder/'pub.pem'),'-rawin','-in',str(folder/'digest'),'-sigfile',str(folder/'sig')]
            r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
            folder.joinpath('digest').write_bytes(bytes(32));r=subprocess.run(args,capture_output=True);self.assertNotEqual(r.returncode,0)
