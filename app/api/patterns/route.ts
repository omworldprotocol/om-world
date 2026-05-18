import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { patternId } from "@/lib/ids";

const PatternSchema = z.object({
  intent_type: z.string().min(2).max(200),
  pattern_name: z.string().min(2).max(200),
  description: z.string().max(4000).optional().nullable(),
  original_intent_id: z.string().optional().nullable(),
  execution_graph: z.unknown().optional().nullable(),
  capabilities_used: z.array(z.string()).optional().default([]),
  historical_cost: z.string().max(200).optional().nullable(),
  historical_time: z.string().max(200).optional().nullable(),
  notes: z.string().max(4000).optional().nullable(),
  reuse_potential: z.enum(["low", "medium", "high"]).optional().default("medium"),
  creator_contact: z.string().max(200).optional().nullable(),
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = PatternSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const d = parsed.data;

  const created = await db.pattern.create({
    data: {
      id: patternId(),
      creatorId: d.creator_contact ?? null,
      intentType: d.intent_type,
      patternName: d.pattern_name,
      description: d.description ?? null,
      originalIntentId: d.original_intent_id ?? null,
      executionGraphJson: d.execution_graph ? JSON.stringify(d.execution_graph) : null,
      capabilitiesUsed: d.capabilities_used.join(","),
      historicalCost: d.historical_cost ?? null,
      historicalTime: d.historical_time ?? null,
      reuseCount: 0,
      successCount: 0,
      failureCount: 0,
      notes: d.notes ?? null,
      reusePotential: d.reuse_potential,
      futureDistributedStorage: true,
      status: "active",
    },
  });

  return NextResponse.json({ pattern_id: created.id, status: "active" }, { status: 201 });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const intentType = url.searchParams.get("intent_type") ?? undefined;
  const status = url.searchParams.get("status") ?? "active";
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 50), 200);

  const rows = await db.pattern.findMany({
    where: {
      ...(intentType && { intentType }),
      ...(status && { status }),
    },
    orderBy: [{ reuseCount: "desc" }, { createdAt: "desc" }],
    take: limit,
  });

  return NextResponse.json({ patterns: rows });
}
