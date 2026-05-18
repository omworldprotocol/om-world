import { NextResponse } from "next/server";
import { z } from "zod";
import { db } from "@/lib/db";
import { intentId } from "@/lib/ids";
import { chargeIntentSubmission } from "@/lib/credits";

const IntentSchema = z.object({
  intent_text: z.string().min(3).max(4000),
  context: z.string().max(4000).optional().nullable(),
  desired_output: z.string().max(2000).optional().nullable(),
  budget: z.string().max(200).optional().nullable(),
  timeline: z.string().max(200).optional().nullable(),
  contact: z.string().min(2).max(200),
  visibility: z.enum(["public", "private"]).optional().default("public"),
});

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const parsed = IntentSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input", details: parsed.error.format() }, { status: 400 });
  }
  const data = parsed.data;

  const created = await db.intent.create({
    data: {
      id: intentId(),
      intentText: data.intent_text,
      context: data.context ?? null,
      desiredOutput: data.desired_output ?? null,
      budget: data.budget ?? null,
      timeline: data.timeline ?? null,
      contact: data.contact,
      visibility: data.visibility,
      originatorId: data.contact,
      status: "submitted",
    },
  });

  try {
    await chargeIntentSubmission({ userContact: data.contact, intentId: created.id });
  } catch (e) {
    console.error("OMC debit failed (non-fatal in MVP):", e);
  }

  return NextResponse.json({ intent_id: created.id, status: created.status }, { status: 201 });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const status = url.searchParams.get("status") ?? undefined;
  const intentType = url.searchParams.get("intent_type") ?? undefined;
  const limit = Math.min(Number(url.searchParams.get("limit") ?? 50), 200);
  const offset = Math.max(Number(url.searchParams.get("offset") ?? 0), 0);

  const rows = await db.intent.findMany({
    where: {
      ...(status && { status }),
      ...(intentType && { intentType }),
      visibility: "public",
    },
    orderBy: { createdAt: "desc" },
    take: limit,
    skip: offset,
  });

  return NextResponse.json({ intents: rows });
}
