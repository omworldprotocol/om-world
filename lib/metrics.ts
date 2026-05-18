/**
 * Self-growth metrics — Phase 3.5 hardening (red-team #1).
 *
 * Reads the per-pattern timing accumulators set by completeWork() and exposes
 * a structured "friction curve" per intent_type. The /api/summary route uses
 * this to surface a top-level proof of the self-growth thesis: does the
 * second realization actually run faster than the first?
 *
 * The numbers here are the system's central honesty test. If
 * `delta_pct <= 0`, the project is not yet what it claims to be.
 */

import { db } from "./db";

export interface FrictionCurve {
  intent_type: string;
  pattern_id: string | null;
  pattern_name: string | null;
  fresh_count: number;
  adapted_count: number;
  fresh_avg_sec: number | null;
  adapted_avg_sec: number | null;
  /** Negative = adapted is faster than fresh (good); positive = slower (bad/zero growth). */
  delta_sec: number | null;
  /** Same delta as percentage of fresh_avg. -20% means adapted is 20% faster. */
  delta_pct: number | null;
  /** Reuse counts split by friction-bound success vs raw count. */
  reuse_count: number;
  successful_reuse_count: number;
  /** True if there's enough data to claim the self-growth thesis is validated for this intent_type. */
  thesis_validated: boolean;
}

const MIN_SAMPLES_FOR_CLAIM = 1; // need at least 1 fresh + 1 adapted to compute delta

/**
 * Read friction curves for all active patterns, ordered by intent_type.
 * Cheap query — just reads the accumulator fields on Pattern rows.
 */
export async function readFrictionCurves(): Promise<FrictionCurve[]> {
  const patterns = await db.pattern.findMany({
    where: { status: "active" },
    orderBy: { intentType: "asc" },
  });

  return patterns.map((p) => {
    const freshAvg = p.freshExecutionCount > 0 ? p.freshTimeSumSec / p.freshExecutionCount : null;
    const adaptedAvg = p.adaptedExecutionCount > 0 ? p.adaptedTimeSumSec / p.adaptedExecutionCount : null;
    let deltaSec: number | null = null;
    let deltaPct: number | null = null;
    if (freshAvg !== null && adaptedAvg !== null) {
      deltaSec = adaptedAvg - freshAvg;
      deltaPct = freshAvg > 0 ? (deltaSec / freshAvg) * 100 : null;
    }
    return {
      intent_type: p.intentType,
      pattern_id: p.id,
      pattern_name: p.patternName,
      fresh_count: p.freshExecutionCount,
      adapted_count: p.adaptedExecutionCount,
      fresh_avg_sec: freshAvg,
      adapted_avg_sec: adaptedAvg,
      delta_sec: deltaSec,
      delta_pct: deltaPct,
      reuse_count: p.reuseCount,
      successful_reuse_count: p.successfulReuseCount,
      thesis_validated:
        p.freshExecutionCount >= MIN_SAMPLES_FOR_CLAIM &&
        p.adaptedExecutionCount >= MIN_SAMPLES_FOR_CLAIM &&
        deltaSec !== null &&
        deltaSec < 0,
    };
  });
}

/**
 * Single scalar: across all patterns with enough data, what's the median delta_pct?
 * The system's headline self-growth number.
 */
export async function medianDeltaPct(): Promise<number | null> {
  const curves = await readFrictionCurves();
  const valid = curves
    .filter((c) => c.thesis_validated && c.delta_pct !== null)
    .map((c) => c.delta_pct!)
    .sort((a, b) => a - b);
  if (valid.length === 0) return null;
  const mid = Math.floor(valid.length / 2);
  return valid.length % 2 === 0 ? (valid[mid - 1] + valid[mid]) / 2 : valid[mid];
}
