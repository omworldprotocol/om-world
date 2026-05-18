import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { recordHeartbeat, verifyNodeSignature } from "@/lib/nodes";
import { pickNextAssignment, confirmAssignment, pickChallengeForNode } from "@/lib/storage_assignment";

/**
 * POST /api/nodes/heartbeat
 *
 * Periodic poll from the node client. Two things happen:
 * 1) The server records last_seen_at + may issue work (assignment or challenge).
 * 2) The node may include a confirmation for a previously-issued assignment.
 *
 * Signature: ed25519 over `"omw-heartbeat|<node_id>|<nonce>"` (nonce = timestamp ms).
 */

const HeartbeatSchema = z.object({
  node_id: z.string(),
  pubkey: z.string(),
  nonce: z.number().int(),
  signature: z.string(),
  free_gb: z.number().int().nonnegative().optional(),
  // Optional: report a previously-issued assignment's confirmation (sha256 the node stored).
  confirm: z.object({
    assignment_id: z.string(),
    sha256: z.string().length(64),
  }).optional(),
});

const NONCE_SKEW_MS = 5 * 60_000;

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = HeartbeatSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const d = parsed.data;

  // Anti-replay: nonce must be a reasonably-current timestamp.
  if (Math.abs(Date.now() - d.nonce) > NONCE_SKEW_MS) {
    return NextResponse.json({ error: "Nonce out of acceptable window" }, { status: 401 });
  }

  const message = `omw-heartbeat|${d.node_id}|${d.nonce}`;
  if (!verifyNodeSignature({ pubkeyBase64: d.pubkey, message, signatureBase64: d.signature })) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  // Look up the node — must exist and own the pubkey we just verified.
  const node = await db.node.findUnique({ where: { id: d.node_id } });
  if (!node) return NextResponse.json({ error: "Node not registered" }, { status: 404 });
  if (node.pubkey !== d.pubkey) {
    return NextResponse.json({ error: "Pubkey does not match registered node" }, { status: 401 });
  }

  await recordHeartbeat(d.node_id);

  // Step 1: process confirmation if the node included one.
  let confirmed: { pattern_id: string } | { error: string } | null = null;
  if (d.confirm) {
    const r = await confirmAssignment({
      nodeId: d.node_id,
      assignmentId: d.confirm.assignment_id,
      reportedSha256: d.confirm.sha256,
    });
    confirmed = r.ok ? { pattern_id: r.patternId } : { error: r.reason };
  }

  // Step 2: issue work — prefer issuing a challenge over a new assignment so
  // a healthy node accumulates proven GB before being asked to store more.
  // We alternate: ~30% challenge, ~70% new assignment.
  let work: unknown = null;

  const wantChallenge = Math.random() < 0.3;
  if (wantChallenge) {
    const ch = await pickChallengeForNode({ nodeId: d.node_id });
    if (ch) {
      work = {
        kind: "challenge",
        assignment_id: ch.assignmentId,
        sha256: ch.sha256,
        range_start: ch.rangeStart,
        range_end: ch.rangeEnd,
      };
    }
  }

  if (!work) {
    const next = await pickNextAssignment({ nodeId: d.node_id, status: node.status });
    if (next) {
      work = {
        kind: "store",
        assignment_id: next.assignmentId,
        pattern_id: next.patternId,
        expected_sha256: next.sha256,
        size_bytes: next.sizeBytes,
        blob_base64: next.blobBase64,
      };
    }
  }

  return NextResponse.json({
    ok: true,
    node_status: node.status,
    strikes: node.strikes,
    confirmed,
    work,
  });
}
