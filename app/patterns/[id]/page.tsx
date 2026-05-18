import Link from "next/link";
import { notFound } from "next/navigation";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

const csvList = (s: string | null | undefined): string[] =>
  s ? s.split(",").map((x) => x.trim()).filter(Boolean) : [];

export default async function PatternDetailPage({ params }: { params: { id: string } }) {
  const pattern = await db.pattern.findUnique({ where: { id: params.id } });
  if (!pattern) notFound();

  const graph = pattern.executionGraphJson ? safeParse(pattern.executionGraphJson) : null;
  const capIds = csvList(pattern.capabilitiesUsed);

  // Fetch capabilities actually used (spec §4.3: "Capabilities used")
  const capabilities = capIds.length
    ? await db.capability.findMany({ where: { id: { in: capIds } } })
    : [];

  // Fetch linked executions: original + every later execution whose intent shares this pattern's intent_type
  const sameTypeIntents = await db.intent.findMany({
    where: { intentType: pattern.intentType },
    select: { id: true, intentText: true, contact: true, createdAt: true },
  });
  const intentMap = new Map(sameTypeIntents.map((i) => [i.id, i]));
  const linkedExecutions = sameTypeIntents.length
    ? await db.execution.findMany({
        where: { intentId: { in: sameTypeIntents.map((i) => i.id) } },
        orderBy: { createdAt: "asc" },
      })
    : [];

  return (
    <div className="max-w-3xl">
      <Link href="/patterns" className="text-sm underline">← All patterns</Link>
      <h1 className="mt-4 text-3xl font-semibold">{pattern.patternName}</h1>
      <p className="mt-1 text-sm text-black/60"><code>{pattern.intentType}</code></p>

      <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat k="Reuse count" v={pattern.reuseCount} />
        <Stat k="Success count" v={pattern.successCount} />
        <Stat k="Failure count" v={pattern.failureCount} />
        <Stat k="Status" v={pattern.status} />
        <Stat k="Historical cost" v={pattern.historicalCost ?? "—"} />
        <Stat k="Historical time" v={pattern.historicalTime ?? "—"} />
        <Stat k="Reuse potential" v={pattern.reusePotential ?? "—"} />
        <Stat k="Created" v={pattern.createdAt.toISOString().slice(0, 10)} />
      </dl>

      {pattern.notes && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Historical notes</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-black/80">{pattern.notes}</p>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Capabilities used</h2>
        {capabilities.length === 0 ? (
          <p className="mt-2 text-sm text-black/60">No capability links recorded.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2">
            {capabilities.map((c) => (
              <li key={c.id} className="rounded-md border border-black/10 bg-white p-3 text-sm">
                <p className="font-medium">{c.name} <span className="text-xs text-black/50">({c.capabilityType})</span></p>
                <p className="mt-1 text-xs text-black/60"><code>{c.id}</code> · {c.providerName}</p>
                <p className="mt-1 text-sm text-black/80">{c.description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Linked executions</h2>
        {linkedExecutions.length === 0 ? (
          <p className="mt-2 text-sm text-black/60">No executions yet.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2">
            {linkedExecutions.map((e, idx) => {
              const intent = intentMap.get(e.intentId);
              const trace = e.traceJson ? safeParse(e.traceJson) : null;
              const mode = (trace && typeof trace === "object" && "execution_mode" in trace ? trace.execution_mode : null) as string | null;
              const isOriginal = e.intentId === pattern.originalIntentId;
              return (
                <li key={e.id} className="rounded-md border border-black/10 bg-white p-3 text-sm">
                  <p className="font-medium">
                    Execution #{idx + 1} {isOriginal && <span className="ml-1 rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-900">original</span>}
                    {mode === "adapted" && <span className="ml-1 rounded bg-indigo-100 px-1.5 py-0.5 text-xs text-indigo-900">adapted</span>}
                    {mode === "fresh" && <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">fresh</span>}
                  </p>
                  <p className="mt-1 text-xs text-black/60">
                    <code>{e.id}</code> · {e.timeUsed ?? "—"} · {e.status}
                  </p>
                  {intent && <p className="mt-1 text-xs text-black/70">Intent: &quot;{intent.intentText.slice(0, 100)}{intent.intentText.length > 100 ? "…" : ""}&quot;</p>}
                  {e.outputText && <p className="mt-1 text-xs text-black/60">Output: {e.outputText.slice(0, 160)}{e.outputText.length > 160 ? "…" : ""}</p>}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {graph && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Execution graph</h2>
          <pre className="mt-2 overflow-auto rounded-lg border border-black/10 bg-white p-4 text-xs">
            {JSON.stringify(graph, null, 2)}
          </pre>
        </section>
      )}

      {pattern.originalIntentId && (
        <p className="mt-6 text-sm text-black/60">
          Original intent: <code>{pattern.originalIntentId}</code>
        </p>
      )}
    </div>
  );
}

function Stat({ k, v }: { k: string; v: number | string }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-3">
      <dt className="text-xs font-semibold text-black/50">{k}</dt>
      <dd className="mt-1 text-base">{v}</dd>
    </div>
  );
}

function safeParse(s: string): Record<string, unknown> | null {
  try {
    const v = JSON.parse(s);
    return typeof v === "object" && v !== null ? (v as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}
