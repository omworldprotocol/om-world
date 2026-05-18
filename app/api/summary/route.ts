import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { readFrictionCurves, medianDeltaPct } from "@/lib/metrics";

// Always pull fresh from DB; never let Next.js prerender this at build time.
export const dynamic = "force-dynamic";

export async function GET() {
  const [
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseAgg,
    patternSuccessfulReuseAgg,
    creditEvents,
    curves,
    deltaMedian,
  ] = await Promise.all([
    db.intent.count(),
    db.intent.count({ where: { status: "fulfilled" } }),
    db.capability.count(),
    db.pattern.count(),
    db.pattern.aggregate({ _sum: { reuseCount: true } }),
    db.pattern.aggregate({ _sum: { successfulReuseCount: true } }),
    db.creditEvent.findMany(),
    readFrictionCurves(),
    medianDeltaPct(),
  ]);

  // Internal OMC ledger numbers — kept for accounting but framed as
  // "contribution records" in the UI, not currency. See README §OMC.
  const contributionsRecorded = creditEvents
    .filter((e) => e.amount > 0)
    .reduce((sum, e) => sum + e.amount, 0);
  const contributionsExGrants = creditEvents
    .filter((e) => e.eventType !== "system_grant" && e.amount > 0)
    .reduce((sum, e) => sum + e.amount, 0);

  return NextResponse.json({
    total_intents: totalIntents,
    fulfilled_intents: fulfilledIntents,
    registered_capabilities: registeredCapabilities,
    patterns_created: patternsCreated,
    pattern_reuse_count: patternReuseAgg._sum.reuseCount ?? 0,
    pattern_successful_reuse_count: patternSuccessfulReuseAgg._sum.successfulReuseCount ?? 0,

    // Headline self-growth metric (red-team #1). null when no pattern has
    // both a fresh and an adapted execution yet.
    self_growth: {
      median_delta_pct: deltaMedian,
      thesis_validated: deltaMedian !== null && deltaMedian < 0,
      curves,
    },

    // Internal ledger — OMC is a contribution record, not a currency.
    contributions: {
      total_recorded: contributionsRecorded,
      total_excluding_initial_grants: contributionsExGrants,
      // Kept for backward compat; will be removed once dashboards switch over.
      _legacy_total_omc_issued: contributionsRecorded,
      _legacy_total_omc_distributed: contributionsExGrants,
    },

    // Old keys kept verbatim for clients that haven't migrated yet.
    total_omc_issued: contributionsRecorded,
    total_omc_distributed: contributionsExGrants,
  });
}
