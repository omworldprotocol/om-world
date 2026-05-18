import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const intent = await db.intent.findUnique({ where: { id: params.id } });
  if (!intent) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const paths = await db.realizationPath.findMany({
    where: { intentId: intent.id },
    orderBy: { createdAt: "asc" },
  });
  const executions = await db.execution.findMany({
    where: { intentId: intent.id },
    orderBy: { createdAt: "asc" },
  });

  return NextResponse.json({ intent, paths, executions });
}
