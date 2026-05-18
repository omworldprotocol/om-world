import Link from "next/link";
import { db } from "@/lib/db";
import { readFrictionCurves, medianDeltaPct } from "@/lib/metrics";

export const dynamic = "force-dynamic";

async function getSummary() {
  const [
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseAgg,
    patternSuccessfulReuseAgg,
    creditEvents,
    recentIntents,
    recentPatterns,
    curves,
    deltaMedian,
  ] = await Promise.all([
    db.intent.count(),
    db.intent.count({ where: { status: "fulfilled" } }),
    db.capability.count(),
    db.pattern.count(),
    db.pattern.aggregate({ _sum: { reuseCount: true } }),
    db.pattern.aggregate({ _sum: { successfulReuseCount: true } }),
    db.creditEvent.findMany(),
    db.intent.findMany({ orderBy: { createdAt: "desc" }, take: 5 }),
    db.pattern.findMany({ orderBy: { createdAt: "desc" }, take: 5 }),
    readFrictionCurves(),
    medianDeltaPct(),
  ]);

  const contributionsRecorded = creditEvents.filter((e) => e.amount > 0).reduce((s, e) => s + e.amount, 0);

  return {
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseCount: patternReuseAgg._sum.reuseCount ?? 0,
    patternSuccessfulReuseCount: patternSuccessfulReuseAgg._sum.successfulReuseCount ?? 0,
    contributionsRecorded,
    recentIntents,
    recentPatterns,
    curves,
    deltaMedian,
  };
}

export default async function DashboardPage() {
  const s = await getSummary();
  const validCurves = s.curves.filter((c) => c.thesis_validated);

  return (
    <div>
      <h1 className="text-3xl font-semibold">OM World Genesis Dashboard</h1>
      <p className="mt-2 text-sm text-black/70">
        The single MVP test: does pattern accumulation reduce future realization friction?
      </p>

      {/* HEADLINE: self-growth metric */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white p-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Self-growth thesis</h2>
          <span className={`text-xs font-mono ${s.deltaMedian !== null && s.deltaMedian < 0 ? "text-emerald-700" : "text-black/50"}`}>
            {s.deltaMedian !== null ? (
              s.deltaMedian < 0 ? "✓ validated" : "⚠ not yet validated"
            ) : "— insufficient data"}
          </span>
        </div>
        <p className="mt-3 text-4xl font-semibold">
          {s.deltaMedian !== null ? `${s.deltaMedian > 0 ? "+" : ""}${s.deltaMedian.toFixed(1)}%` : "—"}
        </p>
        <p className="mt-1 text-xs text-black/60">
          median wall-time delta (adapted reuse vs fresh first run, across all patterns with both samples)
        </p>
        {validCurves.length > 0 && (
          <div className="mt-5 flex flex-col gap-1.5">
            {validCurves.map((c) => (
              <div key={c.intent_type} className="flex items-baseline justify-between text-sm">
                <code className="text-xs text-black/60">{c.intent_type}</code>
                <span className="flex items-baseline gap-2">
                  <span className="font-mono text-xs text-black/50">
                    {c.fresh_avg_sec?.toFixed(1)}s fresh → {c.adapted_avg_sec?.toFixed(1)}s adapted
                  </span>
                  <span className={`font-mono ${c.delta_pct! < 0 ? "text-emerald-700" : "text-amber-700"}`}>
                    {c.delta_pct! > 0 ? "+" : ""}{c.delta_pct!.toFixed(1)}%
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat k="Total intents" v={s.totalIntents} />
        <Stat k="Fulfilled intents" v={s.fulfilledIntents} />
        <Stat k="Registered capabilities" v={s.registeredCapabilities} />
        <Stat k="Patterns created" v={s.patternsCreated} />
        <Stat k="Pattern reuse (raw)" v={s.patternReuseCount} />
        <Stat k="Pattern reuse (friction-reduced)" v={s.patternSuccessfulReuseCount} />
        <Stat k="Contributions recorded (OMC)" v={s.contributionsRecorded.toFixed(2)} note="internal ledger, not a currency" />
        <Stat k="Fulfillment rate" v={s.totalIntents ? `${Math.round((s.fulfilledIntents / s.totalIntents) * 100)}%` : "—"} />
      </section>

      <p className="mt-3 text-xs text-black/50">
        OM Credit (OMC) is a non-transferable internal contribution record. Not a token. Not a currency. Not exchangeable for value, now or in any future state of the protocol. See README §OMC.
      </p>

      <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-2">
        <section>
          <h2 className="text-lg font-semibold">Recent intents</h2>
          <div className="mt-3 flex flex-col gap-2">
            {s.recentIntents.length === 0 && <p className="text-sm text-black/60">No intents yet.</p>}
            {s.recentIntents.map((i) => (
              <div key={i.id} className="rounded-md border border-black/10 bg-white p-3">
                <p className="text-sm">{i.intentText.slice(0, 120)}{i.intentText.length > 120 ? "…" : ""}</p>
                <p className="mt-1 text-xs text-black/60">
                  <code>{i.id}</code> · {i.intentType ?? "unclassified"} · {i.status}
                </p>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h2 className="text-lg font-semibold">Recent patterns</h2>
          <div className="mt-3 flex flex-col gap-2">
            {s.recentPatterns.length === 0 && <p className="text-sm text-black/60">No patterns yet.</p>}
            {s.recentPatterns.map((p) => (
              <Link href={`/patterns/${p.id}`} key={p.id} className="rounded-md border border-black/10 bg-white p-3 hover:border-ink">
                <p className="text-sm font-medium">{p.patternName}</p>
                <p className="mt-1 text-xs text-black/60">
                  <code>{p.intentType}</code> · reused {p.reuseCount} (successful {p.successfulReuseCount}) · created {p.createdAt.toISOString().slice(0, 10)}
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Stat({ k, v, note }: { k: string; v: number | string; note?: string }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-black/50">{k}</p>
      <p className="mt-2 text-2xl font-semibold">{v}</p>
      {note && <p className="mt-1 text-[10px] text-black/40">{note}</p>}
    </div>
  );
}
