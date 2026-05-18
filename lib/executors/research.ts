/**
 * research.cite_synthesis executor.
 *
 * Flow:
 *   1. LLM decomposes the intent into 3-5 search queries
 *   2. OpenClaw web search runs each query (DuckDuckGo), dedup URLs
 *   3. LLM synthesizes a sourced brief from the hits (fresh path)
 *      OR adapts the previous brief's structure for the new topic + new hits (adaptive)
 *
 * Inputs: intent.intentText (treated as the topic), intent.context (optional framing).
 * Output: ResearchBrief { brief_markdown, claims, bibliography, queries_used, source_count }.
 *
 * Per Phase 3 plan, this capability runsOnNode = true so compute-enabled nodes
 * can claim it. Node-side runner (node-client/src/runners/research.ts) mirrors
 * this logic.
 */

import {
  adaptResearchBrief,
  generateResearchBrief,
  generateSearchQueries,
  generateUnsourcedBrief,
  type ResearchBrief,
} from "../llm";
import { multiSearch } from "../openclaw_web";
import type { Executor } from "../capabilities";

const MAX_HITS = Number(process.env.OMW_RESEARCH_MAX_HITS ?? 12);
const PER_QUERY_LIMIT = Number(process.env.OMW_RESEARCH_PER_QUERY_LIMIT ?? 5);

export const researchExecutor: Executor = async (ctx) => {
  const { intent, reusable } = ctx;
  const topic = intent.intentText;
  const context = intent.context;

  // Step 1: decompose into queries
  const queries = await generateSearchQueries({ topic, context });
  if (queries.length === 0) {
    throw new Error("research executor: classifier failed to produce any search queries");
  }

  // Step 2: run the queries via OpenClaw web search
  const hits = await multiSearch({
    queries,
    perQueryLimit: PER_QUERY_LIMIT,
    maxTotal: MAX_HITS,
  });

  if (hits.length === 0) {
    // Graceful degradation: web search unavailable (DuckDuckGo rate limit / network).
    // Produce an unsourced brief from LLM training knowledge with an explicit
    // ⚠️ caveat block. Output keeps the same shape; downstream consumers don't branch.
    const unsourced = await generateUnsourcedBrief({
      topic,
      context,
      queriesAttempted: queries,
      reason: "all web search queries returned 0 hits (likely DuckDuckGo rate limit / bot challenge)",
    });
    return {
      output: unsourced,
      outputText: `Generated unsourced brief on "${topic.slice(0, 80)}" — web search unavailable, training-knowledge fallback. ${queries.length} queries attempted, 0 hits returned.`,
      executionMode: "fresh",
    };
  }

  // Step 3: synthesize or adapt
  // Server-side adaptive path: if reusable Pattern exists and its source execution
  // wrote a ResearchBrief-shaped output, mirror its structure for the new topic.
  if (reusable?.originalIntentId) {
    const { db } = await import("../db");
    const [sourceExec, sourceIntent] = await Promise.all([
      db.execution.findFirst({
        where: { intentId: reusable.originalIntentId, status: "completed" },
        orderBy: { createdAt: "asc" },
      }),
      db.intent.findUnique({ where: { id: reusable.originalIntentId } }),
    ]);

    if (sourceExec?.outputJson && sourceIntent) {
      try {
        const prev = JSON.parse(sourceExec.outputJson) as ResearchBrief;
        if (typeof prev?.brief_markdown === "string" && Array.isArray(prev?.bibliography)) {
          const adapted = await adaptResearchBrief({
            previousBrief: prev,
            previousTopic: sourceIntent.intentText,
            newTopic: topic,
            newContext: context,
            newHits: hits,
            newQueriesUsed: queries,
          });
          return {
            output: adapted,
            outputText: `Adapted research brief from pattern ${reusable.id} (${hits.length} sources, ${queries.length} queries).`,
            executionMode: "adapted",
          };
        }
      } catch (e) {
        console.warn("research adaptive path failed, falling back to fresh:", e);
      }
    }
  }

  const fresh = await generateResearchBrief({
    topic,
    context,
    hits,
    queriesUsed: queries,
  });
  return {
    output: fresh,
    outputText: `Generated sourced research brief on "${topic.slice(0, 80)}" with ${hits.length} cited sources across ${queries.length} queries.`,
    executionMode: "fresh",
  };
};

researchExecutor.runsOnNode = true;
