"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createAutomation } from "@/lib/automations/browser";

export function NewAutomation() {
  const router = useRouter();
  const [name, setName] = useState(""), [description, setDescription] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { const automation = await createAutomation({ name, description: description || undefined }); router.replace(`/automations/${automation.id}`); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create the draft."); setBusy(false); }
  }
  return <div className="mx-auto max-w-2xl"><Link href="/automations" className="text-sm font-semibold text-emerald-800">← Automations</Link><h1 className="mt-4 text-3xl font-bold">Create automation</h1><p className="mt-2 text-slate-600">Start with an inbound WhatsApp message trigger, then add conditions and actions.</p><form onSubmit={submit} className="mt-6 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><label className="block text-sm font-semibold">Name<input required maxLength={150} value={name} onChange={e=>setName(e.target.value)} className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" /></label><label className="block text-sm font-semibold">Description<textarea maxLength={2000} value={description} onChange={e=>setDescription(e.target.value)} rows={3} className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" /></label>{error&&<p role="alert" className="text-sm text-rose-700">{error}</p>}<button disabled={busy||!name.trim()} className="rounded-lg bg-emerald-700 px-4 py-2 font-semibold text-white disabled:opacity-60">{busy?"Creating…":"Create draft"}</button></form></div>;
}
