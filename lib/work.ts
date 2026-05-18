/**
 * Work queue for Phase 2 (compute nodes).
 *
 * When POST /api/executions arrives for a `runsOnNode` capability, the route
 * creates an Execution(status="queued") + WorkAssignment(status="queued") and
 * returns immediately. Three forces can then complete the work:
 *
 *   1) A compute-capable node claims via heartbeat → returns result via
 *      PUT /api/nodes/work
 *   2) The fallback sweep (`runFallbackSweep`) runs queued work inline on the
 *      server if it's been waiting > OMW_LOCAL_FALLBACK_AFTER_SEC
 *   3) A heartbeat-triggered sweep nudges the fallback path even without an
 *      explicit cron — keeps cold-startup honest
 *
 * Both completion paths converge on `completeWork()`, which:
 *  - writes the Execution row to "completed"
 *  - updates Intent + RealizationPath status
 *  - fires OMC rewards (capability provider + pattern create/reuse +
 *    optional node compute reward)
 */

import type { Capability, Intent, Pattern, RealizationPath } from "@prisma/client";
import { db } from "./db";
import { executionId, workAssignmentId } from "./ids";
import type { ClassifiedIntent, MatchedPath } from "./llm";
import { resolveExecutor, runCapability, type ExecutorContext } from "./capabilities";
import {
  rewardCapabilityProvider,
  rewardPatternCreation,
  rewardPatternReuse,
  rewardNodeCompute,
} from "./credits";
import { createPatternFromExecution, findReusablePattern, incrementPatternReuse } from "./patterns";

const FALLBACK_AFTER_SEC = Number(process.env.OMW_LOCAL_FALLBACK_AFTER_SEC ?? 600);

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

/**
 * The minimal serializable input we hand to a node so it can run the executor
 * without re-classifying or re-fetching DB rows. The node may need this data
 * to run an LLM call locally (recruitment, research, etc.).
 */
export interface NodeRunnerInput {
  executor_kind: string;
  intent: {
    id: string;
    text: string;
    context: string | null;
    desired_output: string | null;
  };
  classified: ClassifiedIntent | null;
  matched_path: MatchedPath;
  capabilities: Array<{
    id: string;
    name: string;
    capability_type: string;
    intent_types_supported: string[];
  }>;
  reusable: null | {
    pattern_id: string;
    pattern_name: string;
    source_intent_text: string | null;
    source_output_json: unknown | null;
  };
}

function buildRunnerInput(opts: {
  intent: Intent;
  classified: ClassifiedIntent | null;
  matchedPath: MatchedPath;
  capabilities: Capability[];
  reusable: Pattern | null;
  sourceExecutionOutput: unknown | null;
  sourceIntentText: string | null;
}): NodeRunnerInput {
  return {
    executor_kind: opts.intent.intentType ?? "(unclassified)",
    intent: {
      id: opts.intent.id,
      text: opts.intent.intentText,
      context: opts.intent.context,
      desired_output: opts.intent.desiredOutput,
    },
    classified: opts.classified,
    matched_path: opts.matchedPath,
    capabilities: opts.capabilities.map((c) => ({
      id: c.id,
      name: c.name,
      capability_type: c.capabilityType,
      intent_types_supported: csvList(c.intentTypesSupported),
    })),
    reusable: opts.reusable
      ? {
          pattern_id: opts.reusable.id,
          pattern_name: opts.reusable.patternName,
          source_intent_text: opts.sourceIntentText,
          source_output_json: opts.sourceExecutionOutput,
        }
      : null,
  };
}

/**
 * Enqueue an execution as a WorkAssignment. Creates both rows in one transaction.
 * Returns the newly-created executionId + workAssignmentId.
 */
