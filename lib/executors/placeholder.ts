/**
 * Placeholder executor — used when no registered executor matches the intent_type.
 *
 * Records the execution so the Pattern Library / OMC ledger / dashboard remain
 * consistent, but produces no real artifact. Preserves pre-Phase-0 behavior
 * for unsupported intent categories.
 */

import type { Executor } from "../capabilities";

export const placeholderExecutor: Executor = async (ctx) => {
  return {
    output: {
      note: `No automated executor is registered for intent_type "${ctx.intent.intentType ?? "(unclassified)"}". This execution is recorded; the loop closes and pattern logic still runs, but no artifact was produced.`,
    },
    outputText: "Manual / out-of-band execution recorded.",
    executionMode: "placeholder",
  };
};

// Placeholder is local-only — there's nothing for a node to do.
placeholderExecutor.runsOnNode = false;
