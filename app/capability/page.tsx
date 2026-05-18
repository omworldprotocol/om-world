"use client";

import { useState } from "react";
import Link from "next/link";

export default function CapabilityPage() {
  const [phase, setPhase] = useState<"form" | "submitted" | "error">("form");
  const [error, setError] = useState<string | null>(null);
  const [capabilityId, setCapabilityId] = useState<string | null>(null);

  const [form, setForm] = useState({
    provider_name: "",
    provider_contact: "",
    capability_type: "Tool" as "Tool" | "Agent" | "Human Service",
    name: "",
    description: "",
    intent_types_supported: "",
    input_required: "",
    output_produced: "",
    pricing_model: "free" as "free" | "fixed" | "usage_based" | "custom",
    requires_llm: false,
    requires_api: false,
    requires_human: false,
    notes: "",
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await fetch("/api/capabilities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          intent_types_supported: form.intent_types_supported
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      if (!r.ok) throw new Error((await r.json()).error ?? "Submit failed");
      const data = await r.json();
      setCapabilityId(data.capability_id);
      setPhase("submitted");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }

  if (phase === "submitted") {
    return (
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold">Your capability has joined OM World supply.</h1>
        <p className="mt-2 text-sm text-black/70">Future intents may be routed to your capability.</p>
        <p className="mt-1 text-sm text-black/60">Capability ID: <code>{capabilityId}</code></p>
        <div className="mt-6 flex gap-3">
          <Link href="/" className="rounded-md border border-ink px-4 py-2 text-sm">Home</Link>
          <Link href="/dashboard" className="rounded-md border border-ink px-4 py-2 text-sm">Dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-semibold">Contribute a Capability</h1>
      <p className="mt-2 text-black/70">Help OM World realize intentions.</p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Provider name" required>
            <input required value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} className="input" />
          </Field>
          <Field label="Provider contact (email / X / GitHub)" required>
            <input required value={form.provider_contact} onChange={(e) => setForm({ ...form, provider_contact: e.target.value })} className="input" />
          </Field>
        </div>
        <Field label="Capability type" required>
          <select value={form.capability_type} onChange={(e) => setForm({ ...form, capability_type: e.target.value as "Tool" | "Agent" | "Human Service" })} className="input">
            <option>Tool</option>
            <option>Agent</option>
            <option>Human Service</option>
          </select>
        </Field>
        <Field label="Capability name" required>
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" />
        </Field>
        <Field label="Description" required>
          <textarea required rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input" />
        </Field>
        <Field label="Intent types supported (comma separated, snake_case)">
          <input value={form.intent_types_supported} onChange={(e) => setForm({ ...form, intent_types_supported: e.target.value })} className="input" placeholder="community_growth.builder_recruitment, content.x_thread_generation" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Input required">
            <textarea rows={2} value={form.input_required} onChange={(e) => setForm({ ...form, input_required: e.target.value })} className="input" />
          </Field>
          <Field label="Output produced">
            <textarea rows={2} value={form.output_produced} onChange={(e) => setForm({ ...form, output_produced: e.target.value })} className="input" />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Pricing model">
            <select value={form.pricing_model} onChange={(e) => setForm({ ...form, pricing_model: e.target.value as "free" | "fixed" | "usage_based" | "custom" })} className="input">
              <option value="free">Free</option>
              <option value="fixed">Fixed</option>
              <option value="usage_based">Usage based</option>
              <option value="custom">Custom</option>
            </select>
          </Field>
          <div className="flex flex-col gap-2 pt-7">
            <Check label="Requires LLM" checked={form.requires_llm} onChange={(v) => setForm({ ...form, requires_llm: v })} />
            <Check label="Requires external API" checked={form.requires_api} onChange={(v) => setForm({ ...form, requires_api: v })} />
            <Check label="Requires human" checked={form.requires_human} onChange={(v) => setForm({ ...form, requires_human: v })} />
          </div>
        </div>
        <Field label="Notes">
          <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="input" />
        </Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="self-start rounded-md bg-ink px-6 py-3 text-paper hover:bg-black">Submit Capability</button>
      </form>
      <style jsx>{`
        .input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid rgba(0,0,0,0.15); border-radius: 0.375rem; background: white; }
      `}</style>
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

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}