export async function enqueueWork(opts: {
  intent: Intent;
  classified: ClassifiedIntent | null;
  path: RealizationPath;
  matchedPath: MatchedPath;
  capabilities: Capability[];
  reusable: Pattern | null;
  capabilityIds: string[];
}): Promise<{ executionId: string; workAssignmentId: string }> {
  // Pre-fetch source execution output for adaptive path so nodes don't need DB access.
  let sourceExecutionOutput: unknown | null = null;
  let sourceIntentText: string | null = null;
  if (opts.reusable?.originalIntentId) {
    const [sourceExec, sourceIntent] = await Promise.all([
      db.execution.findFirst({
        where: { intentId: opts.reusable.originalIntentId, status: "completed" },
        orderBy: { createdAt: "asc" },
      }),
      db.intent.findUnique({ where: { id: opts.reusable.originalIntentId } }),
    ]);
    if (sourceExec?.outputJson) {
      try { sourceExecutionOutput = JSON.parse(sourceExec.outputJson); } catch { /* ignore */ }
    }
    sourceIntentText = sourceIntent?.intentText ?? null;
  }

  const runnerInput = buildRunnerInput({
    intent: opts.intent,
    classified: opts.classified,
    matchedPath: opts.matchedPath,
    capabilities: opts.capabilities,
    reusable: opts.reusable,
    sourceExecutionOutput,
    sourceIntentText,
  });

  const execId = executionId();
  const workId = workAssignmentId();

  await db.$transaction(async (tx) => {
    await tx.execution.create({
      data: {
        id: execId,
        intentId: opts.intent.id,
        pathId: opts.path.id,
        capabilityIds: opts.capabilityIds.join(","),
        nodeId: null,
        outputJson: null,
        outputText: "queued",
        traceJson: JSON.stringify({
          queued_at: new Date().toISOString(),
          execution_mode: "queued",
        }),
        cost: opts.path.estimatedCost ?? null,
        timeUsed: null,
        status: "queued",
      },
    });
    await tx.workAssignment.create({
      data: {
        id: workId,
        executionId: execId,
        executorKind: opts.intent.intentType ?? "(unclassified)",
        nodeId: null,
        status: "queued",
        inputJson: JSON.stringify(runnerInput),
      },
    });
    await tx.intent.update({
      where: { id: opts.intent.id },
      data: { status: "in_execution" },
    });
  });

  return { executionId: execId, workAssignmentId: workId };
}

/**
 * Atomically claim the next queued WorkAssignment matching one of the node's executor kinds.
 * Uses a conditional update so two nodes heartbeating simultaneously can't double-claim.
 */
export async function claimNextWorkForNode(opts: {
  nodeId: string;
  executorKinds: string[];
}): Promise<{ workAssignmentId: string; executionId: string; executorKind: string; inputJson: string } | null> {
  if (opts.executorKinds.length === 0) return null;

  const candidate = await db.workAssignment.findFirst({
    where: {
      status: "queued",
      executorKind: { in: opts.executorKinds },
    },
    orderBy: { createdAt: "asc" },
  });
  if (!candidate) return null;

  // updateMany with the additional `status: "queued"` predicate is the atomic claim.
  const claimResult = await db.workAssignment.updateMany({
    where: { id: candidate.id, status: "queued" },
    data: { status: "claimed", nodeId: opts.nodeId, claimedAt: new Date() },
  });
  if (claimResult.count === 0) {
    // Lost the race; another node grabbed it. Caller will retry next heartbeat.
    return null;
  }

  // Also flip the Execution row to "running" so /api/executions/[id] reflects state.
  await db.execution.update({
    where: { id: candidate.executionId },
    data: { status: "running", nodeId: opts.nodeId },
  });

  return {
    workAssignmentId: candidate.id,
    executionId: candidate.executionId,
    executorKind: candidate.executorKind,
    inputJson: candidate.inputJson,
  };
}

export interface CompleteWorkInput {
  workAssignmentId: string;
  nodeId: string | null; // null = ran on server (fallback)
  output: unknown;
  outputText: string;
  executionMode: "fresh" | "adapted" | "placeholder";
  elapsedSec: number;
}

/**
 * Common completion path used by both: (a) node-submitted results,
 * (b) server-side fallback inline runs.
 * Fires all the OMC rewards + records pattern create/reuse.
 */
