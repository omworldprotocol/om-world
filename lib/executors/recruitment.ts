/**
 * Genesis Builder Recruitment executor.
 *
 * Extracted verbatim from the original `isRecruitment` branch in
 * `app/api/executions/route.ts` as part of the Phase 0 dispatcher refactor.
 * Behavior must be identical: fresh generation by default; adaptive fast path
 * when a reusable Pattern for the same intent_type exists and the source
 * execution's output has the expected shape.
 */

import { db } from "../db";
import {
  adaptRecruitmentCampaign,
  generateRecruitmentCampaign,
  type RecruitmentCampaign,
} from "../llm";
import type { Executor } from "../capabilities";

export const recruitmentExecutor: Executor = async (ctx) => {
  const { intent, reusable } = ctx;

  // ADAPTIVE FAST PATH (spec §16): if a reusable pattern exists for this intent
  // type, fetch the previous successful execution's output and adapt it for the
  // new intent. This is what makes the second realization cheaper than the first.
  if (reusable?.originalIntentId) {
    const sourceExec = await db.execution.findFirst({
      where: { intentId: reusable.originalIntentId, status: "completed" },
      orderBy: { createdAt: "asc" },
    });
    const sourceIntent = await db.intent.findUnique({
      where: { id: reusable.originalIntentId },
    });

    if (sourceExec?.outputJson && sourceIntent) {
      try {
        const prev = JSON.parse(sourceExec.outputJson) as RecruitmentCampaign;
        // Heuristic: only attempt adaptation if the previous output has the expected shape.
        if (prev?.project_positioning && Array.isArray(prev?.x_thread)) {
          const adapted = await adaptRecruitmentCampaign({
            previousCampaign: prev,
            previousIntentText: sourceIntent.intentText,
            newIntentText: intent.intentText,
            newContext: intent.context,
          });
          return {
            output: adapted,
            outputText: `Adapted recruitment campaign from pattern ${reusable.id} (source intent: ${reusable.originalIntentId}).`,
            executionMode: "adapted",
          };
        }
      } catch (e) {
        console.warn("Adaptive path failed, falling back to fresh generation:", e);
      }
    }
  }

  const generated = await generateRecruitmentCampaign({
    intentText: intent.intentText,
    context: intent.context,
    desiredOutput: intent.desiredOutput,
  });

  return {
    output: generated,
    outputText:
      "Generated full recruitment campaign package (positioning, X article, X thread, DM templates, GitHub issue plan, target profiles, follow-up plan).",
    executionMode: "fresh",
  };
};

// MVP runs server-side today; Phase 2 will make this offloadable to compute nodes
// once node-side LLM credentials are figured out (see plan §Phase 2 risks).
recruitmentExecutor.runsOnNode = true;
