/**
 * Seed the `research.cite_synthesis` capability row.
 *
 * Idempotent — safe to re-run; skips creation if a capability with the same
 * name already exists. Run locally: `npx tsx scripts/seed_research_capability.ts`
 * On the server: `cd /root/om-world && npx tsx scripts/seed_research_capability.ts`
 */
import { PrismaClient } from "@prisma/client";
import { capabilityId, accountId } from "../lib/ids";

const db = new PrismaClient();

async function main() {
  const providerOwnerId = "github.com/omworldprotocol";

  // Ensure provider account exists (idempotent with the genesis seed).
  await db.creditAccount.upsert({
    where: { ownerId_ownerType: { ownerId: providerOwnerId, ownerType: "provider" } },
    update: {},
    create: {
      id: accountId(),
      ownerId: providerOwnerId,
      ownerType: "provider",
      balance: 0,
      earned: 0,
      spent: 0,
    },
  });

  const existing = await db.capability.findFirst({
    where: { name: "Research Brief Synthesizer" },
  });

  if (existing) {
    console.log(`Capability already seeded: ${existing.id} (${existing.name})`);
    return;
  }

  const cap = await db.capability.create({
    data: {
      id: capabilityId(),
      providerId: providerOwnerId,
      providerName: "OM World Core",
      providerContact: providerOwnerId,
      capabilityType: "Tool",
      name: "Research Brief Synthesizer",
      description:
        "Decomposes a research topic into focused web search queries (DuckDuckGo via OpenClaw), retrieves cited results, and synthesizes a 400-800 word brief with inline [n] citations + a Caveats section. Honest about uncertainty; does not paper over disagreement between sources.",
      intentTypesSupported: "research.cite_synthesis",
      inputRequired: "research topic (intent text); optional framing context",
      outputProduced:
        "brief_markdown, claims (with source URLs), bibliography (title+url+snippet per hit), queries_used, source_count, caveat",
      pricingModel: "fixed",
      requiresLlm: true,
      requiresApi: false,
      requiresHuman: false,
      // Phase 3.5 capability testability.
      testInputJson: JSON.stringify({
        intent_text: "Research the state of intent realization networks.",
        intent_type: "research.cite_synthesis",
        context: "Test invocation; web search may fall back to unsourced brief.",
      }),
      expectedShapeJson: JSON.stringify({
        keys: ["brief_markdown", "claims", "bibliography", "queries_used", "source_count", "caveat"],
      }),
      status: "active",
    },
  });

  console.log(`Seeded capability: ${cap.id} (${cap.name})`);
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(async () => { await db.$disconnect(); });
