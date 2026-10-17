"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { archiveAutomation, listAutomations, type Automation } from "@/lib/automations/browser";

export function AutomationsClient() {
  const [items, setItems] = useState<Automation[]>([]), [search, setSearch] = useState(""), [status, setStatus] = useState(""), [error, setError] = useState("");
  const filtered = useMemo(() => items.filter(item => item.name.toLowerCase().includes(search.toLowerCase()) && (!status || item.status === status)), [items, search, status]);
  async function refresh() { try { const result = await listAutomations(); setItems(result.items); setError(""); } catch (e) { setError(e instanceof Error ? e.message : "Could not load automations."); } }
  useEffect(() => { listAutomations().then(result => { setItems(result.items); setError(""); }).catch(e => setError(e instanceof Error ? e.message : "Could not load automations.")); }, []);
  async function archive(item: Automation) {
    if (!window.confirm(`Archive “${item.name}”?`)) return;
    try { await archiveAutomation(item.id); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "Could not archive automation."); }
  }
  return <div className="mx-auto max-w-6xl space-y-7">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-[.16em] text-emerald-700">Workspace tools</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Automations</h1><p className="mt-2 text-slate-600">Build and monitor WhatsApp message flows.</p></div><Link href="/automations/new" className="rounded-xl bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800">Create automation</Link></header>
    {error && <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-800">{error}</p>}
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-5 flex flex-wrap gap-3"><input aria-label="Search automations" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search automations" className="min-w-60 flex-1 rounded-lg border border-slate-300 px-3 py-2"/><select aria-label="Filter by status" value={status} onChange={e => setStatus(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2"><option value="">All statuses</option>{["draft","active","paused","archived"].map(v => <option key={v} value={v}>{v}</option>)}</select></div>
      {filtered.length === 0 ? <div className="rounded-xl bg-slate-50 px-5 py-12 text-center"><p className="font-semibold">{items.length ? "No automations match these filters" : "No automations yet"}</p><p className="mt-2 text-sm text-slate-600">Create a draft to start building your first flow.</p></div> : <div className="divide-y divide-slate-100">{filtered.map(item => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 py-4"><div><Link href={`/automations/${item.id}`} className="font-semibold text-slate-900 hover:text-emerald-800">{item.name}</Link><p className="mt-1 text-sm text-slate-500">Updated {new Date(item.updated_at).toLocaleString()}</p></div><div className="flex items-center gap-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${item.status === "active" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>{item.status}</span><Link className="text-sm font-semibold text-emerald-800" href={`/automations/${item.id}`}>Open</Link>{item.status !== "archived" && <button onClick={() => void archive(item)} className="text-sm text-slate-500 hover:text-rose-700">Archive</button>}</div></article>)}</div>}</section>
  </div>;
}
