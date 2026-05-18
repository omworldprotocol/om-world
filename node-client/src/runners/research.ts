/**
 * Node-side research runner. Mirrors lib/executors/research.ts.
 *
 * Compute nodes that opt into `research.cite_synthesis` decompose the topic
 * into queries, fetch hits via OpenClaw web search (local subprocess),
 * and synthesize/adapt the brief via the LLM (also local subprocess).
 */

import {
  adaptResearchBrief,
  generateResearchBrief,
  generateSearchQueries,
  generateUnsourcedBrief,
  type ResearchBrief,
} from "../llm.js";
import { multiSearch } from "../openclaw_web.js";

const MAX_HITS = Number(process.env.OMW_RESEARCH_MAX_HITS ?? 12);
const PER_QUERY_LIMIT = Number(process.env.OMW_RESEARCH_PER_QUERY_LIMIT ?? 5);

export interface ResearchRunnerInput {
  executor_kind: string;
  intent: {
    id: string;
    text: string;
    context: string | null;
    desired_output: string | null;
  };
  classified: unknown;
  matched_path: unknown;
  capabilities: Array<{ id: string; name: string; capability_type: string; intent_types_supported: string[] }>;
  reusable: null | {
    pattern_id: string;
    pattern_name: string;
    source_intent_text: string | null;
    source_output_json: unknown | null;
  };
}

export interface ResearchRunnerResult {
  output: unknown;
  outputText: string;
  executionMode: "fresh" | "adapted";
}

export async function runResearch(input: ResearchRunnerInput): Promise<ResearchRunnerResult> {
  const topic = input.intent.text;
  const context = input.intent.context;

  const queries = await generateSearchQueries({ topic, context });
  if (queries.length === 0) {
    throw new Error("research runner: classifier produced 0 queries");
  }

  const hits = await multiSearch({ queries, perQueryLimit: PER_QUERY_LIMIT, maxTotal: MAX_HITS });
  if (hits.length === 0) {
    // Graceful degradation — DuckDuckGo rate-limit / network failure.
    const unsourced = await generateUnsourcedBrief({
      topic,
      context,
      queriesAttempted: queries,
      reason: "all web search queries returned 0 hits (likely DuckDuckGo rate limit / bot challenge)",
    });
    return {
      output: unsourced,
      outputText: `Generated unsourced brief on "${topic.slice(0, 80)}" — web search unavailable, training-knowledge fallback (node-side runner). ${queries.length} queries attempted.`,
      executionMode: "fresh",
    };
  }

  const prev = input.reusable?.source_output_json as ResearchBrief | undefined;
  if (input.reusable && typeof prev?.brief_markdown === "string" && Array.isArray(prev?.bibliography)) {
    const adapted = await adaptResearchBrief({
      previousBrief: prev,
      previousTopic: input.reusable.source_intent_text ?? "",
      newTopic: topic,
      newContext: context,
      newHits: hits,
      newQueriesUsed: queries,
    });
    return {
      output: adapted,
      outputText: `Adapted research brief from pattern ${input.reusable.pattern_id} (${hits.length} sources, node-side runner).`,
      executionMode: "adapted",
    };
  }

  const fresh = await generateResearchBrief({ topic, context, hits, queriesUsed: queries });
  return {
    output: fresh,
    outputText: `Generated sourced research brief on "${topic.slice(0, 80)}" with ${hits.length} cited sources (node-side runner).`,
    executionMode: "fresh",
  };
}
