"use client";

import { useState } from "react";
import { CREATE_CHANNELS, flowsApi } from "@/lib/flows/browser";

export function CreateFlowModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [name, setName] = useState("");
  const [allChannels, setAllChannels] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function toggleAll(checked: boolean) {
    setAllChannels(checked);
    setSelected(checked ? CREATE_CHANNELS.map((c) => c.value) : []);
  }
  function toggleChannel(value: string, checked: boolean) {
    setAllChannels(false);
    setSelected((prev) => (checked ? [...new Set([...prev, value])] : prev.filter((v) => v !== value)));
  }

  async function create() {
    setBusy(true);
    setError("");
    try {
      const channels = allChannels ? ["omnichannel"] : selected;
      const flow = await flowsApi.create(name.trim(), channels);
      onCreated(flow.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the flow.");
      setBusy(false);
    }
  }

  const canCreate = name.trim().length > 0 && !busy;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Create New Flow</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">✕</button>
        </div>

        <label className="mt-5 block text-sm font-semibold text-slate-700">Flow Name</label>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter flow name"
          maxLength={150}
          className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />

        <p className="mt-5 text-sm font-semibold text-slate-700">Channels</p>
        <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={allChannels} onChange={(e) => toggleAll(e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
          All channels (Omnichannel)
        </label>
        <div className="mt-2 flex flex-wrap gap-x-8 gap-y-2">
          {CREATE_CHANNELS.map((c) => (
            <label key={c.value} className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={selected.includes(c.value)} onChange={(e) => toggleChannel(c.value, e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              {c.label}
            </label>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">One chatbot will be created per selected channel.</p>

        {error && <p role="alert" className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}

        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
          <button
            onClick={() => void create()}
            disabled={!canCreate}
            className={`rounded-lg px-5 py-2 text-sm font-semibold text-white transition ${canCreate ? "bg-blue-600 hover:bg-blue-700" : "cursor-not-allowed bg-blue-300"}`}
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