export async function completeWork(input: CompleteWorkInput): Promise<{
  patternEvent: { pattern_id: string; action: "reused" | "created" } | null;
}> {
  const work = await db.workAssignment.findUnique({ where: { id: input.workAssignmentId } });
  if (!work) throw new Error(`workAssignment ${input.workAssignmentId} not found`);
  if (work.status === "completed") {
    // Idempotent — completion already happened. Re-derive pattern event for response.
    return { patternEvent: null };
  }

  const execution = await db.execution.findUnique({ where: { id: work.executionId } });
  if (!execution) throw new Error(`execution ${work.executionId} not found`);

  const path = await db.realizationPath.findUnique({ where: { id: execution.pathId! } });
  const intent = await db.intent.findUnique({ where: { id: execution.intentId } });
  if (!path || !intent) throw new Error(`path or intent missing for execution ${execution.id}`);

  const capIds = csvList(execution.capabilityIds);
  const capabilities = await db.capability.findMany({ where: { id: { in: capIds } } });

  let classified: ClassifiedIntent | null = null;
  if (intent.constraintsJson) {
    try { classified = JSON.parse(intent.constraintsJson) as ClassifiedIntent; } catch { /* ignore */ }
  }
  const reusable = classified ? await findReusablePattern(classified.intent_type) : null;

  const timeUsed = `${input.elapsedSec.toFixed(1)}s`;

  await db.$transaction(async (tx) => {
    await tx.execution.update({
      where: { id: execution.id },
      data: {
        outputJson: JSON.stringify(input.output),
        outputText: input.outputText,
        traceJson: JSON.stringify({
          completed_at: new Date().toISOString(),
          elapsed_sec: input.elapsedSec,
          execution_mode: input.executionMode,
          reused_pattern_id: reusable?.id ?? null,
          executed_by_node: input.nodeId,
        }),
        timeUsed,
        status: "completed",
        nodeId: input.nodeId,
      },
    });
    await tx.workAssignment.update({
      where: { id: work.id },
      data: {
        status: "completed",
        completedAt: new Date(),
        outputJson: JSON.stringify(input.output),
        outputText: input.outputText,
        executionMode: input.executionMode,
        nodeId: input.nodeId,
      },
    });
    await tx.intent.update({ where: { id: execution.intentId }, data: { status: "fulfilled" } });
    await tx.realizationPath.update({ where: { id: path.id }, data: { status: "completed" } });
  });

  // Rewards (best-effort; errors logged but don't fail completion)
  for (const cap of capabilities) {
    try {
      await rewardCapabilityProvider({
        providerContact: cap.providerContact,
        capabilityId: cap.id,
        executionId: execution.id,
        intentId: execution.intentId,
      });
    } catch (e) { console.error("rewardCapabilityProvider failed:", e); }
  }

  if (input.nodeId) {
    try {
      await rewardNodeCompute({
        nodeId: input.nodeId,
        executionId: execution.id,
        elapsedSec: input.elapsedSec,
      });
    } catch (e) { console.error("rewardNodeCompute failed:", e); }
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
            intentId: execution.intentId,
          });
        } catch (e) { console.error("rewardPatternReuse failed:", e); }
      }
    } else {
      try {
        const newPattern = await createPatternFromExecution({
          intentId: execution.intentId,
          intentText: intent.intentText,
          classifiedIntent: classified,
          path: {
            path_summary: path.pathSummary ?? "",
            recommended_capabilities: capIds,
            estimated_cost: path.estimatedCost ?? "",
            estimated_time: path.estimatedTime ?? "",
            proof_condition: path.proofCondition ?? "",
            settlement_template: path.settlementTemplate ?? "fixed_payment",
            why_this_path: "",
          },
          capabilitiesUsed: capIds,
          outcomeSummary: input.outputText,
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
              intentId: execution.intentId,
            });
          } catch (e) { console.error("rewardPatternCreation failed:", e); }
        }
      } catch (e) { console.error("Pattern creation failed (non-fatal):", e); }
    }
  }

  return { patternEvent };
}

