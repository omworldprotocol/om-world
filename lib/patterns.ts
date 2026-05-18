import { db } from "./db";
import { patternId } from "./ids";
import { generatePattern, type ClassifiedIntent, type MatchedPath } from "./llm";

// Phase 3.5 thresholds (red-team #8). Tunable via env.
const FRICTION_REWARD_RATIO = Number(process.env.OMW_FRICTION_REWARD_RATIO ?? 0.85);
const REUSE_WINDOW_SEC = Number(process.env.OMW_REUSE_WINDOW_SEC ?? 7 * 24 * 3600); // 7d
const REUSE_WINDOW_CAP = Number(process.env.OMW_REUSE_WINDOW_CAP ?? 50);
const COOLDOWN_HOURS = Number(process.env.OMW_PATTERN_COOLDOWN_HOURS ?? 168); // 1 week

/**
 * Look up an existing pattern that may already realize this intent_type.
 * MVP heuristic: highest reuse_count with matching intent_type and status=active.
 * Phase 3.5: excludes patterns currently in cool-down (generic-capture defense).
 */
export async function findReusablePattern(intentType: string) {
  const now = new Date();
  return db.pattern.findFirst({
    where: {
      intentType,
      status: "active",
      OR: [{ cooldownUntil: null }, { cooldownUntil: { lt: now } }],
    },
    orderBy: [{ successfulReuseCount: "desc" }, { reuseCount: "desc" }, { createdAt: "asc" }],
  });
}

/**
 * Create a pattern record from a completed execution.
 * Phase 3.5: records the first FRESH execution time so the friction curve has
 * a baseline to compare future adapted executions against.
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
  freshElapsedSec?: number;
}) {
  const generated = await generatePattern({
    intentText: opts.intentText,
    classifiedIntent: opts.classifiedIntent,
    path: opts.path,
    capabilitiesUsed: opts.capabilitiesUsed,
    outcomeSummary: opts.outcomeSummary,
  });

  const freshSec = opts.freshElapsedSec ?? 0;

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
      // Phase 3.5: seed the friction baseline.
      freshTimeSumSec: freshSec,
      freshExecutionCount: freshSec > 0 ? 1 : 0,
      adaptedTimeSumSec: 0,
      adaptedExecutionCount: 0,
      successfulReuseCount: 0,
      notes: generated.historical_notes,
      reusePotential: generated.reuse_potential,
      futureDistributedStorage: true,
      status: "active",
    },
  });
}

/**
 * Phase 3.5 reuse semantics (red-team #8).
 *
 * Caller passes the elapsed time of the adapted execution + the reuser's
 * contact (to enforce creator ≠ reuser for reward gating). Returns:
 *
 *   { rewardEligible: bool, reason: string, pattern: Pattern }
 *
 * - rewardEligible = true ONLY when:
 *   (a) adapted_elapsed < FRICTION_REWARD_RATIO * fresh_avg, AND
 *   (b) reuser_contact != creator_id, AND
 *   (c) pattern is not in cool-down
 * - Else the reuse is still recorded (reuseCount++) but no OMC fires.
 *
 * Also implements the generic-capture defense: if reuses in the current
 * rolling window exceed REUSE_WINDOW_CAP, the pattern enters cool-down.
 */
export async function recordPatternReuse(opts: {
  id: string;
  adaptedElapsedSec: number;
  reuserContact: string | null;
}): Promise<{ rewardEligible: boolean; reason: string; freshAvg: number | null }> {
  const now = new Date();
  const pattern = await db.pattern.findUnique({ where: { id: opts.id } });
  if (!pattern) throw new Error(`pattern ${opts.id} not found`);

  const freshAvg = pattern.freshExecutionCount > 0
    ? pattern.freshTimeSumSec / pattern.freshExecutionCount
    : null;

  // Friction check: did this reuse actually save time?
  const ratio = freshAvg && freshAvg > 0 ? opts.adaptedElapsedSec / freshAvg : 1;
  const fasterThanThreshold = freshAvg !== null && ratio < FRICTION_REWARD_RATIO;
  const creatorIsReuser = pattern.creatorId !== null && pattern.creatorId === opts.reuserContact;
  const inCooldown = pattern.cooldownUntil !== null && pattern.cooldownUntil > now;

  // Rolling window count for generic-capture defense.
  let windowStartedAt = pattern.reuseWindowStartedAt;
  let windowCount = pattern.reuseWindowCount;
  if (!windowStartedAt || (now.getTime() - windowStartedAt.getTime()) > REUSE_WINDOW_SEC * 1000) {
    windowStartedAt = now;
    windowCount = 0;
  }
  windowCount += 1;

  let newCooldownUntil: Date | null = pattern.cooldownUntil;
  if (windowCount >= REUSE_WINDOW_CAP && !inCooldown) {
    newCooldownUntil = new Date(now.getTime() + COOLDOWN_HOURS * 3600 * 1000);
  }

  const rewardEligible = fasterThanThreshold && !creatorIsReuser && !inCooldown;
  const reason = inCooldown
    ? "pattern in cool-down (generic-capture defense triggered)"
    : creatorIsReuser
      ? "creator==reuser; self-reuse earns no OMC"
      : !fasterThanThreshold
        ? `reuse not fast enough (ratio=${ratio.toFixed(2)}, threshold=${FRICTION_REWARD_RATIO})`
        : "OK";

  await db.pattern.update({
    where: { id: opts.id },
    data: {
      reuseCount: { increment: 1 },
      successfulReuseCount: rewardEligible ? { increment: 1 } : undefined,
      adaptedTimeSumSec: { increment: opts.adaptedElapsedSec },
      adaptedExecutionCount: { increment: 1 },
      reuseWindowStartedAt: windowStartedAt,
      reuseWindowCount: windowCount,
      cooldownUntil: newCooldownUntil,
    },
  });

  return { rewardEligible, reason, freshAvg };
}

/**
 * Phase 3.5: when a fresh execution lands for a pattern that already exists
 * (e.g. an intent matched an existing pattern but adaptive path failed and the
 * system regenerated from scratch), add the timing to the fresh accumulator.
 * Used by completeWork on executionMode=="fresh" when reusable was found.
 */
export async function recordFreshExecution(opts: { id: string; freshElapsedSec: number }) {
  return db.pattern.update({
    where: { id: opts.id },
    data: {
      freshTimeSumSec: { increment: opts.freshElapsedSec },
      freshExecutionCount: { increment: 1 },
    },
  });
}

/**
 * Legacy alias for callers that still bump reuseCount the old way.
 * @deprecated use recordPatternReuse for full Phase 3.5 semantics.
 */
export async function incrementPatternReuse(id: string) {
  return db.pattern.update({
    where: { id },
    data: { reuseCount: { increment: 1 } },
  });
}
