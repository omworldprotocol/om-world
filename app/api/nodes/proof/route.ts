import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { verifyNodeSignature, recordChallengeSuccess, recordChallengeFailure } from "@/lib/nodes";
import { computeRangeHash } from "@/lib/storage_assignment";
import { rewardNodeStorage } from "@/lib/credits";

/**
 * POST /api/nodes/proof
 *
 * The node responds to a challenge issued in a prior heartbeat. The challenge
 * named an assignment_id + byte range. The node computes sha256 of those bytes
 * from its local blob copy and signs the result.
 *
 * Server independently recomputes the same range hash from the original Pattern.
 * Match → strike-counter reset + OMC reward; mismatch → strike + (eventually) demotion.
 */

const ProofSchema = z.object({
  node_id: z.string(),
  pubkey: z.string(),
  nonce: z.number().int(),
  signature: z.string(),
  assignment_id: z.string(),
  range_start: z.number().int().nonnegative(),
  range_end: z.number().int().nonnegative(),
  range_sha256: z.string().length(64),
});

const NONCE_SKEW_MS = 5 * 60_000;

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = ProofSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const d = parsed.data;

  if (Math.abs(Date.now() - d.nonce) > NONCE_SKEW_MS) {
    return NextResponse.json({ error: "Nonce out of acceptable window" }, { status: 401 });
  }

  const message = `omw-proof|${d.node_id}|${d.assignment_id}|${d.range_start}|${d.range_end}|${d.range_sha256}|${d.nonce}`;
  if (!verifyNodeSignature({ pubkeyBase64: d.pubkey, message, signatureBase64: d.signature })) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  const assignment = await db.nodeAssignment.findUnique({ where: { id: d.assignment_id } });
  if (!assignment) return NextResponse.json({ error: "assignment not found" }, { status: 404 });
  if (assignment.nodeId !== d.node_id) return NextResponse.json({ error: "node mismatch" }, { status: 403 });
  if (assignment.status !== "confirmed") {
    return NextResponse.json({ error: "assignment not yet confirmed" }, { status: 409 });
  }

  const expected = await computeRangeHash({
    patternId: assignment.patternId,
    rangeStart: d.range_start,
    rangeEnd: d.range_end,
  });
  if (!expected) {
    return NextResponse.json({ error: "could not recompute expected hash" }, { status: 500 });
  }

  const matched = expected === d.range_sha256;

  if (!matched) {
    await recordChallengeFailure({ nodeId: d.node_id, assignmentId: d.assignment_id });
    const node = await db.node.findUnique({ where: { id: d.node_id } });
    return NextResponse.json({
      ok: false,
      matched: false,
      strikes: node?.strikes ?? null,
      status: node?.status ?? null,
    }, { status: 200 });
  }

  await recordChallengeSuccess({ nodeId: d.node_id, assignmentId: d.assignment_id });

  // Reward for time-since-last-success * bytes (default 1 OMC/GB/day, prorated hourly).
  // Compute gb-hours since last successful proof; cap at 24h to bound retroactive backfill.
  const prevLast = assignment.lastChallengeAt;
  const nowMs = Date.now();
  const elapsedH = prevLast
    ? Math.min(24, (nowMs - prevLast.getTime()) / 3_600_000)
    : 0; // first successful proof — no retroactive credit, only forward
  const gbHours = (assignment.sizeBytes / 1024 / 1024 / 1024) * elapsedH;
  let event = null;
  if (gbHours > 0) {
    event = await rewardNodeStorage({
      nodeId: d.node_id,
      patternId: assignment.patternId,
      gbHours,
    });
  }

  const node = await db.node.findUnique({ where: { id: d.node_id } });
  return NextResponse.json({
    ok: true,
    matched: true,
    gb_hours_credited: gbHours,
    credit_event_id: event?.id ?? null,
    proven_gb: node?.provenGb ?? 0,
  });
}
