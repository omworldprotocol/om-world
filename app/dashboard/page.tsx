import Link from "next/link";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

async function getSummary() {
  const [
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseAgg,
    creditEvents,
    recentIntents,
    recentPatterns,
  ] = await Promise.all([
    db.intent.count(),
    db.intent.count({ where: { status: "fulfilled" } }),
    db.capability.count(),
    db.pattern.count(),
    db.pattern.aggregate({ _sum: { reuseCount: true } }),
    db.creditEvent.findMany(),
    db.intent.findMany({ orderBy: { createdAt: "desc" }, take: 5 }),
    db.pattern.findMany({ orderBy: { createdAt: "desc" }, take: 5 }),
  ]);

  const totalOmcIssued = creditEvents.filter((e) => e.amount > 0).reduce((s, e) => s + e.amount, 0);
  const totalOmcDistributed = creditEvents
    .filter((e) => e.eventType !== "system_grant" && e.amount > 0)
    .reduce((s, e) => s + e.amount, 0);

  return {
    totalIntents,
    fulfilledIntents,
    registeredCapabilities,
    patternsCreated,
    patternReuseCount: patternReuseAgg._sum.reuseCount ?? 0,
    totalOmcIssued,
    totalOmcDistributed,
    recentIntents,
    recentPatterns,
  };
}

export default async function DashboardPage() {
  const s = await getSummary();

  return (
    <div>
      <h1 className="text-3xl font-semibold">OM World Genesis Dashboard</h1>
      <p className="mt-2 text-sm text-black/70">
        The MVP test: does pattern accumulation reduce future realization friction?
      </p>

      <section className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat k="Total intents" v={s.totalIntents} />
        <Stat k="Fulfilled intents" v={s.fulfilledIntents} />
        <Stat k="Registered capabilities" v={s.registeredCapabilities} />
        <Stat k="Patterns created" v={s.patternsCreated} />
        <Stat k="Pattern reuse count" v={s.patternReuseCount} />
        <Stat k="Total OMC issued" v={s.totalOmcIssued} />
        <Stat k="OMC distributed (excl. grants)" v={s.totalOmcDistributed} />
        <Stat k="Fulfillment rate" v={s.totalIntents ? `${Math.round((s.fulfilledIntents / s.totalIntents) * 100)}%` : "—"} />
      </section>

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
                  <code>{p.intentType}</code> · reused {p.reuseCount} · created {p.createdAt.toISOString().slice(0, 10)}
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: number | string }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-black/50">{k}</p>
      <p className="mt-2 text-2xl font-semibold">{v}</p>
    </div>
  );
}
