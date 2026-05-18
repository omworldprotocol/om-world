/**
 * Capability executor registry (Phase 0 of MVP Wave 2 plan).
 *
 * Each capability is an executor: a pure async function that takes an
 * `ExecutorContext` (everything from the intent / path / capabilities / reusable
 * pattern) and returns an `ExecutorResult` (the output to record in the
 * `executions` table).
 *
 * The route handler `/api/executions` looks up the executor for an intent's
 * classified `intent_type` and calls it. Pattern creation/reuse, OMC reward,
 * and trace recording happen in the route handler — uniformly for every
 * capability — so executors stay small.
 *
 * Lookup is **longest-prefix match** to preserve the pre-refactor behavior
 * where `community_growth.builder_recruitment` matched `community_growth.builder_recruitment.bd_v2`,
 * etc. If no registered prefix matches, the placeholder executor runs.
 */

import type { Intent, RealizationPath, Capability, Pattern } from "@prisma/client";
import type { ClassifiedIntent, MatchedPath } from "./llm";

export interface ExecutorContext {
  intent: Intent;
  classified: ClassifiedIntent | null;
  path: RealizationPath;
  matchedPath: MatchedPath;
  capabilities: Capability[];
  reusable: Pattern | null;
  /** "local-dev" by default; Phase 2 will inject a real node ID when work is claimed by a node. */
  nodeId: string;
}

export interface ExecutorResult {
  output: unknown;
  outputText: string;
  executionMode: "fresh" | "adapted" | "placeholder";
  /** Phase 4+ will populate this when blob storage is wired in. */
  artifactRefs?: Array<{ kind: string; uri: string; sha256: string }>;
}

export interface Executor {
  (ctx: ExecutorContext): Promise<ExecutorResult>;
  /** Phase 2 reads this to decide if work is offloadable to compute nodes. */
  runsOnNode?: boolean;
}

import { recruitmentExecutor } from "./executors/recruitment";
import { placeholderExecutor } from "./executors/placeholder";
import { researchExecutor } from "./executors/research";

/**
 * The capability registry. Keys are canonical `intent_type` strings.
 * Add a new capability by importing its executor and adding one entry here.
 */
export const CAPABILITY_EXECUTORS: Record<string, Executor> = {
  "community_growth.builder_recruitment": recruitmentExecutor,
  "research.cite_synthesis": researchExecutor,
};

/**
 * Resolve an executor for a given intent_type via longest-prefix match.
 * Returns the placeholder executor if no registered prefix matches.
 */
export function resolveExecutor(intentType: string | null | undefined): Executor {
  if (!intentType) return placeholderExecutor;
  let bestKey: string | null = null;
  for (const key of Object.keys(CAPABILITY_EXECUTORS)) {
    if (intentType === key || intentType.startsWith(key + ".")) {
      if (bestKey === null || key.length > bestKey.length) bestKey = key;
    }
  }
  return bestKey ? CAPABILITY_EXECUTORS[bestKey] : placeholderExecutor;
}

/**
 * Run a capability end-to-end. Thin wrapper that just resolves and invokes.
 * The route handler uses this as its single execution call.
 */
export async function runCapability(ctx: ExecutorContext): Promise<ExecutorResult> {
  const executor = resolveExecutor(ctx.intent.intentType);
  return executor(ctx);
}
