/**
 * Local content-addressed blob store at $OMW_NODE_DIR/blobs/<sha256>.
 *
 * Pure filesystem. No metadata DB on the node side in v0 — assignment metadata
 * lives only on the server, the node is a dumb byte holder addressed by sha256.
 */

import { mkdirSync, existsSync, readFileSync, writeFileSync, statSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
import { defaultNodeDir } from "./identity";

function blobDir(): string {
  const dir = join(defaultNodeDir(), "blobs");
  mkdirSync(dir, { recursive: true });
  return dir;
}

export function sha256(bytes: Buffer): string {
  return createHash("sha256").update(bytes).digest("hex");
}

/** Store bytes idempotently; returns the sha256. Verifies expected hash if supplied. */
export function putBlob(bytes: Buffer, expectedSha256?: string): { sha256: string } {
  const hash = sha256(bytes);
  if (expectedSha256 && hash !== expectedSha256) {
    throw new Error(`blob hash mismatch: got ${hash}, expected ${expectedSha256}`);
  }
  const path = join(blobDir(), hash);
  if (!existsSync(path)) {
    writeFileSync(path, bytes);
  }
  return { sha256: hash };
}

/** Read a blob from disk, or null if not present. */
export function getBlob(hash: string): Buffer | null {
  const path = join(blobDir(), hash);
  if (!existsSync(path)) return null;
  return readFileSync(path);
}

/** Hash a byte range of a stored blob; used for challenge responses. */
export function hashBlobRange(hash: string, rangeStart: number, rangeEnd: number): string | null {
  const blob = getBlob(hash);
  if (!blob) return null;
  if (rangeStart < 0 || rangeEnd > blob.length || rangeStart >= rangeEnd) return null;
  const slice = blob.subarray(rangeStart, rangeEnd);
  return createHash("sha256").update(slice).digest("hex");
}

/** Aggregate disk usage of stored blobs. */
export function totalStoredBytes(): number {
  const dir = blobDir();
  let total = 0;
  for (const name of readdirSync(dir)) {
    try {
      total += statSync(join(dir, name)).size;
    } catch { /* skip transient files */ }
  }
  return total;
}
