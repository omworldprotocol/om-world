import { db } from "./db";
import { matchCapabilities, type ClassifiedIntent, type MatchedPath } from "./llm";
import { pathId } from "./ids";

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

/**
 * Find candidate capabilities for a classified intent.
 * MVP strategy: any capability whose intent_types_supported overlaps with the classified intent_type,
 * or any active capability if no overlap (so a brand-new intent_type still surfaces something for the LLM).
 */
export async function findCandidateCapabilities(classifiedIntentType: string) {
  const all = await db.capability.findMany({
    where: { status: { in: ["submitted", "approved", "active"] } },
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
 * persist each path as a RealizationPath row, return the persisted records.
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

  const { paths } = await matchCapabilities({
    classifiedIntent: opts.classifiedIntent,
    intentText: opts.intentText,
    capabilities: candidates,
  });

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
          status: "proposed",
        },
      });
      return { path, id: row.id };
    }),
  );

  return saved;
}
