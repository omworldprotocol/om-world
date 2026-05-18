/**
 * Unified LLM routing layer for OM World MVP.
 *
 * Mirrors the SOVEREIGN-X llm_client pattern (connectors/llm_client.py):
 *   LLM_BACKEND=openclaw (default) → openclaw CLI subprocess (GPT-5.5 via ChatGPT Plus OAuth)
 *   LLM_BACKEND=deepseek           → direct DeepSeek API
 *
 * Auto-fallback: if openclaw fails (binary missing, timeout, rc!=0, empty output),
 * automatically retry via DeepSeek.
 *
 * Per repo memory (feedback_openclaw_gpt55_local_path), CLI must NOT pass --gateway
 * on OpenClaw >= 2026.5.12 — semantics were reversed between 5.7-5.12. lib/openclaw.ts
 * handles this correctly.
 */

import { chatViaOpenclaw } from "./openclaw";
import { chatViaDeepseek } from "./deepseek";

type LastModel = string;
let _lastModel: LastModel = "(unset)";
export function lastModel(): LastModel { return _lastModel; }

export async function callLlm(
  systemPrompt: string,
  userPrompt: string,
  options?: { maxTokens?: number; temperature?: number },
): Promise<string> {
  const backend = (process.env.LLM_BACKEND ?? "openclaw").toLowerCase();

  if (backend === "deepseek") {
    const { text, model } = await chatViaDeepseek({
      system: systemPrompt,
      user: userPrompt,
      maxTokens: options?.maxTokens,
      temperature: options?.temperature,
    });
    _lastModel = model;
    return text;
  }

  try {
    const { text, model } = await chatViaOpenclaw({
      system: systemPrompt,
      user: userPrompt,
    });
    _lastModel = model;
    return text;
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    console.warn(`[llm] OpenClaw failed (${reason}) — falling back to DeepSeek`);
    try {
      const { text, model } = await chatViaDeepseek({
        system: systemPrompt,
        user: userPrompt,
        maxTokens: options?.maxTokens,
        temperature: options?.temperature,
      });
      _lastModel = model;
      return text;
    } catch (fallbackErr) {
      const fallReason = fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr);
      throw new Error(`Both OpenClaw and DeepSeek failed. OpenClaw: ${reason}. DeepSeek: ${fallReason}`);
    }
  }
}

/**
 * Call LLM with a single user message that must return strict JSON.
 * Strips ```json fences and parses. Throws if not parseable.
 */
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
    if (match) {
      return JSON.parse(match[0]) as T;
    }
    throw new Error(`LLM did not return parseable JSON. Raw: ${raw.slice(0, 500)}`);
  }
}

// ---------- Spec §7.1 — Intent classification ----------

export interface ClassifiedIntent {
  intent_type: string;
  summary: string;
  required_capabilities: string[];
  desired_outputs: string[];
  risk_level: "low" | "medium" | "high";
  estimated_complexity: "low" | "medium" | "high";
  reusable_pattern_potential: "low" | "medium" | "high";
}

export async function classifyIntent(input: {
  intentText: string;
  context?: string | null;
}): Promise<ClassifiedIntent> {
  const system = `You are the OM World Intent Classifier.

Given a user's intent, classify it into an intent_type.

Return JSON only — no prose, no code fences.

Fields:
- intent_type: concise snake_case category, e.g. "community_growth.builder_recruitment"
- summary: one sentence
- required_capabilities: list of capability descriptions needed
- desired_outputs: list
- risk_level: low | medium | high
- estimated_complexity: low | medium | high
- reusable_pattern_potential: low | medium | high`;

  const user = `User intent:
${input.intentText}

Context:
${input.context ?? "(none)"}`;

  return callLlmJson<ClassifiedIntent>(system, user, { temperature: 0.2 });
}

// ---------- Spec §7.2 — Capability matching ----------

