import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { classifyIntent } from "@/lib/llm";

export async function POST(_req: Request, { params }: { params: { id: string } }) {
  const intent = await db.intent.findUnique({ where: { id: params.id } });
  if (!intent) {
    return NextResponse.json({ error: "Intent not found" }, { status: 404 });
  }

  let classified;
  try {
    classified = await classifyIntent({ intentText: intent.intentText, context: intent.context });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: "Classification failed", message }, { status: 502 });
  }

  await db.intent.update({
    where: { id: intent.id },
    data: {
      intentType: classified.intent_type,
      status: "classified",
      constraintsJson: JSON.stringify(classified),
    },
  });

  return NextResponse.json({
    intent_id: intent.id,
    intent_type: classified.intent_type,
    classified,
  });
}
