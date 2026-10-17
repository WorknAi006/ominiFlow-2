"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  createAutomation, getAutomation, getAutomationOptions, updateAutomation,
  type Action, type AutomationOptions, type Condition, type MatchType,
  type ThenMode, type TriggerType,
} from "@/lib/automations/browser";

interface BuilderState {
  name: string;
  trigger_type: TriggerType;
  trigger_config: { mode?: string; hours?: number };
  match_type: MatchType;
  conditions: Condition[];
  then_mode: ThenMode;
  flow_ref: string;
  actions: Action[];
  is_active: boolean;
  runs_first: number;
}

const EMPTY: BuilderState = {
  name: "",
  trigger_type: "new_contact_created",
  trigger_config: {},
  match_type: "all",
  conditions: [],
  then_mode: "run_actions",
  flow_ref: "",
  actions: [],
  is_active: true,
  runs_first: 0,
};

export function AutomationBuilder({ id }: { id?: string }) {
  const router = useRouter();
  const [options, setOptions] = useState<AutomationOptions | null>(null);
  const [state, setState] = useState<BuilderState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const opts = await getAutomationOptions();
        setOptions(opts);
        if (id) {
          const a = await getAutomation(id);
          setState({
            name: a.name,
            trigger_type: a.trigger_type,
            trigger_config: a.trigger_config as { mode?: string; hours?: number },
            match_type: a.match_type,
            conditions: a.conditions ?? [],
            then_mode: a.then_mode,
            flow_ref: a.flow_ref ?? "",
            actions: a.actions ?? [],
            is_active: a.is_active,
            runs_first: a.runs_first,
          });
        }
        setError("");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load the builder.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  function patch(p: Partial<BuilderState>) { setState((s) => ({ ...s, ...p })); }

  function addCondition() {
    const field = options?.condition_fields[0]?.value ?? "existing_contact";
    const operator = options?.operators[0]?.value ?? "is";
    patch({ conditions: [...state.conditions, { field, operator, value: "" }] });
  }
  function setCondition(i: number, p: Partial<Condition>) {
    patch({ conditions: state.conditions.map((c, idx) => (idx === i ? { ...c, ...p } : c)) });
  }
  function removeCondition(i: number) {
    patch({ conditions: state.conditions.filter((_, idx) => idx !== i) });
  }

  function addAction() {
    const type = options?.actions[0]?.value ?? "add_tags";
    patch({ actions: [...state.actions, { type, config: {} }] });
  }
  function setActionType(i: number, type: string) {
    patch({ actions: state.actions.map((a, idx) => (idx === i ? { type, config: {} } : a)) });
  }
  function setActionConfig(i: number, key: string, value: string) {
    patch({ actions: state.actions.map((a, idx) => (idx === i ? { ...a, config: { ...a.config, [key]: value } } : a)) });
  }
  function removeAction(i: number) {
    patch({ actions: state.actions.filter((_, idx) => idx !== i) });
  }

  async function save() {
    setBusy(true);
    setError("");
    const body = {
      name: state.name.trim(),
      trigger_type: state.trigger_type,
      trigger_config: state.trigger_type === "chat_stuck_in_mode"
        ? { mode: state.trigger_config.mode || "bot", hours: Number(state.trigger_config.hours) || 1 }
        : {},
      match_type: state.match_type,
      conditions: state.conditions,
      then_mode: state.then_mode,
      flow_ref: state.then_mode === "start_flow" ? state.flow_ref || null : null,
      actions: state.then_mode === "run_actions" ? state.actions : [],
      is_active: state.is_active,
      runs_first: Number(state.runs_first) || 0,
    };
    try {
      if (id) await updateAutomation(id, body);
      else await createAutomation(body);
      router.push("/automations");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the automation.");
      setBusy(false);
    }
  }

  if (loading) return <div className="mx-auto max-w-2xl"><p className="mt-10 text-center text-sm text-slate-500">Loading…</p></div>;
  if (!options) return <div className="mx-auto max-w-2xl"><p role="alert" className="mt-10 text-center text-sm text-rose-700">{error || "Could not load the builder."}</p></div>;

  const actionOptions = options.actions;
  const selectedActionConfig = (type: string) => actionOptions.find((a) => a.value === type)?.config_fields ?? [];

  return (
    <div className="mx-auto max-w-2xl pb-16">
      <button onClick={() => router.push("/automations")} className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900">
        <span className="text-lg leading-none">←</span> {id ? "Edit automation" : "New automation"}
      </button>

      {error && <p role="alert" className="mt-4 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</p>}

      {/* Name */}
      <div className="mt-6">
        <label className="block text-sm font-medium text-slate-600">Name</label>
        <input
          value={state.name}
          onChange={(e) => patch({ name: e.target.value })}
          placeholder="e.g. Welcome new contacts"
          maxLength={150}
          className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
        />
      </div>

      {/* WHEN */}
      <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-bold text-slate-800"><span className="text-xs font-semibold uppercase tracking-wide text-slate-400">When</span> This happens</p>
        <select
          value={state.trigger_type}
          onChange={(e) => patch({ trigger_type: e.target.value as TriggerType })}
          className="mt-3 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-emerald-500"
        >
          {options.triggers.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        {state.trigger_type === "chat_stuck_in_mode" && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className="text-xs font-medium text-slate-600">Mode
              <input value={state.trigger_config.mode ?? "bot"} onChange={(e) => patch({ trigger_config: { ...state.trigger_config, mode: e.target.value } })} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs font-medium text-slate-600">Hours
              <input type="number" min={1} max={168} value={state.trigger_config.hours ?? 1} onChange={(e) => patch({ trigger_config: { ...state.trigger_config, hours: Number(e.target.value) } })} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        )}
      </section>

      {/* IF */}
      <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-bold text-slate-800"><span className="text-xs font-semibold uppercase tracking-wide text-slate-400">If</span> These conditions match</p>
        <p className="mt-1 text-xs text-slate-400">Optional — leave empty to always run</p>
        <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
          Match
          <select value={state.match_type} onChange={(e) => patch({ match_type: e.target.value as MatchType })} className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm">
            <option value="all">all</option>
            <option value="any">any</option>
          </select>
          of the conditions (optional)
        </div>
        <div className="mt-3 space-y-2">
          {state.conditions.map((c, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              <select value={c.field} onChange={(e) => setCondition(i, { field: e.target.value })} className="min-w-[9rem] flex-1 rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-emerald-700">
                {options.condition_fields.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
              <select value={c.operator} onChange={(e) => setCondition(i, { operator: e.target.value })} className="min-w-[8rem] rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm">
                {options.operators.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <input value={c.value} onChange={(e) => setCondition(i, { value: e.target.value })} placeholder="Value" className="min-w-[8rem] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <button type="button" onClick={() => removeCondition(i)} aria-label="Remove condition" className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-rose-600">🗑</button>
            </div>
          ))}
        </div>
        <button type="button" onClick={addCondition} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">+ Add condition</button>
      </section>

      {/* THEN */}
      <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-bold text-slate-800"><span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Then</span> Do this</p>
        <div className="mt-3 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button type="button" onClick={() => patch({ then_mode: "run_actions" })} className={`rounded-md px-3 py-1.5 text-sm font-semibold ${state.then_mode === "run_actions" ? "bg-slate-900 text-white" : "text-slate-600"}`}>Run actions</button>
          <button type="button" onClick={() => patch({ then_mode: "start_flow" })} className={`rounded-md px-3 py-1.5 text-sm font-semibold ${state.then_mode === "start_flow" ? "bg-slate-900 text-white" : "text-slate-600"}`}>Start a flow</button>
        </div>

        {state.then_mode === "run_actions" ? (
          <>
            <div className="mt-4 space-y-3">
              {state.actions.map((a, i) => (
                <div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-400">{i + 1}.</span>
                    <select value={a.type} onChange={(e) => setActionType(i, e.target.value)} className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                      {actionOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <button type="button" onClick={() => removeAction(i)} aria-label="Remove action" className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-rose-600">🗑</button>
                  </div>
                  {selectedActionConfig(a.type).map((cf) => (
                    <div key={cf.key} className="mt-2">
                      {cf.type === "chat_status" ? (
                        <select value={String(a.config[cf.key] ?? "")} onChange={(e) => setActionConfig(i, cf.key, e.target.value)} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                          <option value="">{cf.label}</option>
                          {options.chat_statuses.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                      ) : (
                        <input value={String(a.config[cf.key] ?? "")} onChange={(e) => setActionConfig(i, cf.key, e.target.value)} placeholder={cf.label} className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <button type="button" onClick={addAction} className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">+ Add action</button>
          </>
        ) : (
          <div className="mt-4">
            <label className="text-xs font-medium text-slate-600">Flow reference
              <input value={state.flow_ref} onChange={(e) => patch({ flow_ref: e.target.value })} placeholder="Flow name or ID" className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <p className="mt-2 text-xs text-slate-400">Flows run outside this engine; the reference is stored for routing.</p>
          </div>
        )}
      </section>

      {/* Footer */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button type="button" role="switch" aria-checked={state.is_active} onClick={() => patch({ is_active: !state.is_active })} className={`relative h-6 w-11 rounded-full transition ${state.is_active ? "bg-emerald-500" : "bg-slate-300"}`}>
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${state.is_active ? "left-[22px]" : "left-0.5"}`} />
          </button>
          <span className="text-sm font-medium text-slate-700">Active</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-500">Runs first
          <input type="number" min={0} max={9999} value={state.runs_first} onChange={(e) => patch({ runs_first: Number(e.target.value) })} className="w-20 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </label>
      </div>

      <div className="mt-6 flex items-center justify-end gap-3">
        <button type="button" onClick={() => router.push("/automations")} className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
        <button type="button" disabled={busy || !state.name.trim()} onClick={() => void save()} className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
          {busy ? "Saving…" : id ? "Save automation" : "Create automation"}
        </button>
      </div>
    </div>
  );
}
