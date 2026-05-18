import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { executionId } from "@/lib/ids";
import type { ClassifiedIntent, MatchedPath } from "@/lib/llm";
import { rewardCapabilityProvider, rewardPatternCreation, rewardPatternReuse } from "@/lib/credits";
import { createPatternFromExecution, findReusablePattern, incrementPatternReuse } from "@/lib/patterns";
import { runCapability } from "@/lib/capabilities";

const ExecutionRequest = z.object({
  intent_id: z.string(),
  path_id: z.string(),
  capability_ids: z.array(z.string()).min(1),
});

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

export async function POST(req: Request) {
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

  // Determine classification (needed early for reusable-pattern lookup).
  let classified: ClassifiedIntent | null = null;
  if (intent.constraintsJson) {
    try { classified = JSON.parse(intent.constraintsJson) as ClassifiedIntent; } catch { /* ignore */ }
  }

  // Check for reusable pattern BEFORE generation — enables the fast adaptive path.
  let reusable: Awaited<ReturnType<typeof findReusablePattern>> = null;
  if (classified) {
    reusable = await findReusablePattern(classified.intent_type);
  }

  const matchedPath: MatchedPath = {
    path_summary: path.pathSummary ?? "",
    recommended_capabilities: csvList(path.recommendedCapabilities),
    estimated_cost: path.estimatedCost ?? "",
    estimated_time: path.estimatedTime ?? "",
    proof_condition: path.proofCondition ?? "",
    settlement_template: path.settlementTemplate ?? "fixed_payment",
    why_this_path: "",
  };

  const startedAt = Date.now();

  // Single dispatch point. The registry resolves the executor by intent_type
  // (longest-prefix match), falling back to the placeholder for unsupported types.
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

  // Reward each capability provider
  for (const cap of capabilities) {
    try {
      await rewardCapabilityProvider({
        providerContact: cap.providerContact,
        capabilityId: cap.id,
        executionId: execution.id,
        intentId: intent_id,
      });
    } catch (e) {
      console.error("rewardCapabilityProvider failed:", e);
    }
  }

  // Pattern logic: reuse if we already found one above; otherwise create.
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
      } catch (e) {
        console.error("Pattern creation failed (non-fatal):", e);
      }
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
