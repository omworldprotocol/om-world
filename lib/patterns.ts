import { db } from "./db";
import { patternId } from "./ids";
import { generatePattern, type ClassifiedIntent, type MatchedPath } from "./llm";

/**
 * Look up an existing pattern that may already realize this intent_type.
 * MVP heuristic: highest reuse_count with matching intent_type and status=active.
 */
export async function findReusablePattern(intentType: string) {
  return db.pattern.findFirst({
    where: { intentType, status: "active" },
    orderBy: [{ reuseCount: "desc" }, { successCount: "desc" }, { createdAt: "asc" }],
  });
}

/**
 * Create a pattern record from a completed execution.
 */
export async function createPatternFromExecution(opts: {
  intentId: string;
  intentText: string;
  classifiedIntent: ClassifiedIntent;
  path: MatchedPath;
  capabilitiesUsed: string[];
  outcomeSummary: string;
  creatorContact?: string;
  historicalCost?: string;
  historicalTime?: string;
}) {
  const generated = await generatePattern({
    intentText: opts.intentText,
    classifiedIntent: opts.classifiedIntent,
    path: opts.path,
    capabilitiesUsed: opts.capabilitiesUsed,
    outcomeSummary: opts.outcomeSummary,
  });

  return db.pattern.create({
    data: {
      id: patternId(),
      creatorId: opts.creatorContact ?? null,
      intentType: generated.intent_type,
      patternName: generated.pattern_name,
      description: generated.historical_notes,
      originalIntentId: opts.intentId,
      executionGraphJson: JSON.stringify({
        input_requirements: generated.input_requirements,
        execution_steps: generated.execution_steps,
        proof_condition: generated.proof_condition,
        settlement_template: generated.settlement_template,
        failure_modes: generated.failure_modes,
      }),
      capabilitiesUsed: opts.capabilitiesUsed.join(","),
      historicalCost: opts.historicalCost,
      historicalTime: opts.historicalTime,
      reuseCount: 0,
      successCount: 1,
      failureCount: 0,
      notes: generated.historical_notes,
      reusePotential: generated.reuse_potential,
      futureDistributedStorage: true,
      status: "active",
    },
  });
}

export async function incrementPatternReuse(id: string) {
  return db.pattern.update({
    where: { id },
    data: { reuseCount: { increment: 1 } },
  });
}
