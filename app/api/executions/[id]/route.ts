import { NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const exec = await db.execution.findUnique({ where: { id: params.id } });
  if (!exec) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ execution: exec });
}
