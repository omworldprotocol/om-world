/**
 * Capability test runner — Phase 3.5 (red-team #6).
 *
 * Iterates capabilities, runs each one's executor against the registered
 * test_input_json, checks the output has all keys listed in expected_shape_json,
 * updates last_tested_at + test_pass_rate.
 *
 * Run: `npx tsx scripts/test_capability.ts [--id capability_xxx] [--all]`
 *
 * Without --id or --all, prints a summary of which capabilities need testing
 * (last_tested_at older than 30d) and exits.
 *
 * IMPORTANT: this calls real LLMs. Each test = one real executor invocation.
 * Don't run --all without cause.
 */

import { PrismaClient } from "@prisma/client";
import { runCapability } from "../lib/capabilities";
import type { ClassifiedIntent, MatchedPath } from "../lib/llm";

const db = new PrismaClient();
const STALENESS_DAYS = Number(process.env.OMW_CAPABILITY_STALENESS_DAYS ?? 30);
const STALE_CUTOFF = new Date(Date.now() - STALENESS_DAYS * 24 * 3600 * 1000);

interface TestInput {
  intent_text: string;
  context?: string;
  desired_output?: string;
  intent_type: string;
}

interface ExpectedShape {
  keys: string[]; // top-level keys that MUST exist in the output JSON
}

function parseArgs(): { id: string | null; all: boolean } {
  const args = process.argv.slice(2);
  let id: string | null = null;
  let all = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--id") id = args[++i];
    else if (args[i] === "--all") all = true;
  }
  return { id, all };
}

async function runOneTest(capId: string): Promise<{ pass: boolean; reason: string }> {
  const cap = await db.capability.findUnique({ where: { id: capId } });
  if (!cap) return { pass: false, reason: "capability not found" };
  if (!cap.testInputJson || !cap.expectedShapeJson) {
    return { pass: false, reason: "missing test_input_json or expected_shape_json" };
  }
  let testInput: TestInput;
  let expected: ExpectedShape;
  try {
    testInput = JSON.parse(cap.testInputJson);
    expected = JSON.parse(cap.expectedShapeJson);
  } catch (e) {
    return { pass: false, reason: `malformed JSON: ${e instanceof Error ? e.message : e}` };
  }

  // Build a synthetic ExecutorContext. We don't write anything to the DB; the
  // test is a "would the executor succeed and return output of expected shape?"
  // probe.
  const fakeIntent = {
    id: `test_${Date.now()}`,
    intentText: testInput.intent_text,
    context: testInput.context ?? null,
    desiredOutput: testInput.desired_output ?? null,
    intentType: testInput.intent_type,
    contact: "test-runner",
    originatorId: null,
    visibility: "private",
    constraintsJson: JSON.stringify({
      intent_type: testInput.intent_type,
      summary: "test invocation",
      required_capabilities: [],
      desired_outputs: [],
      risk_level: "low",
      estimated_complexity: "low",
      reusable_pattern_potential: "low",
    } satisfies ClassifiedIntent),
    status: "test",
    budget: null,
    timeline: null,
    matchedPathId: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  const matchedPath: MatchedPath = {
    path_summary: "test",
    recommended_capabilities: [capId],
    estimated_cost: "test",
    estimated_time: "test",
    proof_condition: "test",
    settlement_template: "fixed_payment",
    why_this_path: "test",
  };

  try {
    const result = await runCapability({
      intent: fakeIntent,
      classified: JSON.parse(fakeIntent.constraintsJson) as ClassifiedIntent,
      path: {
        id: "test",
        intentId: fakeIntent.id,
        recommendedCapabilities: capId,
        estimatedCost: null,
        estimatedTime: null,
        proofCondition: null,
        settlementTemplate: null,
        pathSummary: null,
        matchScore: null,
        alternativesJson: null,
        routerVersion: null,
        status: "test",
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      matchedPath,
      capabilities: [cap],
      reusable: null,
      nodeId: "test-runner",
    });

    if (result.executionMode === "placeholder") {
      return { pass: false, reason: "executor returned placeholder (no real executor registered for intent_type)" };
    }
    const output = result.output as Record<string, unknown> | null;
    if (output === null || typeof output !== "object") {
      return { pass: false, reason: "output is not an object" };
    }
    for (const key of expected.keys) {
      if (!(key in output)) {
        return { pass: false, reason: `missing required key "${key}" in output` };
      }
    }
    return { pass: true, reason: "OK" };
  } catch (e) {
    return { pass: false, reason: `executor threw: ${e instanceof Error ? e.message : String(e)}` };
  }
}

async function recordTest(capId: string, pass: boolean): Promise<void> {
  const cap = await db.capability.findUnique({ where: { id: capId } });
  if (!cap) return;
  // Rolling pass rate: weight new result 50/50 against prior.
  const priorRate = cap.testPassRate ?? (pass ? 0.0 : 1.0);
  const newRate = priorRate * 0.5 + (pass ? 0.5 : 0.0);
  await db.capability.update({
    where: { id: capId },
    data: {
      lastTestedAt: new Date(),
      testPassRate: Math.max(0, Math.min(1, newRate)),
    },
  });
}

async function main() {
  const { id, all } = parseArgs();

  if (!id && !all) {
    // Default: report which capabilities need testing.
    const caps = await db.capability.findMany({ where: { status: { in: ["submitted", "approved", "active"] } } });
    console.log(`Total capabilities: ${caps.length}`);
    for (const c of caps) {
      const stale = !c.lastTestedAt || c.lastTestedAt < STALE_CUTOFF;
      const status = stale ? "STALE" : "fresh";
      const lastTest = c.lastTestedAt ? c.lastTestedAt.toISOString() : "never";
      const hasTest = c.testInputJson ? "has-test" : "NO-TEST";
      console.log(`  ${c.id} ${status} ${hasTest} last_tested=${lastTest} pass_rate=${c.testPassRate ?? "n/a"} — ${c.name}`);
    }
    console.log(`\nRun with --id capability_xxx or --all to actually test.`);
    return;
  }

  const targets = id
    ? [await db.capability.findUnique({ where: { id } })].filter(Boolean)
    : await db.capability.findMany({ where: { status: { in: ["submitted", "approved", "active"] } } });

  for (const cap of targets) {
    if (!cap) continue;
    console.log(`\nTesting ${cap.id} — ${cap.name}`);
    const result = await runOneTest(cap.id);
    await recordTest(cap.id, result.pass);
    console.log(`  → ${result.pass ? "PASS" : "FAIL"}: ${result.reason}`);
  }
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(async () => { await db.$disconnect(); });
