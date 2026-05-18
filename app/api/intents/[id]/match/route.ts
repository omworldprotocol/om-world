import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { classifyIntent, type ClassifiedIntent } from "@/lib/llm";
import { matchAndPersist } from "@/lib/matching";
import { findReusablePattern } from "@/lib/patterns";

export async function POST(_req: Request, { params }: { params: { id: string } }) {
  const intent = await db.intent.findUnique({ where: { id: params.id } });
  if (!intent) {
    return NextResponse.json({ error: "Intent not found" }, { status: 404 });
  }

  let classified: ClassifiedIntent;
  if (intent.intentType && intent.constraintsJson) {
    try {
      classified = JSON.parse(intent.constraintsJson) as ClassifiedIntent;
    } catch {
      classified = await classifyIntent({ intentText: intent.intentText, context: intent.context });
    }
  } else {
    classified = await classifyIntent({ intentText: intent.intentText, context: intent.context });
    await db.intent.update({
      where: { id: intent.id },
      data: {
        intentType: classified.intent_type,
        status: "classified",
        constraintsJson: JSON.stringify(classified),
      },
    });
  }

  const reusable = await findReusablePattern(classified.intent_type);

  const paths = await matchAndPersist({
    intentId: intent.id,
    intentText: intent.intentText,
    classifiedIntent: classified,
  });

  if (paths.length > 0) {
    await db.intent.update({
      where: { id: intent.id },
      data: { status: "matched", matchedPathId: paths[0].id },
    });
  }

  return NextResponse.json({
    intent_id: intent.id,
    intent_type: classified.intent_type,
    reusable_pattern: reusable
      ? {
          id: reusable.id,
          pattern_name: reusable.patternName,
          reuse_count: reusable.reuseCount,
          historical_cost: reusable.historicalCost,
          historical_time: reusable.historicalTime,
        }
      : null,
    paths: paths.map((p) => ({
      path_id: p.id,
      path_summary: p.path.path_summary,
      recommended_capabilities: p.path.recommended_capabilities,
      estimated_cost: p.path.estimated_cost,
      estimated_time: p.path.estimated_time,
      proof_condition: p.path.proof_condition,
      settlement_template: p.path.settlement_template,
      why_this_path: p.path.why_this_path,
    })),
  });
}
