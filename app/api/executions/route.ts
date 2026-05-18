import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { executionId } from "@/lib/ids";
import type { ClassifiedIntent, MatchedPath } from "@/lib/llm";
import { rewardCapabilityProvider, rewardPatternCreation, rewardPatternReuse } from "@/lib/credits";
import { createPatternFromExecution, findReusablePattern, incrementPatternReuse } from "@/lib/patterns";
import { runCapability } from "@/lib/capabilities";
import { enqueueWork, runFallbackSweep, shouldEnqueue } from "@/lib/work";

const ExecutionRequest = z.object({
  intent_id: z.string(),
  path_id: z.string(),
  capability_ids: z.array(z.string()).min(1),
});

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

export async function POST(req: Request) {
  // Opportunistic fallback sweep — flushes any queued work that's gone stale.
  void runFallbackSweep().catch((e) => console.error("fallback sweep:", e));

  const body = await req.json().catch(() => null);
  const parsed = ExecutionRequest.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const { intent_id, path_id, capability_ids } = parsed.data;

  const intent = await db.intent.findUnique({ where: { id: intent_id } });
  if (!intent) return NextResponse.json({ error: "Intent not found" }, { status: 404 });

  const path = await db.realizationPath.findUnique({ where: { id: path_id } });
  if (!path) return NextResponse.json({ error: "Path not found" }, { status: 404 });

  const capabilities = await db.capability.findMany({ where: { id: { in: capability_ids } } });
  if (capabilities.length === 0) {
    return NextResponse.json({ error: "No matching capabilities" }, { status: 404 });
  }

  let classified: ClassifiedIntent | null = null;
  if (intent.constraintsJson) {
    try { classified = JSON.parse(intent.constraintsJson) as ClassifiedIntent; } catch { /* ignore */ }
  }

  const reusable = classified ? await findReusablePattern(classified.intent_type) : null;

  const matchedPath: MatchedPath = {
    path_summary: path.pathSummary ?? "",
    recommended_capabilities: csvList(path.recommendedCapabilities),
    estimated_cost: path.estimatedCost ?? "",
    estimated_time: path.estimatedTime ?? "",
    proof_condition: path.proofCondition ?? "",
    settlement_template: path.settlementTemplate ?? "fixed_payment",
    why_this_path: "",
  };

  // ───────────────────────────────────────────────────────────────────
  // Path A: capability is runsOnNode → enqueue + return queued
  // ───────────────────────────────────────────────────────────────────
  if (shouldEnqueue(intent.intentType)) {
    const { executionId: execId, workAssignmentId } = await enqueueWork({
      intent,
      classified,
      path,
      matchedPath,
      capabilities,
      reusable,
      capabilityIds: capability_ids,
    });
    return NextResponse.json({
      execution_id: execId,
      work_assignment_id: workAssignmentId,
      status: "queued",
      output_text: "Queued for a compute node; will fall back to inline server execution if no node claims within OMW_LOCAL_FALLBACK_AFTER_SEC.",
    }, { status: 202 });
  }

  // ───────────────────────────────────────────────────────────────────
  // Path B: capability is NOT runsOnNode (e.g. placeholder) → run inline now
  // ───────────────────────────────────────────────────────────────────
  const startedAt = Date.now();
  let executorResult;
  try {
    executorResult = await runCapability({
      intent,
      classified,
      path,
      matchedPath,
      capabilities,
      reusable,
      nodeId: process.env.OM_NODE_ID || "local-dev",
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: "Execution failed", message }, { status: 502 });
  }

  const { output, outputText, executionMode } = executorResult;
  const elapsedMs = Date.now() - startedAt;
  const timeUsed = `${(elapsedMs / 1000).toFixed(1)}s`;

  const execution = await db.execution.create({
    data: {
      id: executionId(),
      intentId: intent_id,
      pathId: path_id,
      capabilityIds: capability_ids.join(","),
      nodeId: process.env.OM_NODE_ID || "local-dev",
      outputJson: JSON.stringify(output),
      outputText,
      traceJson: JSON.stringify({
        started_at: new Date(startedAt).toISOString(),
        finished_at: new Date().toISOString(),
        elapsed_ms: elapsedMs,
        capability_count: capabilities.length,
        execution_mode: executionMode,
        reused_pattern_id: reusable?.id ?? null,
      }),
      cost: path.estimatedCost ?? null,
      timeUsed,
      status: "completed",
    },
  });

  await db.intent.update({ where: { id: intent_id }, data: { status: "fulfilled" } });
  await db.realizationPath.update({ where: { id: path_id }, data: { status: "completed" } });

  for (const cap of capabilities) {
    try {
      await rewardCapabilityProvider({
        providerContact: cap.providerContact,
        capabilityId: cap.id,
        executionId: execution.id,
        intentId: intent_id,
      });
    } catch (e) { console.error("rewardCapabilityProvider failed:", e); }
  }

  let patternEvent: { pattern_id: string; action: "reused" | "created" } | null = null;
  if (classified) {
    if (reusable) {
      await incrementPatternReuse(reusable.id);
      patternEvent = { pattern_id: reusable.id, action: "reused" };
      if (reusable.creatorId) {
        try {
          await rewardPatternReuse({
            creatorContact: reusable.creatorId,
            patternId: reusable.id,
            intentId: intent_id,
          });
        } catch (e) { console.error("rewardPatternReuse failed:", e); }
      }
    } else {
      try {
        const newPattern = await createPatternFromExecution({
          intentId: intent_id,
          intentText: intent.intentText,
          classifiedIntent: classified,
          path: matchedPath,
          capabilitiesUsed: capability_ids,
          outcomeSummary: outputText,
          creatorContact: capabilities[0]?.providerContact,
          historicalCost: path.estimatedCost ?? undefined,
          historicalTime: timeUsed,
        });
        patternEvent = { pattern_id: newPattern.id, action: "created" };
        if (newPattern.creatorId) {
          try {
            await rewardPatternCreation({
              creatorContact: newPattern.creatorId,
              patternId: newPattern.id,
              intentId: intent_id,
            });
          } catch (e) { console.error("rewardPatternCreation failed:", e); }
        }
      } catch (e) { console.error("Pattern creation failed (non-fatal):", e); }
    }
  }

  return NextResponse.json({
    execution_id: execution.id,
    status: execution.status,
    output_text: outputText,
    time_used: timeUsed,
    execution_mode: executionMode,
    pattern_event: patternEvent,
  }, { status: 201 });
}
