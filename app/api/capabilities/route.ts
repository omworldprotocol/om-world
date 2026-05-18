import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { capabilityId } from "@/lib/ids";
import { ensureAccount } from "@/lib/credits";

const CapabilitySchema = z.object({
  provider_name: z.string().min(2).max(200),
  provider_contact: z.string().min(2).max(200),
  capability_type: z.enum(["Tool", "Agent", "Human Service"]),
  name: z.string().min(2).max(200),
  description: z.string().min(5).max(4000),
  intent_types_supported: z.array(z.string()).optional().default([]),
  input_required: z.string().max(2000).optional().nullable(),
  output_produced: z.string().max(2000).optional().nullable(),
  requires_llm: z.boolean().optional().default(false),
  requires_api: z.boolean().optional().default(false),
  requires_human: z.boolean().optional().default(false),
  pricing_model: z.enum(["free", "fixed", "usage_based", "custom"]).optional().default("free"),
  notes: z.string().max(4000).optional().nullable(),
  // Phase 3.5 (red-team #6): testability fields. Optional in v0 so existing
  // tooling doesn't break, but new public registrations are nudged hard:
  // capabilities without these are flagged "untested" in matching + UI.
  test_input: z.object({
    intent_text: z.string().min(3).max(2000),
    intent_type: z.string(),
    context: z.string().max(2000).optional(),
    desired_output: z.string().max(2000).optional(),
  }).optional(),
  expected_shape: z.object({
    keys: z.array(z.string()).min(1),
  }).optional(),
});

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = CapabilitySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const data = parsed.data;

  const created = await db.capability.create({
    data: {
      id: capabilityId(),
      providerId: data.provider_contact,
      providerName: data.provider_name,
      providerContact: data.provider_contact,
      capabilityType: data.capability_type,
      name: data.name,
      description: data.description,
      intentTypesSupported: data.intent_types_supported.join(","),
      inputRequired: data.input_required ?? null,
      outputProduced: data.output_produced ?? null,
      pricingModel: data.pricing_model,
      requiresLlm: data.requires_llm,
      requiresApi: data.requires_api,
      requiresHuman: data.requires_human,
      testInputJson: data.test_input ? JSON.stringify(data.test_input) : null,
      expectedShapeJson: data.expected_shape ? JSON.stringify(data.expected_shape) : null,
      status: "active",
    },
  });

  try {
    await ensureAccount(data.provider_contact, "provider");
  } catch (e) {
    console.error("ensureAccount for provider failed (non-fatal):", e);
  }

  return NextResponse.json({ capability_id: created.id, status: created.status }, { status: 201 });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const type = url.searchParams.get("capability_type") ?? undefined;
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 50), 200);
  const offset = Math.max(Number(url.searchParams.get("offset") ?? 0), 0);

  const rows = await db.capability.findMany({
    where: { ...(type && { capabilityType: type }) },
    orderBy: { createdAt: "desc" },
    take: limit,
    skip: offset,
  });

  return NextResponse.json({ capabilities: rows });
}
