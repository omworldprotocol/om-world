import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { verifyNodeSignature } from "@/lib/nodes";
import { completeWork } from "@/lib/work";

/**
 * PUT /api/nodes/work
 *
 * A node submits the result of a compute job it previously claimed via a
 * heartbeat work assignment. Signed nonce within 5min window, signature
 * authenticates the result-to-work binding.
 *
 * Idempotent: if the work_assignment is already in "completed", returns 200
 * with the prior pattern_event (re-derived).
 */

const SubmitSchema = z.object({
  node_id: z.string(),
  pubkey: z.string(),
  nonce: z.number().int(),
  signature: z.string(),
  work_assignment_id: z.string(),
  output: z.unknown(),
  output_text: z.string().max(4000),
  execution_mode: z.enum(["fresh", "adapted", "placeholder"]),
  elapsed_sec: z.number().nonnegative(),
});

const NONCE_SKEW_MS = 5 * 60_000;

export async function PUT(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = SubmitSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const d = parsed.data;

  if (Math.abs(Date.now() - d.nonce) > NONCE_SKEW_MS) {
    return NextResponse.json({ error: "Nonce out of acceptable window" }, { status: 401 });
  }

  const message = `omw-work-submit|${d.node_id}|${d.work_assignment_id}|${d.execution_mode}|${d.nonce}`;
  if (!verifyNodeSignature({ pubkeyBase64: d.pubkey, message, signatureBase64: d.signature })) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  const node = await db.node.findUnique({ where: { id: d.node_id } });
  if (!node) return NextResponse.json({ error: "Node not registered" }, { status: 404 });
  if (node.pubkey !== d.pubkey) {
    return NextResponse.json({ error: "Pubkey does not match registered node" }, { status: 401 });
  }

  const work = await db.workAssignment.findUnique({ where: { id: d.work_assignment_id } });
  if (!work) return NextResponse.json({ error: "Work assignment not found" }, { status: 404 });
  if (work.nodeId !== d.node_id) {
    return NextResponse.json({ error: "Work not claimed by this node" }, { status: 403 });
  }
  if (work.status === "completed") {
    return NextResponse.json({
      ok: true,
      already_completed: true,
      execution_id: work.executionId,
    });
  }

  try {
    const { patternEvent } = await completeWork({
      workAssignmentId: d.work_assignment_id,
      nodeId: d.node_id,
      output: d.output,
      outputText: d.output_text,
      executionMode: d.execution_mode,
      elapsedSec: d.elapsed_sec,
    });
    return NextResponse.json({
      ok: true,
      execution_id: work.executionId,
      pattern_event: patternEvent,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: "Completion failed", message }, { status: 500 });
  }
}