/**
 * Inline-run a queued WorkAssignment on the server (fallback path).
 * Reads input + ctx from the DB, calls the registry directly, completes.
 */
export async function runQueuedWorkInline(workAssignmentId: string): Promise<void> {
  const work = await db.workAssignment.findUnique({ where: { id: workAssignmentId } });
  if (!work || work.status !== "queued") return;

  // Atomic claim by server.
  const claim = await db.workAssignment.updateMany({
    where: { id: workAssignmentId, status: "queued" },
    data: { status: "running", nodeId: "local-fallback", claimedAt: new Date() },
  });
  if (claim.count === 0) return; // lost the race
  await db.execution.update({
    where: { id: work.executionId },
    data: { status: "running", nodeId: "local-fallback" },
  });

  const execution = await db.execution.findUniqueOrThrow({ where: { id: work.executionId } });
  const intent = await db.intent.findUniqueOrThrow({ where: { id: execution.intentId } });
  const path = await db.realizationPath.findUniqueOrThrow({ where: { id: execution.pathId! } });
  const capIds = csvList(execution.capabilityIds);
  const capabilities = await db.capability.findMany({ where: { id: { in: capIds } } });

  let classified: ClassifiedIntent | null = null;
  if (intent.constraintsJson) {
    try { classified = JSON.parse(intent.constraintsJson) as ClassifiedIntent; } catch { /* ignore */ }
  }
  const reusable = classified ? await findReusablePattern(classified.intent_type) : null;

  const matchedPath: MatchedPath = {
    path_summary: path.pathSummary ?? "",
    recommended_capabilities: capIds,
    estimated_cost: path.estimatedCost ?? "",
    estimated_time: path.estimatedTime ?? "",
    proof_condition: path.proofCondition ?? "",
    settlement_template: path.settlementTemplate ?? "fixed_payment",
    why_this_path: "",
  };

  const ctx: ExecutorContext = {
    intent,
    classified,
    path,
    matchedPath,
    capabilities,
    reusable,
    nodeId: "local-fallback",
  };

  const startedAt = Date.now();
  try {
    const result = await runCapability(ctx);
    const elapsedSec = (Date.now() - startedAt) / 1000;
    await completeWork({
      workAssignmentId: work.id,
      nodeId: null, // server-side run, no node reward
      output: result.output,
      outputText: result.outputText,
      executionMode: result.executionMode,
      elapsedSec,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    await db.workAssignment.update({
      where: { id: work.id },
      data: { status: "failed", errorText: message, completedAt: new Date() },
    });
    await db.execution.update({
      where: { id: work.executionId },
      data: { status: "failed", outputText: `inline fallback failed: ${message}` },
    });
  }
}

/**
 * Sweep for queued work that has been waiting too long and run it inline.
 * Cheap; called opportunistically from the heartbeat + executions routes.
 * Self-limited to 3 runs per sweep to avoid blocking the calling request.
 */
let sweepInFlight = false;
export async function runFallbackSweep(): Promise<number> {
  if (sweepInFlight) return 0;
  sweepInFlight = true;
  try {
    const cutoff = new Date(Date.now() - FALLBACK_AFTER_SEC * 1000);
    const stale = await db.workAssignment.findMany({
      where: { status: "queued", createdAt: { lt: cutoff } },
      orderBy: { createdAt: "asc" },
      take: 3,
    });
    let count = 0;
    for (const w of stale) {
      try {
        await runQueuedWorkInline(w.id);
        count++;
      } catch (e) {
        console.error(`runFallbackSweep failed for ${w.id}:`, e);
      }
    }
    return count;
  } finally {
    sweepInFlight = false;
  }
}

/**
 * Decide whether a particular intent_type should be enqueued (runs on a node)
 * vs run inline immediately. Driven by the executor's runsOnNode annotation.
 */
export function shouldEnqueue(intentType: string | null | undefined): boolean {
  const exec = resolveExecutor(intentType);
  return exec.runsOnNode === true;
}
