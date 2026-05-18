/**
 * LLM dispatcher: OpenClaw default → DeepSeek fallback. Plus JSON helper.
 * Subset of /Users/feiyang/all_bots/om-world/lib/llm.ts — only what the
 * runners need (recruitment generate + adapt).
 */

import { chatViaOpenclaw } from "./openclaw.js";
import { chatViaDeepseek } from "./deepseek.js";

export async function callLlm(
  systemPrompt: string,
  userPrompt: string,
  options?: { maxTokens?: number; temperature?: number },
): Promise<string> {
  const backend = (process.env.LLM_BACKEND ?? "openclaw").toLowerCase();

  if (backend === "deepseek") {
    const { text } = await chatViaDeepseek({
      system: systemPrompt,
      user: userPrompt,
      maxTokens: options?.maxTokens,
      temperature: options?.temperature,
    });
    return text;
  }

  try {
    const { text } = await chatViaOpenclaw({ system: systemPrompt, user: userPrompt });
    return text;
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    console.warn(`[node:llm] OpenClaw failed (${reason}) — falling back to DeepSeek`);
    const { text } = await chatViaDeepseek({
      system: systemPrompt,
      user: userPrompt,
      maxTokens: options?.maxTokens,
      temperature: options?.temperature,
    });
    return text;
  }
}

export async function callLlmJson<T = unknown>(
  systemPrompt: string,
  userPrompt: string,
  options?: { maxTokens?: number; temperature?: number },
): Promise<T> {
  const raw = (await callLlm(systemPrompt, userPrompt, options)).trim();
  const stripped = raw
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();
  try {
    return JSON.parse(stripped) as T;
  } catch {
    const match = stripped.match(/\{[\s\S]*\}/);
    if (match) return JSON.parse(match[0]) as T;
    throw new Error(`LLM did not return parseable JSON. Raw: ${raw.slice(0, 500)}`);
  }
}

// ---------- Genesis Builder Recruitment ----------
// Type + prompts mirror lib/llm.ts so node + server produce structurally identical outputs.

export interface RecruitmentCampaign {
  project_positioning: string;
  x_article: string;
  x_thread: string[];
  dm_templates: Array<{ audience: string; message: string }>;
  github_issue_plan: Array<{ title: string; body: string }>;
  target_builder_profiles: Array<{ archetype: string; where_to_find: string; signals: string[] }>;
  follow_up_plan: string;
}

export async function generateRecruitmentCampaign(input: {
  intentText: string;
  context?: string | null;
  desiredOutput?: string | null;
}): Promise<RecruitmentCampaign> {
  const system = `You are the OM World Genesis Builder Recruitment Generator.

Produce a complete recruitment campaign package. Tone: humble, technical, specific. Avoid hype.
Avoid token / financial incentives — OM World has no token.

Return JSON only with this shape:
{
  "project_positioning": "1-2 paragraph positioning statement",
  "x_article": "300-500 word article suitable for X (Twitter) long-form",
  "x_thread": ["tweet 1 (<= 280 chars)", "tweet 2", "..."] (5-7 tweets),
  "dm_templates": [{"audience": "GitHub maintainer of intent/agent project", "message": "..."}] (3 templates for different audiences),
  "github_issue_plan": [{"title": "...", "body": "..."}] (2-3 issue templates that could be opened on related repos as design-discussion outreach),
  "target_builder_profiles": [{"archetype": "...", "where_to_find": "GitHub/X/Discord/...", "signals": ["..."]}] (3-5 profiles),
  "follow_up_plan": "schedule and rules for following up"
}`;

  const user = `Intent: ${input.intentText}

Context: ${input.context ?? "(none)"}

Desired output: ${input.desiredOutput ?? "(default — full recruitment package)"}`;

  return callLlmJson<RecruitmentCampaign>(system, user, {
    maxTokens: 4000,
    temperature: 0.7,
  });
}

export async function adaptRecruitmentCampaign(input: {
  previousCampaign: RecruitmentCampaign;
  previousIntentText: string;
  newIntentText: string;
  newContext?: string | null;
}): Promise<RecruitmentCampaign> {
  const system = `You are the OM World Pattern Adapter.

You will receive a PREVIOUS successful recruitment campaign (built for a different project)
and a NEW intent. Adapt the campaign for the new intent.

Rules:
- Keep the same JSON shape.
- Replace project-specific names, roles, and references with the new intent's specifics.
- Preserve the overall structure, tone, and field count (same number of dm_templates, target_builder_profiles, etc.).
- Do not invent new fields. Do not add hype. No token / financial incentive promises.

Return JSON only with the same shape as the previous campaign:
{
  "project_positioning": "...",
  "x_article": "...",
  "x_thread": ["...", "..."],
  "dm_templates": [{"audience": "...", "message": "..."}],
  "github_issue_plan": [{"title": "...", "body": "..."}],
  "target_builder_profiles": [{"archetype": "...", "where_to_find": "...", "signals": ["..."]}],
  "follow_up_plan": "..."
}`;

  const user = `PREVIOUS intent: ${input.previousIntentText}

PREVIOUS campaign (template to adapt):
${JSON.stringify(input.previousCampaign)}

NEW intent: ${input.newIntentText}

NEW context: ${input.newContext ?? "(none)"}

Output the adapted JSON.`;

  return callLlmJson<RecruitmentCampaign>(system, user, {
    maxTokens: 3000,
    temperature: 0.4,
  });
}
