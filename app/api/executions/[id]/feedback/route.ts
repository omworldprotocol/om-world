import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";

/**
 * PATCH /api/executions/[id]/feedback
 *
 * Phase 3.5 (red-team #10). The intent author confirms whether the produced
 * output was actually useful. Drives Pattern.successfulReuseCount when this
 * execution was a reuse of an existing pattern; gives downstream metrics a
 * "did it work, or did the LLM just produce something?" signal.
 *
 * Body: { accepted: boolean, note?: string }
 *
 * Auth: v0 trusts intent.contact (founder is sole user). When user #2 lands
 * (per punt registry), this needs a per-intent token.
 */

const FeedbackSchema = z.object({
  accepted: z.boolean(),
  note: z.string().max(500).optional(),
});

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const body = await req.json().catch(() => null);
  const parsed = FeedbackSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }

  const execution = await db.execution.findUnique({ where: { id: params.id } });
  if (!execution) return NextResponse.json({ error: "Execution not found" }, { status: 404 });
  if (execution.userAccepted !== null) {
    return NextResponse.json({
      error: "Feedback already recorded",
      current: { accepted: execution.userAccepted, at: execution.feedbackAt },
    }, { status: 409 });
  }

  await db.execution.update({
    where: { id: params.id },
    data: {
      userAccepted: parsed.data.accepted,
      feedbackAt: new Date(),
      feedbackNote: parsed.data.note ?? null,
    },
  });

  // If positive feedback and this execution was a Pattern reuse, bump the
  // successful_reuse_count even if the friction-ratio gate didn't fire (the
  // user is the ultimate signal of "did it actually help me").
  if (parsed.data.accepted) {
    const trace = execution.traceJson ? safeParse(execution.traceJson) : null;
    const reusedPatternId = trace?.reused_pattern_id as string | undefined;
    if (reusedPatternId) {
      try {
        await db.pattern.update({
          where: { id: reusedPatternId },
          data: { successfulReuseCount: { increment: 1 } },
        });
      } catch (e) { console.error("bump successfulReuseCount failed:", e); }
    }
  }

  return NextResponse.json({ ok: true, accepted: parsed.data.accepted });
}

function safeParse(s: string): Record<string, unknown> | null {
  try {
    const v = JSON.parse(s);
    return typeof v === "object" && v !== null ? (v as Record<string, unknown>) : null;
  } catch { return null; }
}
