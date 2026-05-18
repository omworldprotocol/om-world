import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { recordEvent, type EventType } from "@/lib/credits";

const ManualEvent = z.object({
  account_id: z.string(),
  amount: z.number(),
  event_type: z.enum([
    "intent_submission_debit",
    "capability_reward",
    "pattern_creation_reward",
    "pattern_reuse_reward",
    "system_grant",
    "manual_adjustment",
  ]),
  intent_id: z.string().optional(),
  pattern_id: z.string().optional(),
  capability_id: z.string().optional(),
  execution_id: z.string().optional(),
  description: z.string().max(2000).optional(),
});

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const parsed = ManualEvent.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }

  const event = await recordEvent({
    accountId: parsed.data.account_id,
    amount: parsed.data.amount,
    eventType: parsed.data.event_type as EventType,
    intentId: parsed.data.intent_id,
    patternId: parsed.data.pattern_id,
    capabilityId: parsed.data.capability_id,
    executionId: parsed.data.execution_id,
    description: parsed.data.description,
  });

  return NextResponse.json({ event_id: event.id, status: "recorded" }, { status: 201 });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const accountId = url.searchParams.get("account_id") ?? undefined;
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 50), 200);

  const events = await db.creditEvent.findMany({
    where: { ...(accountId && { accountId }) },
    orderBy: { createdAt: "desc" },
    take: limit,
  });

  return NextResponse.json({ events });
}
