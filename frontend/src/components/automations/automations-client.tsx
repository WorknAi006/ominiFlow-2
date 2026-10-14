"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  activateAutomation, deleteAutomation, listAutomations, pauseAutomation,
  type Automation, type TriggerType,
} from "@/lib/automations/browser";

const TRIGGER_LABELS: Record<TriggerType, string> = {
  new_contact_created: "New contact created",
  tag_added_to_contact: "Tag added to contact",
  chat_status_changed: "Chat status changed",
  chat_stuck_in_mode: "Chat stuck in a mode for N hours",
};

export function AutomationsClient() {
  const [items, setItems] = useState<Automation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");

  async function refresh() {
    try {
      const result = await listAutomations();
      setItems(result.items);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load automations.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void refresh(); }, []);

  async function toggle(item: Automation) {
    setBusyId(item.id);
    try {
      await (item.is_active ? pauseAutomation(item.id) : activateAutomation(item.id));
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update automation.");
    } finally {
      setBusyId("");
    }
  }
  async function remove(item: Automation) {
    if (!window.confirm(`Delete “${item.name}”? This cannot be undone.`)) return;
    setBusyId(item.id);
    try {
      await deleteAutomation(item.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete automation.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Automations</h1>
          <p className="mt-1 text-sm text-slate-500">When something happens, run actions</p>
        </div>
        <Link href="/automations/new" className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700">
          <span className="text-base leading-none">+</span> New automation
        </Link>
      </header>

      {error && <p role="alert" className="mt-5 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}

      {loading ? (
        <p className="mt-10 text-center text-sm text-slate-500">Loading automations…</p>
      ) : items.length === 0 ? (
        <div className="mt-8">
          <p className="mb-5 text-sm text-slate-500">Run actions automatically when something happens — no flow needed.</p>
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
            <svg className="h-9 w-9 text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" /></svg>
            <p className="mt-4 text-sm font-semibold text-slate-600">No automations yet</p>
            <Link href="/automations/new" className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              <span className="text-base leading-none">+</span> Create your first
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <ul className="divide-y divide-slate-100">
            {items.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
                <div className="min-w-0">
                  <Link href={`/automations/${item.id}`} className="font-semibold text-slate-900 hover:text-emerald-700">{item.name}</Link>
                  <p className="mt-0.5 truncate text-xs text-slate-500">
                    WHEN {TRIGGER_LABELS[item.trigger_type]} · {item.conditions.length} condition{item.conditions.length === 1 ? "" : "s"} · {item.actions.length} action{item.actions.length === 1 ? "" : "s"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void toggle(item)}
                    className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${item.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${item.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                    {item.is_active ? "Active" : "Paused"}
                  </button>
                  <Link href={`/automations/${item.id}`} className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">Edit</Link>
                  <button type="button" disabled={busyId === item.id} onClick={() => void remove(item)} className="text-sm text-slate-400 hover:text-rose-600">Delete</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
