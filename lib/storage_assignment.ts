/**
 * Storage assignment: pick the next Pattern blob to push to a heartbeating node.
 *
 * Strategy (v0):
 * - Prefer Patterns with no storage_uri yet (first-time replication)
 * - Skip Patterns already assigned to this node
 * - Cap per-node outstanding assignments at MAX_ASSIGNMENTS_PER_NODE
 * - Cap each blob at MAX_BLOB_BYTES
 *
 * Production (Phase 1.5+) will add: replication factor > 1, capacity-aware
 * placement, and assignment rebalancing on node retirement.
 */

import crypto from "node:crypto";
import { db } from "./db";
import { newId } from "./ids";

const MAX_ASSIGNMENTS_PER_NODE = 10;
const MAX_BLOB_BYTES = 1_000_000; // 1 MB blob ceiling for v0 — Patterns are small

export interface BlobAssignment {
  assignmentId: string;
  patternId: string;
  sha256: string;
  sizeBytes: number;
  blobBase64: string;
}

/**
 * Build the canonical blob for a Pattern: concatenated JSON of
 * { pattern, source_execution } so the node has self-contained verifiable bytes.
 */
async function buildPatternBlob(patternId: string): Promise<{ blob: Buffer; sha256: string } | null> {
  const pattern = await db.pattern.findUnique({ where: { id: patternId } });
  if (!pattern) return null;

  let sourceExecution = null;
  if (pattern.originalIntentId) {
    sourceExecution = await db.execution.findFirst({
      where: { intentId: pattern.originalIntentId, status: "completed" },
      orderBy: { createdAt: "asc" },
    });
  }

  const obj = {
    pattern: {
      id: pattern.id,
      intent_type: pattern.intentType,
      pattern_name: pattern.patternName,
      execution_graph: pattern.executionGraphJson ? JSON.parse(pattern.executionGraphJson) : null,
      capabilities_used: pattern.capabilitiesUsed,
      created_at: pattern.createdAt.toISOString(),
    },
    source_execution: sourceExecution
      ? {
          id: sourceExecution.id,
          output: sourceExecution.outputJson ? JSON.parse(sourceExecution.outputJson) : null,
          trace: sourceExecution.traceJson ? JSON.parse(sourceExecution.traceJson) : null,
        }
      : null,
  };

  const blob = Buffer.from(JSON.stringify(obj), "utf-8");
  if (blob.length > MAX_BLOB_BYTES) return null;
  const sha256 = crypto.createHash("sha256").update(blob).digest("hex");
  return { blob, sha256 };
}

/**
 * Find an outstanding assignment for this node that's still in `assigned` state
 * — used to re-push if the node lost the blob (e.g. disk wipe + re-register).
 */
async function findUnconfirmedAssignment(nodeId: string): Promise<BlobAssignment | null> {
  const row = await db.nodeAssignment.findFirst({
    where: { nodeId, status: "assigned" },
    orderBy: { assignedAt: "asc" },
  });
  if (!row) return null;
  const built = await buildPatternBlob(row.patternId);
  if (!built) return null;
  return {
    assignmentId: row.id,
    patternId: row.patternId,
    sha256: built.sha256,
    sizeBytes: built.blob.length,
    blobBase64: built.blob.toString("base64"),
  };
}

/**
 * Pick the next Pattern to assign to this node:
 * - prefer Patterns with no storageUri yet
 * - then Patterns this node doesn't already hold
 */
