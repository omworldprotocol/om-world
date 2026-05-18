import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { executionId } from "@/lib/ids";
import {
  adaptRecruitmentCampaign,
  generateRecruitmentCampaign,
  type ClassifiedIntent,
  type MatchedPath,
  type RecruitmentCampaign,
} from "@/lib/llm";
import { rewardCapabilityProvider, rewardPatternCreation, rewardPatternReuse } from "@/lib/credits";
import { createPatternFromExecution, findReusablePattern, incrementPatternReuse } from "@/lib/patterns";

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

  const startedAt = Date.now();
  let output: unknown = null;
  let outputText = "";
  let executionMode: "fresh" | "adapted" | "placeholder" = "placeholder";

  // MVP §9: only one intent category is fully executable: Genesis Builder Recruitment.
  // For others, return a placeholder so the loop still closes and pattern logic still runs.
  const isRecruitment = intent.intentType?.startsWith("community_growth.builder_recruitment") ?? false;
  if (isRecruitment) {
    let adapted = false;

    // ADAPTIVE FAST PATH (spec §16): if a reusable pattern exists for this intent type,
    // fetch the previous successful execution's output and adapt it for the new intent.
    // This is what makes the second realization cheaper than the first.
    if (reusable?.originalIntentId) {
      const sourceExec = await db.execution.findFirst({
        where: { intentId: reusable.originalIntentId, status: "completed" },
        orderBy: { createdAt: "asc" },
      });
      const sourceIntent = await db.intent.findUnique({ where: { id: reusable.originalIntentId } });

      if (sourceExec?.outputJson && sourceIntent) {
        try {
          const prev = JSON.parse(sourceExec.outputJson) as RecruitmentCampaign;
          // Heuristic: only attempt adaptation if the previous output has the expected shape.
          if (prev?.project_positioning && Array.isArray(prev?.x_thread)) {
            output = await adaptRecruitmentCampaign({
              previousCampaign: prev,
              previousIntentText: sourceIntent.intentText,
              newIntentText: intent.intentText,
              newContext: intent.context,
            });
            outputText = `Adapted recruitment campaign from pattern ${reusable.id} (source intent: ${reusable.originalIntentId}).`;
            executionMode = "adapted";
            adapted = true;
          }
        } catch (e) {
          console.warn("Adaptive path failed, falling back to fresh generation:", e);
        }
      }
    }

    if (!adapted) {
      try {
        output = await generateRecruitmentCampaign({
          intentText: intent.intentText,
          context: intent.context,
          desiredOutput: intent.desiredOutput,
        });
        outputText = "Generated full recruitment campaign package (positioning, X article, X thread, DM templates, GitHub issue plan, target profiles, follow-up plan).";
        executionMode = "fresh";
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        return NextResponse.json({ error: "Execution failed", message }, { status: 502 });
      }
    }
  } else {
    output = {
      note: "MVP supports automated execution only for community_growth.builder_recruitment intents. This execution is recorded but produced no artifact.",
    };
    outputText = "Manual / out-of-band execution recorded.";
  }

  const elapsedMs = Date.now() - startedAt;
  const timeUsed = `${(elapsedMs / 1000).toFixed(1)}s`;

  const matchedPath: MatchedPath = {
    path_summary: path.pathSummary ?? "",
    recommended_capabilities: csvList(path.recommendedCapabilities),
    estimated_cost: path.estimatedCost ?? "",
    estimated_time: path.estimatedTime ?? "",
    proof_condition: path.proofCondition ?? "",
    settlement_template: path.settlementTemplate ?? "fixed_payment",
    why_this_path: "",
  };

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
