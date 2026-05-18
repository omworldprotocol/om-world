import Link from "next/link";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function PatternsPage() {
  const patterns = await db.pattern.findMany({
    orderBy: [{ reuseCount: "desc" }, { createdAt: "desc" }],
    take: 100,
  });

  return (
    <div>
      <h1 className="text-3xl font-semibold">Pattern Library</h1>
      <p className="mt-2 text-black/70">
        Reusable realization patterns that make future intentions easier to realize.
      </p>

      {patterns.length === 0 && (
        <div className="mt-8 rounded-lg border border-dashed border-black/20 bg-white p-8 text-center text-sm text-black/60">
          No patterns yet. <Link href="/intent" className="underline">Submit the first intent</Link>.
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        {patterns.map((p) => (
          <Link
            href={`/patterns/${p.id}`}
            key={p.id}
            className="rounded-lg border border-black/10 bg-white p-5 hover:border-ink"
          >
            <p className="font-medium">{p.patternName}</p>
            <p className="mt-1 text-xs text-black/60"><code>{p.intentType}</code></p>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-xs text-black/70">
              <div><dt className="font-semibold text-black/50">Reuse</dt><dd>{p.reuseCount}</dd></div>
              <div><dt className="font-semibold text-black/50">Success</dt><dd>{p.successCount}</dd></div>
              <div><dt className="font-semibold text-black/50">Status</dt><dd>{p.status}</dd></div>
              <div><dt className="font-semibold text-black/50">Cost</dt><dd>{p.historicalCost ?? "—"}</dd></div>
              <div><dt className="font-semibold text-black/50">Time</dt><dd>{p.historicalTime ?? "—"}</dd></div>
              <div><dt className="font-semibold text-black/50">Reuse pot.</dt><dd>{p.reusePotential ?? "—"}</dd></div>
            </dl>
          </Link>
        ))}
      </div>
    </div>
  );
}
