"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { flowsApi, type FlowSummary } from "@/lib/flows/browser";
import { CreateFlowModal } from "@/components/flow/create-flow-modal";

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
}

export function FlowList() {
  const router = useRouter();
  const [items, setItems] = useState<FlowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  async function refresh() {
    try {
      const result = await flowsApi.list();
      setItems(result.items);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load flows.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void refresh(); }, []);

  const filtered = useMemo(
    () => items.filter((f) => f.name.toLowerCase().includes(search.toLowerCase())),
    [items, search],
  );
  const total = filtered.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(page, pageCount);
  const paged = filtered.slice((current - 1) * pageSize, current * pageSize);

  async function copy(id: string) {
    setBusyId(id);
    try { await flowsApi.copy(id); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not copy flow."); }
    finally { setBusyId(""); }
  }
  async function remove(f: FlowSummary) {
    if (!window.confirm(`Delete “${f.name}”? This cannot be undone.`)) return;
    setBusyId(f.id);
    try { await flowsApi.remove(f.id); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not delete flow."); }
    finally { setBusyId(""); }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Flow</h1>
          <p className="mt-1 text-sm text-slate-500">Chat flow automation</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700">
          <span className="text-base leading-none">+</span> Create Flow
        </button>
      </header>

      {error && <p role="alert" className="mt-5 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search flows..."
          className="mb-4 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
        />

        {loading ? (
          <p className="py-10 text-center text-sm text-slate-500">Loading flows…</p>
        ) : total === 0 ? (
          <div className="py-14 text-center">
            <p className="text-sm font-semibold text-slate-600">{items.length ? "No flows match your search" : "No flows yet"}</p>
            <button onClick={() => setModalOpen(true)} className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">+ Create your first flow</button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    <th className="px-3 py-3">#</th>
                    <th className="px-3 py-3">Flow name</th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">Created</th>
                    <th className="px-3 py-3">Last updated</th>
                    <th className="px-3 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paged.map((f, i) => (
                    <tr key={f.id} className="hover:bg-slate-50">
                      <td className="px-3 py-4 text-slate-400">{String((current - 1) * pageSize + i + 1).padStart(2, "0")}</td>
                      <td className="px-3 py-4">
                        <button onClick={() => router.push(`/flow/${f.id}`)} className="flex items-center gap-2 text-left">
                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600">⿻</span>
                          <span>
                            <span className="block font-semibold text-slate-900">{f.name}</span>
                            <span className="block text-xs text-slate-400">Chat Flow Configuration</span>
                          </span>
                        </button>
                      </td>
                      <td className="px-3 py-4">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${f.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${f.status === "active" ? "bg-emerald-500" : "bg-slate-400"}`} />
                          {f.status === "active" ? "Active" : "Draft"}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-slate-500">{formatDate(f.created_at)}</td>
                      <td className="px-3 py-4 text-slate-500">{formatDate(f.updated_at)}</td>
                      <td className="px-3 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={() => router.push(`/flow/${f.id}`)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100">✎ Edit</button>
                          <button disabled={busyId === f.id} onClick={() => void copy(f.id)} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100">⧉ Copy</button>
                          <button disabled={busyId === f.id} onClick={() => void remove(f)} className="inline-flex items-center gap-1 rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50">🗑 Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
              <span>Showing {(current - 1) * pageSize + 1} to {Math.min(current * pageSize, total)} of {total} results</span>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2">Rows per page:
                  <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }} className="rounded-md border border-slate-300 px-2 py-1">
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
                <button disabled={current <= 1} onClick={() => setPage(current - 1)} className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40">‹ Previous</button>
                <span className="rounded-md bg-emerald-600 px-3 py-1 font-semibold text-white">{current}</span>
                <button disabled={current >= pageCount} onClick={() => setPage(current + 1)} className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40">Next ›</button>
              </div>
            </div>
          </>
        )}
      </div>

      {modalOpen && <CreateFlowModal onClose={() => setModalOpen(false)} onCreated={(id) => router.push(`/flow/${id}`)} />}
    </div>
  );
}