export async function pickNextAssignment(opts: {
  nodeId: string;
  status: string; // node's current status — only "active" gets new work
}): Promise<BlobAssignment | null> {
  if (opts.status !== "active") return null;

  // 1) Re-deliver any still-in-flight unconfirmed assignment first.
  const pending = await findUnconfirmedAssignment(opts.nodeId);
  if (pending) return pending;

  // 2) Respect outstanding cap.
  const outstanding = await db.nodeAssignment.count({
    where: { nodeId: opts.nodeId, status: { in: ["assigned", "confirmed"] } },
  });
  if (outstanding >= MAX_ASSIGNMENTS_PER_NODE) return null;

  // 3) Pick Patterns the node doesn't yet hold, preferring unstored ones.
  const existing = await db.nodeAssignment.findMany({
    where: { nodeId: opts.nodeId },
    select: { patternId: true },
  });
  const heldIds = new Set(existing.map((r) => r.patternId));

  const candidates = await db.pattern.findMany({
    where: {
      status: "active",
      id: { notIn: Array.from(heldIds) },
    },
    orderBy: [
      { storageUri: { sort: "asc", nulls: "first" } }, // unstored first
      { reuseCount: "desc" },
      { createdAt: "asc" },
    ],
    take: 5,
  });

  for (const p of candidates) {
    const built = await buildPatternBlob(p.id);
    if (!built) continue;
    const created = await db.nodeAssignment.create({
      data: {
        id: newId("assign"),
        nodeId: opts.nodeId,
        patternId: p.id,
        sha256: built.sha256,
        sizeBytes: built.blob.length,
        status: "assigned",
      },
    });
    return {
      assignmentId: created.id,
      patternId: created.patternId,
      sha256: created.sha256,
      sizeBytes: created.sizeBytes,
      blobBase64: built.blob.toString("base64"),
    };
  }

  return null;
}

/**
 * Mark an assignment as confirmed once the node reports it received and stored
 * the blob. Also updates the Pattern's storage_uri + content_hash for first-time
 * Pattern storage so the Pattern Library reflects that the blob is now replicated.
 */
export async function confirmAssignment(opts: {
  nodeId: string;
  assignmentId: string;
  reportedSha256: string;
}): Promise<{ ok: true; patternId: string } | { ok: false; reason: string }> {
  const assignment = await db.nodeAssignment.findUnique({ where: { id: opts.assignmentId } });
  if (!assignment) return { ok: false, reason: "assignment not found" };
  if (assignment.nodeId !== opts.nodeId) return { ok: false, reason: "node mismatch" };
  if (assignment.sha256 !== opts.reportedSha256) {
    return { ok: false, reason: "sha256 mismatch" };
  }

  await db.nodeAssignment.update({
    where: { id: opts.assignmentId },
    data: { status: "confirmed", confirmedAt: new Date() },
  });

  // First-time storage — mark the Pattern so /patterns shows the storage_uri.
  const pattern = await db.pattern.findUnique({ where: { id: assignment.patternId } });
  if (pattern && !pattern.storageUri) {
    await db.pattern.update({
      where: { id: assignment.patternId },
      data: {
        storageUri: `omw-node://${opts.nodeId}/${opts.reportedSha256}`,
        contentHash: opts.reportedSha256,
      },
    });
  }

  return { ok: true, patternId: assignment.patternId };
}

export async function pickChallengeForNode(opts: {
  nodeId: string;
}): Promise<{ assignmentId: string; sha256: string; sizeBytes: number; rangeStart: number; rangeEnd: number } | null> {
  const confirmed = await db.nodeAssignment.findMany({
    where: { nodeId: opts.nodeId, status: "confirmed" },
  });
  if (confirmed.length === 0) return null;
  const pick = confirmed[Math.floor(Math.random() * confirmed.length)];
  const size = pick.sizeBytes;
  if (size < 1) return null;
  // Random 64-byte range (or smaller if blob is tiny).
  const span = Math.min(64, size);
  const rangeStart = Math.floor(Math.random() * (size - span + 1));
  const rangeEnd = rangeStart + span;
  return {
    assignmentId: pick.id,
    sha256: pick.sha256,
    sizeBytes: size,
    rangeStart,
    rangeEnd,
  };
}

/**
 * Recompute the expected hash for a range of a Pattern's blob.
 * Used by the proof route to verify the node's response.
 */
export async function computeRangeHash(opts: {
  patternId: string;
  rangeStart: number;
  rangeEnd: number;
}): Promise<string | null> {
  const built = await buildPatternBlob(opts.patternId);
  if (!built) return null;
  const slice = built.blob.subarray(opts.rangeStart, opts.rangeEnd);
  return crypto.createHash("sha256").update(slice).digest("hex");
}
