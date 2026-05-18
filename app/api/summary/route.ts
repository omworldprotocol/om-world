import { NextResponse } from "next/server";
import { db } from "@/lib/db";

// Always pull fresh from DB; never let Next.js prerender this at build time.
export const dynamic = "force-dynamic";

export async function GET() {
  const [
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseAgg,
    creditEvents,
  ] = await Promise.all([
    db.intent.count(),
    db.intent.count({ where: { status: "fulfilled" } }),
    db.capability.count(),
    db.pattern.count(),
    db.pattern.aggregate({ _sum: { reuseCount: true } }),
    db.creditEvent.findMany(),
  ]);

  const totalOmcIssued = creditEvents
    .filter((e) => e.amount > 0)
    .reduce((sum, e) => sum + e.amount, 0);

  const totalOmcDistributed = creditEvents
    .filter((e) => e.eventType !== "system_grant" && e.amount > 0)
    .reduce((sum, e) => sum + e.amount, 0);

  return NextResponse.json({
    total_intents: totalIntents,
    fulfilled_intents: fulfilledIntents,
    registered_capabilities: registeredCapabilities,
    patterns_created: patternsCreated,
    pattern_reuse_count: patternReuseAgg._sum.reuseCount ?? 0,
    total_omc_issued: totalOmcIssued,
    total_omc_distributed: totalOmcDistributed,
  });
}
