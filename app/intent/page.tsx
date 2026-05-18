"use client";

import { useState } from "react";
import Link from "next/link";

type Phase = "form" | "submitted" | "classified" | "matched" | "executed" | "error";

interface PathView {
  path_id: string;
  path_summary: string;
  recommended_capabilities: string[];
  estimated_cost: string;
  estimated_time: string;
  proof_condition: string;
  settlement_template: string;
  why_this_path: string;
}

export default function IntentPage() {
  const [phase, setPhase] = useState<Phase>("form");
  const [error, setError] = useState<string | null>(null);
  const [intentId, setIntentId] = useState<string | null>(null);
  const [intentType, setIntentType] = useState<string | null>(null);
  const [reusable, setReusable] = useState<{ id: string; pattern_name: string; reuse_count: number } | null>(null);
  const [paths, setPaths] = useState<PathView[]>([]);
  const [executionResult, setExecutionResult] = useState<{ execution_id: string; output_text: string; pattern_event: { pattern_id: string; action: string } | null } | null>(null);

  const [form, setForm] = useState({
    intent_text: "",
    context: "",
    desired_output: "",
    budget: "",
    timeline: "",
    contact: "",
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await fetch("/api/intents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error((await r.json()).error ?? "Submit failed");
      const data = await r.json();
      setIntentId(data.intent_id);
      setPhase("submitted");

      // Auto-trigger match (which also classifies if needed).
      const match = await fetch(`/api/intents/${data.intent_id}/match`, { method: "POST" });
      if (!match.ok) throw new Error((await match.json()).error ?? "Match failed");
      const m = await match.json();
      setIntentType(m.intent_type);
      setReusable(m.reusable_pattern);
      setPaths(m.paths);
      setPhase("matched");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }

  async function execute(path: PathView) {
    if (!intentId) return;
    setPhase("executed");
    setError(null);
    try {
      const r = await fetch("/api/executions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          intent_id: intentId,
          path_id: path.path_id,
          capability_ids: path.recommended_capabilities,
        }),
      });
      if (!r.ok) throw new Error((await r.json()).error ?? "Execution failed");
      const data = await r.json();
      setExecutionResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }

  if (phase === "form" || phase === "submitted") {
    return (
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold">Submit an Intent</h1>
        <p className="mt-2 text-black/70">Tell OM World what you want to realize.</p>
        <form onSubmit={submit} className="mt-8 flex flex-col gap-5">
          <Field label="What do you want to realize?" required>
            <textarea
              required
              rows={3}
              value={form.intent_text}
              onChange={(e) => setForm({ ...form, intent_text: e.target.value })}
              placeholder="I want to recruit 5 Genesis co-builders for my project."
              className="input"
            />
          </Field>
          <Field label="Context">
            <textarea
              rows={2}
              value={form.context}
              onChange={(e) => setForm({ ...form, context: e.target.value })}
              className="input"
            />
          </Field>
          <Field label="Desired output">
            <textarea
              rows={2}
              value={form.desired_output}
              onChange={(e) => setForm({ ...form, desired_output: e.target.value })}
              className="input"
            />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Budget (optional)">
              <input value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} className="input" />
            </Field>
            <Field label="Timeline (optional)">
              <input value={form.timeline} onChange={(e) => setForm({ ...form, timeline: e.target.value })} className="input" />
            </Field>
          </div>
          <Field label="Contact (email / X / GitHub)" required>
            <input
              required
              value={form.contact}
              onChange={(e) => setForm({ ...form, contact: e.target.value })}
              placeholder="@your_handle"
              className="input"
            />
          </Field>
          <button
            type="submit"
            disabled={phase === "submitted"}
            className="self-start rounded-md bg-ink px-6 py-3 text-paper hover:bg-black disabled:opacity-50"
          >
            {phase === "submitted" ? "Classifying and matching…" : "Submit Intent"}
          </button>
        </form>
        <style jsx>{`
          .input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid rgba(0,0,0,0.15); border-radius: 0.375rem; background: white; }
        `}</style>
      </div>
    );
  }

  if (phase === "matched" || phase === "executed") {
    return (
      <div className="max-w-3xl">
        <h1 className="text-3xl font-semibold">Your intent has entered OM World.</h1>
        <p className="mt-2 text-sm text-black/60">Intent ID: <code>{intentId}</code></p>
        <p className="mt-1 text-sm text-black/60">Classified as: <code>{intentType}</code></p>

        {reusable && (
          <div className="mt-6 rounded-lg border border-emerald-300 bg-emerald-50 p-4">
            <p className="text-sm font-semibold text-emerald-900">Reusable pattern found</p>
            <p className="mt-1 text-sm text-emerald-900">
              <Link href={`/patterns/${reusable.id}`} className="underline">{reusable.pattern_name}</Link> ·
              {" "}reused {reusable.reuse_count} time{reusable.reuse_count === 1 ? "" : "s"}
            </p>
            <p className="mt-1 text-xs text-emerald-800">This intent type has been realized before — OM World may execute it cheaper / faster than the first time.</p>
          </div>
        )}

        <h2 className="mt-8 text-xl font-semibold">Recommended realization paths</h2>
        {paths.length === 0 && (
          <p className="mt-2 text-sm text-black/70">No matching capabilities yet. <Link href="/capability" className="underline">Contribute one</Link>.</p>
        )}
        <div className="mt-4 flex flex-col gap-4">
          {paths.map((p) => (
            <div key={p.path_id} className="rounded-lg border border-black/10 bg-white p-5">
              <p className="font-medium">{p.path_summary}</p>
              <p className="mt-2 text-xs text-black/60">{p.why_this_path}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-black/70 sm:grid-cols-4">
                <Item k="Cost" v={p.estimated_cost} />
                <Item k="Time" v={p.estimated_time} />
                <Item k="Settlement" v={p.settlement_template} />
                <Item k="Capabilities" v={String(p.recommended_capabilities.length)} />
              </dl>
              <button
                onClick={() => execute(p)}
                disabled={phase === "executed"}
                className="mt-4 rounded-md bg-ink px-4 py-2 text-sm text-paper hover:bg-black disabled:opacity-50"
              >
                {phase === "executed" ? "Executing…" : "Execute this path"}
              </button>
            </div>
          ))}
        </div>

        {executionResult && (
          <div className="mt-8 rounded-lg border border-black/20 bg-white p-5">
            <p className="font-semibold">Execution complete.</p>
            <p className="mt-1 text-sm text-black/70">Execution ID: <code>{executionResult.execution_id}</code></p>
            <p className="mt-1 text-sm text-black/70">{executionResult.output_text}</p>
            {executionResult.pattern_event && (
              <p className="mt-2 text-sm">
                Pattern <code>{executionResult.pattern_event.pattern_id}</code> was{" "}
                <strong>{executionResult.pattern_event.action}</strong>.{" "}
                <Link href={`/patterns/${executionResult.pattern_event.pattern_id}`} className="underline">View pattern</Link>
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="mt-2 text-sm text-red-600">{error}</p>
      <button onClick={() => { setPhase("form"); setError(null); }} className="mt-4 underline">Start over</button>
    </div>
  );
}

function Field({ label, children, required }: { label: string; children: React.ReactNode; required?: boolean }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}{required && <span className="text-red-500"> *</span>}</span>
      {children}
    </label>
  );
}

function Item({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="font-semibold text-black/50">{k}</dt>
      <dd>{v || "—"}</dd>
    </div>
  );
}
