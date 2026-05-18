/**
 * Node identity: ed25519 keypair generation, persistence, signing.
 * Stored at $OMW_NODE_DIR/identity.json (chmod 600). Default dir ~/.omw-node.
 */

import { mkdirSync, existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import nacl from "tweetnacl";

export function defaultNodeDir(): string {
  return process.env.OMW_NODE_DIR || join(homedir(), ".omw-node");
}

export interface Identity {
  publicKeyB64: string;
  secretKeyB64: string;
}

function b64encode(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("base64");
}

function b64decode(str: string): Uint8Array {
  return Uint8Array.from(Buffer.from(str, "base64"));
}

export function loadOrCreateIdentity(): Identity {
  const dir = defaultNodeDir();
  const path = join(dir, "identity.json");
  if (existsSync(path)) {
    const raw = JSON.parse(readFileSync(path, "utf-8"));
    if (!raw.publicKeyB64 || !raw.secretKeyB64) {
      throw new Error(`identity.json at ${path} is malformed`);
    }
    return raw;
  }
  mkdirSync(dir, { recursive: true });
  const kp = nacl.sign.keyPair();
  const id: Identity = {
    publicKeyB64: b64encode(kp.publicKey),
    secretKeyB64: b64encode(kp.secretKey),
  };
  writeFileSync(path, JSON.stringify(id, null, 2));
  try { chmodSync(path, 0o600); } catch { /* best effort */ }
  return id;
}

export function signMessage(id: Identity, message: string): string {
  const sk = b64decode(id.secretKeyB64);
  const sig = nacl.sign.detached(new TextEncoder().encode(message), sk);
  return b64encode(sig);
}

export function publicKey(id: Identity): string {
  return id.publicKeyB64;
}

export { b64decode, b64encode };
