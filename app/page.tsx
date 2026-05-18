import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-6 pt-8">
        <h1 className="text-5xl font-semibold leading-tight tracking-tight">
          One Mind, One World.
        </h1>
        <p className="max-w-2xl text-lg text-black/70">
          OM World is a self-growing intent realization network. It connects what people want with
          the capabilities that can deliver it, and turns every realization into a reusable pattern
          so the next one is easier.
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          <Link
            href="/intent"
            className="inline-flex items-center rounded-md bg-ink px-6 py-3 text-base font-medium text-paper hover:bg-black"
          >
            Submit an Intent
          </Link>
          <Link
            href="/capability"
            className="inline-flex items-center rounded-md border border-ink px-6 py-3 text-base font-medium text-ink hover:bg-ink hover:text-paper"
          >
            Contribute a Capability
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card title="Demand">
          Tell OM World what you want to realize. Your intent enters a public network of available
          capabilities.
        </Card>
        <Card title="Supply">
          Register tools, agents, or human services. Future intents may be routed to you.
        </Card>
        <Card title="Patterns">
          Each realization becomes a reusable pattern. The library is OM World&apos;s memory and its
          compounding asset.
        </Card>
      </section>

      <section className="rounded-lg border border-black/10 bg-white p-6">
        <h2 className="text-xl font-semibold">The MVP test</h2>
        <p className="mt-2 text-sm text-black/70">
          Does pattern accumulation reduce future realization friction? The Genesis MVP only proves
          one thing — that the second time you ask, it should cost less time, less thinking, and
          less OMC than the first.
        </p>
      </section>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-6">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-black/70">{children}</p>
    </div>
  );
}
