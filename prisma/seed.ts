/**
 * Seed the OM World MVP database with:
 *  - A system credit account
 *  - The first capability: Genesis Builder Recruitment Generator
 *    (registered as a Tool, provided by OM World Core)
 *
 * Run: npm run db:seed
 */
import { PrismaClient } from "@prisma/client";
import { capabilityId, accountId, creditEventId } from "../lib/ids";

const db = new PrismaClient();

async function main() {
  // 1) System account
  const sysOwnerId = "om-world-core";
  const sysAccount = await db.creditAccount.upsert({
    where: { ownerId_ownerType: { ownerId: sysOwnerId, ownerType: "system" } },
    update: {},
    create: {
      id: accountId(),
      ownerId: sysOwnerId,
      ownerType: "system",
      balance: 0,
      earned: 0,
      spent: 0,
    },
  });

  // 2) Provider account for OM World Core
  const providerOwnerId = "github.com/omworldprotocol";
  const providerAccount = await db.creditAccount.upsert({
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

  // 3) Genesis Capability: Genesis Builder Recruitment Generator
  const existing = await db.capability.findFirst({
    where: { name: "Genesis Builder Recruitment Generator" },
  });

  let capability = existing;
  if (!existing) {
    capability = await db.capability.create({
      data: {
        id: capabilityId(),
        providerId: providerOwnerId,
        providerName: "OM World Core",
        providerContact: providerOwnerId,
        capabilityType: "Tool",
        name: "Genesis Builder Recruitment Generator",
        description:
          "Generates a complete recruitment package for projects looking for early Genesis co-builders: project positioning, X article, X thread, DM templates, GitHub issue plan, target builder profiles, and follow-up plan.",
        intentTypesSupported: "community_growth.builder_recruitment",
        inputRequired: "project description, target roles, optional context",
        outputProduced:
          "project_positioning, x_article, x_thread, dm_templates, github_issue_plan, target_builder_profiles, follow_up_plan",
        pricingModel: "fixed",
        requiresLlm: true,
        requiresApi: false,
        requiresHuman: false,
        status: "active",
      },
    });
  }

  console.log("Seed complete:");
  console.log("  System account:", sysAccount.id);
  console.log("  Provider account:", providerAccount.id);
  console.log("  Genesis capability:", capability!.id, "—", capability!.name);

  // Suppress unused-warning for creditEventId; available for future seeding.
  void creditEventId;
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(async () => { await db.$disconnect(); });
