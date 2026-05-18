/**
 * Node-side recruitment runner. Mirrors lib/executors/recruitment.ts: if the
 * server sent a `reusable` block, take the adaptive fast path; otherwise
 * generate fresh.
 */

import {
  adaptRecruitmentCampaign,
  generateRecruitmentCampaign,
  type RecruitmentCampaign,
} from "../llm.js";

export interface RunnerInput {
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

export interface RunnerResult {
  output: unknown;
  outputText: string;
  executionMode: "fresh" | "adapted";
}

export async function runRecruitment(input: RunnerInput): Promise<RunnerResult> {
  const prev = input.reusable?.source_output_json as RecruitmentCampaign | undefined;

  // Adaptive fast path — only if the prior output has the expected shape.
  if (input.reusable && prev?.project_positioning && Array.isArray(prev?.x_thread)) {
    const adapted = await adaptRecruitmentCampaign({
      previousCampaign: prev,
      previousIntentText: input.reusable.source_intent_text ?? "",
      newIntentText: input.intent.text,
      newContext: input.intent.context,
    });
    return {
      output: adapted,
      outputText: `Adapted recruitment campaign from pattern ${input.reusable.pattern_id} (node-side runner).`,
      executionMode: "adapted",
    };
  }

  const generated = await generateRecruitmentCampaign({
    intentText: input.intent.text,
    context: input.intent.context,
    desiredOutput: input.intent.desired_output,
  });

  return {
    output: generated,
    outputText:
      "Generated full recruitment campaign package on node (positioning, X article, X thread, DM templates, GitHub issue plan, target profiles, follow-up plan).",
    executionMode: "fresh",
  };
}
