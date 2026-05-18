/**
 * Node lifecycle: registration, heartbeat tracking, strike accounting.
 * Phase 1 of MVP Wave 2 plan — storage-only nodes.
 *
 * Identity model: each node generates an ed25519 keypair locally on first run
 * and POSTs its pubkey here. The `Node.id` is derived as the first 16 hex chars
 * of sha256(pubkey) so the ID is short-but-collision-resistant and recoverable
 * from the pubkey alone.
 *
 * No Sybil resistance in v0. Acceptable while the founder is the only operator;
 * MUST be revisited before opening node registration publicly (see plan §Phase 1 risks).
 */

import crypto from "node:crypto";
import nacl from "tweetnacl";
import { db } from "./db";

const STRIKE_THRESHOLD = 3;

export function nodeIdFromPubkey(pubkeyBase64: string): string {
  const buf = Buffer.from(pubkeyBase64, "base64");
  return crypto.createHash("sha256").update(buf).digest("hex").slice(0, 16);
}

/**
 * Verify a detached ed25519 signature over a UTF-8 message.
 * Returns true if valid.
 */
export function verifyNodeSignature(opts: {
  pubkeyBase64: string;
  message: string;
  signatureBase64: string;
}): boolean {
  try {
    const pubkey = Uint8Array.from(Buffer.from(opts.pubkeyBase64, "base64"));
    const sig = Uint8Array.from(Buffer.from(opts.signatureBase64, "base64"));
    const msg = new TextEncoder().encode(opts.message);
    if (pubkey.length !== 32 || sig.length !== 64) return false;
    return nacl.sign.detached.verify(msg, sig, pubkey);
  } catch {
    return false;
  }
}

/**
 * Register a new node or refresh its capacity claim.
 * The first registration also opens a CreditAccount(ownerType="node").
 */
export async function registerNode(opts: {
  pubkeyBase64: string;
  claimedGb: number;
  ownerContact?: string | null;
}) {
  const id = nodeIdFromPubkey(opts.pubkeyBase64);
  const now = new Date();

  const node = await db.node.upsert({
    where: { id },
    create: {
      id,
      pubkey: opts.pubkeyBase64,
      ownerContact: opts.ownerContact ?? null,
      claimedGb: Math.max(0, Math.floor(opts.claimedGb)),
      provenGb: 0,
      status: "active",
      strikes: 0,
      lastSeenAt: now,
    },
    update: {
      claimedGb: Math.max(0, Math.floor(opts.claimedGb)),
      lastSeenAt: now,
    },
  });

  // Ensure a node-owned CreditAccount exists (idempotent via ensureAccount).
  const { ensureAccount } = await import("./credits");
  await ensureAccount(id, "node");

  return node;
}

/** Update last_seen_at + return current node row (or null if not found). */
export async function recordHeartbeat(nodeId: string) {
  try {
    return await db.node.update({
      where: { id: nodeId },
      data: { lastSeenAt: new Date() },
    });
  } catch {
    return null;
  }
}

/**
 * Record a successful challenge response; resets the per-assignment failure counter
 * and bumps the node's proven_gb upward (averaged across assignments).
 */
export async function recordChallengeSuccess(opts: {
  nodeId: string;
  assignmentId: string;
}) {
  await db.nodeAssignment.update({
    where: { id: opts.assignmentId },
    data: { lastChallengeAt: new Date(), challengeFailures: 0 },
  });
  // Recompute proven_gb as the sum of confirmed assignment sizes for this node.
  const sum = await db.nodeAssignment.aggregate({
    where: { nodeId: opts.nodeId, status: "confirmed" },
    _sum: { sizeBytes: true },
  });
  const provenGb = (sum._sum.sizeBytes ?? 0) / (1024 ** 3);
  await db.node.update({ where: { id: opts.nodeId }, data: { provenGb } });
}

/**
 * Record a failed challenge. Adds a strike to the node; if the node hits
 * STRIKE_THRESHOLD it moves to status="striked" and stops earning.
 */
export async function recordChallengeFailure(opts: {
  nodeId: string;
  assignmentId: string;
}) {
  const node = await db.node.update({
    where: { id: opts.nodeId },
    data: { strikes: { increment: 1 } },
  });
  await db.nodeAssignment.update({
    where: { id: opts.assignmentId },
    data: { challengeFailures: { increment: 1 } },
  });
  if (node.strikes >= STRIKE_THRESHOLD && node.status === "active") {
    await db.node.update({
      where: { id: opts.nodeId },
      data: { status: "striked" },
    });
  }
}