export interface MatchedPath {
  path_summary: string;
  recommended_capabilities: string[]; // capability ids
  estimated_cost: string;
  estimated_time: string;
  proof_condition: string;
  settlement_template: string;
  why_this_path: string;
}

export async function matchCapabilities(input: {
  classifiedIntent: ClassifiedIntent;
  intentText: string;
  capabilities: Array<{
    id: string;
    name: string;
    description: string;
    capability_type: string;
    intent_types_supported: string[];
    pricing_model: string | null;
  }>;
}): Promise<{ paths: MatchedPath[] }> {
  const system = `You are the OM World Matching Engine.

Given a classified intent and a list of available capabilities, recommend 1-3 realization paths.

Return JSON only with shape:
{
  "paths": [
    {
      "path_summary": "...",
      "recommended_capabilities": ["capability_xxx", ...],
      "estimated_cost": "e.g. 10 OMC",
      "estimated_time": "e.g. 30 minutes",
      "proof_condition": "...",
      "settlement_template": "fixed_payment | milestone | bounty | success_fee | usage_based | staked_execution",
      "why_this_path": "..."
    }
  ]
}

Only reference capability ids that appear in the provided list. If no capability is a reasonable match, return paths: [].`;

  const user = `Intent (classified):
${JSON.stringify(input.classifiedIntent, null, 2)}

Original intent text:
${input.intentText}

Available capabilities:
${JSON.stringify(input.capabilities, null, 2)}`;

  return callLlmJson<{ paths: MatchedPath[] }>(system, user, { temperature: 0.3 });
}

// ---------- Spec §7.3 — Pattern generation ----------

export interface GeneratedPattern {
  pattern_name: string;
  intent_type: string;
  input_requirements: string[];
  execution_steps: string[];
  required_capabilities: string[];
  proof_condition: string;
  settlement_template: string;
  historical_notes: string;
  failure_modes: string[];
  reuse_potential: "low" | "medium" | "high";
}

export async function generatePattern(input: {
  intentText: string;
  classifiedIntent: ClassifiedIntent;
  path: MatchedPath;
  capabilitiesUsed: string[];
  outcomeSummary: string;
}): Promise<GeneratedPattern> {
  const system = `You are the OM World Pattern Builder.

Given an intent, execution path, capabilities used, and outcome, create a reusable realization pattern.

Return JSON only matching this shape:
{
  "pattern_name": "...",
  "intent_type": "...",
  "input_requirements": ["..."],
  "execution_steps": ["..."],
  "required_capabilities": ["..."],
  "proof_condition": "...",
  "settlement_template": "fixed_payment | milestone | bounty | success_fee | usage_based | staked_execution",
  "historical_notes": "...",
  "failure_modes": ["..."],
  "reuse_potential": "low | medium | high"
}`;

  const user = `Intent: ${input.intentText}

Classified: ${JSON.stringify(input.classifiedIntent)}

Execution path: ${JSON.stringify(input.path)}

Capabilities used (ids): ${JSON.stringify(input.capabilitiesUsed)}

Outcome:
${input.outcomeSummary}`;

  return callLlmJson<GeneratedPattern>(system, user, { temperature: 0.3 });
}

// ---------- Spec §9 — Genesis Builder Recruitment campaign generation ----------

export interface RecruitmentCampaign {
  project_positioning: string;
  x_article: string;
  x_thread: string[];
  dm_templates: Array<{ audience: string; message: string }>;
  github_issue_plan: Array<{ title: string; body: string }>;
  target_builder_profiles: Array<{ archetype: string; where_to_find: string; signals: string[] }>;
  follow_up_plan: string;
}

/**
 * Pattern-reuse fast path: given a previous successful campaign, adapt it to a new intent.
 * Uses a much smaller prompt + smaller max_tokens than a fresh generation, so wall time drops.
 * This is the operational realization of spec §16's success criterion: "second time should be easier".
 */
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
