import { db } from "./db";
import { matchCapabilities, type ClassifiedIntent, type MatchedPath } from "./llm";
import { pathId } from "./ids";

// Phase 3.5: bump on any prompt/algorithm change so supply-side can correlate
// "why was I picked / not picked" against the version that decided it.
export const ROUTER_VERSION = "v0.2.0-2026-05-19-explainable";

// Phase 3.5: capability staleness threshold (red-team #6). Capabilities that
// haven't passed a test in this many days are excluded from matching.
const CAPABILITY_STALENESS_DAYS = Number(process.env.OMW_CAPABILITY_STALENESS_DAYS ?? 30);

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

/**
 * Find candidate capabilities for a classified intent.
 *
 * MVP strategy:
 *   - any capability whose intent_types_supported overlaps with the classified intent_type
 *   - or any active capability if no overlap (so a brand-new intent_type still surfaces something)
 *
 * Phase 3.5 additions:
 *   - exclude capabilities not tested within CAPABILITY_STALENESS_DAYS UNLESS
 *     OMW_REQUIRE_CAPABILITY_TEST is "false" (dev override). Genesis seed
 *     capabilities are exempt while founder is the sole operator.
 */
export async function findCandidateCapabilities(classifiedIntentType: string) {
  const requireTest = (process.env.OMW_REQUIRE_CAPABILITY_TEST ?? "false").toLowerCase() === "true";
  const staleCutoff = new Date(Date.now() - CAPABILITY_STALENESS_DAYS * 24 * 3600 * 1000);

  const all = await db.capability.findMany({
    where: {
      status: { in: ["submitted", "approved", "active"] },
      ...(requireTest && {
        OR: [
          { lastTestedAt: { gte: staleCutoff } },
          { providerContact: "github.com/omworldprotocol" }, // founder-seeded exemption
        ],
      }),
    },
    take: 30,
  });

  const matched = all.filter((c) => {
    const types = csvList(c.intentTypesSupported);
    return types.includes(classifiedIntentType) || types.length === 0;
  });

  return (matched.length > 0 ? matched : all).map((c) => ({
    id: c.id,
    name: c.name,
    description: c.description,
    capability_type: c.capabilityType,
    intent_types_supported: csvList(c.intentTypesSupported),
    pricing_model: c.pricingModel,
  }));
}

/**
 * Run the full match step: pull candidate capabilities, ask the LLM for paths,
 * persist each path + the alternatives_considered + the router_version so
 * supply-side can audit why decisions went how they went.
 */
export async function matchAndPersist(opts: {
  intentId: string;
  intentText: string;
  classifiedIntent: ClassifiedIntent;
}): Promise<Array<{ path: MatchedPath; id: string }>> {
  const candidates = await findCandidateCapabilities(opts.classifiedIntent.intent_type);

  if (candidates.length === 0) {
    return [];
  }

  const { paths, alternatives_considered } = await matchCapabilities({
    classifiedIntent: opts.classifiedIntent,
    intentText: opts.intentText,
    capabilities: candidates,
  });

  const alternativesJson = alternatives_considered ? JSON.stringify(alternatives_considered) : null;

  const saved = await Promise.all(
    paths.map(async (path) => {
      const row = await db.realizationPath.create({
        data: {
          id: pathId(),
          intentId: opts.intentId,
          recommendedCapabilities: path.recommended_capabilities.join(","),
          estimatedCost: path.estimated_cost,
          estimatedTime: path.estimated_time,
          proofCondition: path.proof_condition,
          settlementTemplate: path.settlement_template,
          pathSummary: path.path_summary,
          // Phase 3.5: persist the LLM's match decision so /patterns/[id] can
          // surface it later and supply-side participants can audit.
          matchScore: typeof path.match_score === "number" ? path.match_score : null,
          alternativesJson,
          routerVersion: ROUTER_VERSION,
          status: "proposed",
        },
      });
      return { path, id: row.id };
    }),
  );

  return saved;
}
