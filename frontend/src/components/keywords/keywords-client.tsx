"use client";

import { useState, useEffect, useCallback, useMemo, type FormEvent } from "react";
import Link from "next/link";
import {
  KeywordApiError,
  createKeyword,
  deleteKeyword,
  listKeywords,
  updateKeyword,
  type Keyword,
  type MatchType,
} from "@/lib/keywords/browser";
import { flowsApi, type FlowSummary } from "@/lib/flows/browser";

type ViewMode = "table" | "grid";
type StatusFilter = "all" | "active" | "inactive";
type ActionFilter = "all" | "flow" | "text";

interface KeywordForm {
  id: string | null;
  keyword_text: string;
  match_type: MatchType;
  action_type: "flow" | "text";
  run_flow: string | null;
  reply_text: string;
  is_active: boolean;
}

const MATCH_TYPE_META: Record<
  MatchType,
  { label: string; symbol: string; description: string; badgeClass: string }
> = {
  exact: {
    label: "Exact Match",
    symbol: "=",
    description: "Matches inbound text exactly (case-insensitive)",
    badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  contains: {
    label: "Contains",
    symbol: "~",
    description: "Triggers if phrase appears anywhere in the message",
    badgeClass: "bg-blue-50 text-blue-700 border-blue-200",
  },
  starts_with: {
    label: "Starts With",
    symbol: "^",
    description: "Triggers if message begins with this phrase",
    badgeClass: "bg-purple-50 text-purple-700 border-purple-200",
  },
  ends_with: {
    label: "Ends With",
    symbol: "$",
    description: "Triggers if message ends with this phrase",
    badgeClass: "bg-amber-50 text-amber-700 border-amber-200",
  },
};

export function KeywordsClient() {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [matchFilter, setMatchFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<ActionFilter>("all");

  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [flowsLoading, setFlowsLoading] = useState(true);
  const [flowsError, setFlowsError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [formOpen, setFormOpen] = useState(false);
  const [formState, setFormState] = useState<KeywordForm | null>(null);
  const [flowSearch, setFlowSearch] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Keyword | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listKeywords();
      setKeywords(data);
      setError("");
    } catch (err) {
      setError(err instanceof KeywordApiError ? err.message : "Could not load keywords.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFlows = useCallback(async () => {
    setFlowsLoading(true);
    try {
      const data = await flowsApi.list();
      setFlows(data.items);
      setFlowsError("");
    } catch {
      setFlowsError("Could not load flows.");
    } finally {
      setFlowsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    void loadFlows();
  }, [load, loadFlows]);

  const flowMap = useMemo(() => {
    const map = new Map<string, FlowSummary>();
    for (const f of flows) map.set(f.id, f);
    return map;
  }, [flows]);

  const openCreateForm = () => {
    setFormError("");
    setFlowSearch("");
    setFormState({
      id: null,
      keyword_text: "",
      match_type: "exact",
      action_type: flows.length > 0 ? "flow" : "text",
      run_flow: flows.length > 0 ? flows[0].id : null,
      reply_text: "",
      is_active: true,
    });
    setFormOpen(true);
  };

  const openEditForm = (k: Keyword) => {
    setFormError("");
    setFlowSearch("");
    const isFlow = Boolean(k.flow_id);
    setFormState({
      id: k.id,
      keyword_text: k.keyword_text,
      match_type: k.match_type,
      action_type: isFlow ? "flow" : "text",
      run_flow: k.flow_id,
      reply_text: k.reply_text || "",
      is_active: k.is_active,
    });
    setFormOpen(true);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!formState) return;

    const trimmed = formState.keyword_text.trim();
    if (!trimmed) {
      return setFormError("Please enter a keyword or phrase.");
    }

    if (formState.action_type === "flow" && !formState.run_flow) {
      return setFormError("Please select a flow to trigger.");
    }

    if (formState.action_type === "text" && !formState.reply_text.trim()) {
      return setFormError("Please enter a reply message.");
    }

    setSaving(true);
    setFormError("");

    try {
      const payload = {
        keyword_text: trimmed,
        match_type: formState.match_type,
        flow_id: formState.action_type === "flow" ? formState.run_flow : null,
        reply_text: formState.action_type === "text" ? formState.reply_text.trim() : null,
        is_active: formState.is_active,
      };

      if (formState.id) {
        await updateKeyword(formState.id, payload);
      } else {
        await createKeyword(payload);
      }
      setFormOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof KeywordApiError ? err.message : "Could not save keyword.");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteKeyword(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch {
      alert("Could not delete keyword. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  const toggleActive = async (k: Keyword) => {
    const nextState = !k.is_active;
    // Optimistic update
    setKeywords((prev) => prev.map((x) => (x.id === k.id ? { ...x, is_active: nextState } : x)));
    try {
      const updated = await updateKeyword(k.id, { is_active: nextState });
      setKeywords((prev) => prev.map((x) => (x.id === k.id ? updated : x)));
    } catch {
      // Revert on failure
      setKeywords((prev) => prev.map((x) => (x.id === k.id ? { ...x, is_active: !nextState } : x)));
      alert("Could not update keyword status.");
    }
  };

  // Filtered list
  const filtered = useMemo(() => {
    return keywords.filter((k) => {
      if (search) {
        const q = search.toLowerCase();
        const matchesText = k.keyword_text.toLowerCase().includes(q);
        const matchesFlow = (k.flow_name || (k.flow_id ? flowMap.get(k.flow_id)?.name : "") || "")
          .toLowerCase()
          .includes(q);
        const matchesReply = (k.reply_text || "").toLowerCase().includes(q);
        if (!matchesText && !matchesFlow && !matchesReply) return false;
      }
      if (statusFilter === "active" && !k.is_active) return false;
      if (statusFilter === "inactive" && k.is_active) return false;
      if (matchFilter !== "all" && k.match_type !== matchFilter) return false;
      if (actionFilter === "flow" && !k.flow_id) return false;
      if (actionFilter === "text" && !k.reply_text) return false;
      return true;
    });
  }, [keywords, search, statusFilter, matchFilter, actionFilter, flowMap]);

  // Priority is assigned based on creation order (oldest first matches first deterministically in backend)
  const priorityIndexMap = useMemo(() => {
    const activeKeywordsSorted = [...keywords]
      .filter((k) => k.is_active)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const map = new Map<string, number>();
    activeKeywordsSorted.forEach((k, idx) => map.set(k.id, idx + 1));
    return map;
  }, [keywords]);

  // Statistics
  const stats = useMemo(() => {
    const total = keywords.length;
    const active = keywords.filter((k) => k.is_active).length;
    const flowTriggers = keywords.filter((k) => k.flow_id).length;
    const textReplies = keywords.filter((k) => k.reply_text && !k.flow_id).length;
    return { total, active, flowTriggers, textReplies };
  }, [keywords]);

  // Filtered flow choices for searchable select
  const filteredFlowChoices = useMemo(() => {
    if (!flowSearch.trim()) return flows;
    const q = flowSearch.toLowerCase();
    return flows.filter((f) => f.name.toLowerCase().includes(q));
  }, [flows, flowSearch]);

  return (
    <section className="page-enter max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Keyword Triggers</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Omnichannel
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Automatically trigger conversation flows or responses when customer messages match specified keywords across WhatsApp, Web Chat, Instagram, and Messenger.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#00b050] hover:bg-[#009944] text-white rounded-xl text-sm font-bold shadow-sm transition-all"
            onClick={openCreateForm}
          >
            <span className="text-lg leading-none">+</span>
            <span>New Keyword Rule</span>
          </button>
        </div>
      </header>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Rules</div>
          <div className="text-2xl font-black text-slate-900 mt-1">{stats.total}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Configured keyword triggers</div>
        </div>
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs">
          <div className="text-xs font-bold text-emerald-600 uppercase tracking-wider">Active Rules</div>
          <div className="text-2xl font-black text-emerald-700 mt-1">{stats.active}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Listening on inbound messages</div>
        </div>
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs">
          <div className="text-xs font-bold text-indigo-600 uppercase tracking-wider">Flow Automations</div>
          <div className="text-2xl font-black text-indigo-700 mt-1">{stats.flowTriggers}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Triggering interactive flows</div>
        </div>
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs">
          <div className="text-xs font-bold text-blue-600 uppercase tracking-wider">Text Replies</div>
          <div className="text-2xl font-black text-blue-700 mt-1">{stats.textReplies}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Direct message replies</div>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-3.5 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search box */}
          <div className="relative flex-1">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">⌕</span>
            <input
              type="text"
              placeholder="Search by keyword, flow name, or reply text..."
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:bg-white focus:border-[#00b050] transition"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            )}
          </div>

          {/* Filter dropdowns */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Status tabs */}
            <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200">
              {(["all", "active", "inactive"] as StatusFilter[]).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 text-xs font-bold rounded-lg capitalize transition ${
                    statusFilter === st
                      ? "bg-white text-slate-900 shadow-2xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Match Type Dropdown */}
            <select
              value={matchFilter}
              onChange={(e) => setMatchFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 outline-none focus:border-[#00b050]"
            >
              <option value="all">All Match Types</option>
              <option value="exact">Exact (=)</option>
              <option value="contains">Contains (~)</option>
              <option value="starts_with">Starts With (^)</option>
              <option value="ends_with">Ends With ($)</option>
            </select>

            {/* Action Type Dropdown */}
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value as ActionFilter)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 outline-none focus:border-[#00b050]"
            >
              <option value="all">All Actions</option>
              <option value="flow">Trigger Flow</option>
              <option value="text">Send Text</option>
            </select>

            {/* View Mode Toggle */}
            <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200 ml-auto md:ml-0">
              <button
                type="button"
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${
                  viewMode === "table" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500"
                }`}
                onClick={() => setViewMode("table")}
                title="Table view"
              >
                Table
              </button>
              <button
                type="button"
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${
                  viewMode === "grid" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500"
                }`}
                onClick={() => setViewMode("grid")}
                title="Grid view"
              >
                Cards
              </button>
            </div>
          </div>
        </div>

        {/* Priority & Conflict Resolution Banner */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 bg-slate-50/70 px-3 py-2 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-700">Deterministic Conflict Resolution:</span>
            <span>Rules are evaluated in priority sequence (oldest active first). First matching active rule triggers.</span>
          </div>
          <span className="hidden sm:inline font-semibold text-slate-400">
            Showing {filtered.length} of {keywords.length} rules
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button type="button" onClick={() => void load()} className="font-bold underline text-xs">
            Retry
          </button>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center space-y-3">
          <div className="w-8 h-8 border-3 border-[#00b050] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-600">Loading keyword triggers…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-3xl p-12 text-center max-w-md mx-auto space-y-4 my-8">
          <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center text-2xl mx-auto font-mono">
            #
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-800">
              {search || statusFilter !== "all" || matchFilter !== "all" || actionFilter !== "all"
                ? "No matching keyword rules"
                : "No keyword rules yet"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {search || statusFilter !== "all" || matchFilter !== "all" || actionFilter !== "all"
                ? "Try adjusting your search criteria or clearing active filters."
                : "Create rules to automatically route inbound messages or initiate multi-step flows."}
            </p>
          </div>
          {search || statusFilter !== "all" || matchFilter !== "all" || actionFilter !== "all" ? (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setStatusFilter("all");
                setMatchFilter("all");
                setActionFilter("all");
              }}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
            >
              Clear all filters
            </button>
          ) : (
            <button
              type="button"
              onClick={openCreateForm}
              className="px-4 py-2 bg-[#00b050] hover:bg-[#009944] text-white text-xs font-bold rounded-xl shadow-xs transition"
            >
              + Create First Keyword Rule
            </button>
          )}
        </div>
      ) : viewMode === "table" ? (
        /* TABLE VIEW */
        <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4 w-12 text-center">Pri</th>
                  <th className="py-3 px-4">Keyword / Phrase</th>
                  <th className="py-3 px-4">Match Mode</th>
                  <th className="py-3 px-4">Action & Destination</th>
                  <th className="py-3 px-4">Channels</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((k) => {
                  const meta = MATCH_TYPE_META[k.match_type] || MATCH_TYPE_META.exact;
                  const pri = priorityIndexMap.get(k.id);
                  const flow = k.flow_id ? flowMap.get(k.flow_id) : null;
                  const flowDisplayName = k.flow_name || (flow ? flow.name : null);

                  return (
                    <tr key={k.id} className="hover:bg-slate-50/60 transition-colors group">
                      {/* Priority */}
                      <td className="py-3.5 px-4 text-center">
                        {k.is_active && pri !== undefined ? (
                          <span
                            className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200"
                            title={`Priority #${pri}: Evaluated in deterministic creation order`}
                          >
                            #{pri}
                          </span>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>

                      {/* Keyword Phrase */}
                      <td className="py-3.5 px-4 font-semibold text-slate-900">
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-1 bg-slate-100/90 rounded-lg font-mono text-xs text-slate-800 border border-slate-200/80">
                            &ldquo;{k.keyword_text}&rdquo;
                          </span>
                        </div>
                      </td>

                      {/* Match Type */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${meta.badgeClass}`}
                          title={meta.description}
                        >
                          <span className="font-mono font-bold">{meta.symbol}</span>
                          <span>{meta.label}</span>
                        </span>
                      </td>

                      {/* Action & Destination */}
                      <td className="py-3.5 px-4">
                        {k.flow_id ? (
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-md bg-indigo-50 text-indigo-600 flex items-center justify-center text-xs font-bold shrink-0">
                              ▶
                            </span>
                            <div className="min-w-0">
                              <div className="font-semibold text-slate-800 truncate text-xs">
                                {flowDisplayName || "Attached Flow"}
                              </div>
                              <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                <span>Automation Flow</span>
                                {flow?.status && (
                                  <span className="uppercase text-[9px] font-bold text-slate-400">
                                    ({flow.status})
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        ) : k.reply_text ? (
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                              ↩
                            </span>
                            <div className="min-w-0 max-w-xs">
                              <div className="text-xs text-slate-700 truncate font-medium">
                                {k.reply_text}
                              </div>
                              <span className="text-[10px] text-slate-400">Quick Text Reply</span>
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">No action configured</span>
                        )}
                      </td>

                      {/* Channels */}
                      <td className="py-3.5 px-4">
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 border border-slate-200 rounded-md text-[11px] text-slate-600 font-medium"
                          title="WhatsApp, Web Chat, Instagram, Messenger"
                        >
                          <span>🌐</span>
                          <span>All Channels</span>
                        </span>
                      </td>

                      {/* Status Toggle */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => void toggleActive(k)}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold transition ${
                            k.is_active
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                              : "bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              k.is_active ? "bg-emerald-500" : "bg-slate-400"
                            }`}
                          />
                          <span>{k.is_active ? "Active" : "Inactive"}</span>
                        </button>
                      </td>

                      {/* Action buttons */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => openEditForm(k)}
                            className="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(k)}
                            className="p-1 text-xs text-slate-400 hover:text-rose-600 rounded-lg transition"
                            title="Delete rule"
                          >
                            🗑
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* GRID / CARDS VIEW */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Create new card */}
          <button
            type="button"
            className="flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/60 hover:bg-slate-100/80 transition min-h-[220px] text-center group cursor-pointer"
            onClick={openCreateForm}
          >
            <div className="w-11 h-11 rounded-2xl bg-[#00b050] text-white flex items-center justify-center text-2xl font-bold mb-3 shadow-sm group-hover:scale-105 transition-transform">
              +
            </div>
            <h3 className="font-bold text-slate-800 text-sm">Add Keyword Trigger</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-[200px]">
              Trigger automation flows or responses on inbound customer messages
            </p>
          </button>

          {filtered.map((k) => {
            const meta = MATCH_TYPE_META[k.match_type] || MATCH_TYPE_META.exact;
            const pri = priorityIndexMap.get(k.id);
            const flow = k.flow_id ? flowMap.get(k.flow_id) : null;
            const flowDisplayName = k.flow_name || (flow ? flow.name : null);

            return (
              <div
                key={k.id}
                className="bg-white border border-slate-200/90 rounded-2xl p-5 flex flex-col justify-between shadow-2xs hover:shadow-xs transition relative group min-h-[220px]"
              >
                {/* Card Header */}
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-1.5">
                      {k.is_active && pri !== undefined && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200">
                          #{pri}
                        </span>
                      )}
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${meta.badgeClass}`}
                      >
                        <span className="font-mono">{meta.symbol}</span>
                        <span>{meta.label}</span>
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditForm(k)}
                        className="p-1 text-slate-400 hover:text-slate-700 text-xs rounded"
                        title="Edit"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(k)}
                        className="p-1 text-slate-400 hover:text-rose-600 text-xs rounded"
                        title="Delete"
                      >
                        🗑
                      </button>
                    </div>
                  </div>

                  <h3 className="font-bold text-slate-900 text-base leading-snug break-words">
                    &ldquo;{k.keyword_text}&rdquo;
                  </h3>
                </div>

                {/* Card Action Destination */}
                <div className="my-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                    Action Destination
                  </div>
                  {k.flow_id ? (
                    <div className="flex items-center gap-2">
                      <span className="text-indigo-600 font-bold text-xs">▶</span>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-slate-800 truncate">
                          {flowDisplayName || "Automation Flow"}
                        </div>
                        <div className="text-[10px] text-slate-400">Trigger multi-step flow</div>
                      </div>
                    </div>
                  ) : k.reply_text ? (
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600 font-bold text-xs">↩</span>
                      <div className="text-xs text-slate-700 font-medium line-clamp-2">
                        {k.reply_text}
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 italic">None</div>
                  )}
                </div>

                {/* Card Footer */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <span>🌐</span> All Channels
                  </span>

                  <button
                    type="button"
                    onClick={() => void toggleActive(k)}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold transition ${
                      k.is_active
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-slate-100 text-slate-500 border border-slate-200"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        k.is_active ? "bg-emerald-500" : "bg-slate-400"
                      }`}
                    />
                    <span>{k.is_active ? "Active" : "Inactive"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE / EDIT MODAL */}
      {formOpen && formState && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white border border-slate-200 rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-slate-900">
                  {formState.id ? "Edit Keyword Rule" : "Create Keyword Rule"}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Configure an automated inbound trigger for omnichannel messaging
                </p>
              </div>
              <button
                type="button"
                className="w-8 h-8 rounded-full bg-slate-100 text-slate-400 hover:text-slate-600 flex items-center justify-center text-sm font-bold transition"
                onClick={() => setFormOpen(false)}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSave} className="p-6 space-y-5 overflow-y-auto flex-1">
              {/* Keyword Text Field */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Keyword / Trigger Phrase <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formState.keyword_text}
                  onChange={(e) => setFormState({ ...formState, keyword_text: e.target.value })}
                  placeholder="e.g. Order Status, Support, Hi, Pricing"
                  autoFocus
                  maxLength={255}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 outline-none focus:bg-white focus:border-[#00b050] transition"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Matching is case-insensitive. Extra whitespace is automatically trimmed.
                </p>
              </div>

              {/* Match Type Selection */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Matching Mode <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(["exact", "contains", "starts_with", "ends_with"] as MatchType[]).map((mt) => {
                    const meta = MATCH_TYPE_META[mt];
                    const selected = formState.match_type === mt;
                    return (
                      <button
                        key={mt}
                        type="button"
                        onClick={() => setFormState({ ...formState, match_type: mt })}
                        className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                          selected
                            ? "bg-emerald-50/50 border-[#00b050] ring-1 ring-[#00b050]"
                            : "bg-white border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-xs text-slate-900">{meta.label}</span>
                          <span className="font-mono text-xs font-bold text-slate-400">
                            {meta.symbol}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 leading-tight">
                          {meta.description}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Type Selection */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Action Type <span className="text-rose-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setFormState({ ...formState, action_type: "flow" })}
                    className={`p-3 rounded-xl border text-left transition ${
                      formState.action_type === "flow"
                        ? "bg-indigo-50/50 border-indigo-600 ring-1 ring-indigo-600"
                        : "bg-white border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold text-xs text-indigo-700 mb-0.5">
                      <span>▶</span> Trigger Automation Flow
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Launch an interactive flow builder conversation
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setFormState({ ...formState, action_type: "text" })}
                    className={`p-3 rounded-xl border text-left transition ${
                      formState.action_type === "text"
                        ? "bg-blue-50/50 border-blue-600 ring-1 ring-blue-600"
                        : "bg-white border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold text-xs text-blue-700 mb-0.5">
                      <span>↩</span> Quick Text Reply
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Send an immediate single text message
                    </p>
                  </button>
                </div>
              </div>

              {/* Target Flow Selection (When Action is Flow) */}
              {formState.action_type === "flow" && (
                <div className="bg-slate-50/80 p-3.5 rounded-2xl border border-slate-200 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Select Flow to Execute
                    </label>
                    <Link
                      href="/flow"
                      target="_blank"
                      className="text-[11px] font-bold text-indigo-600 hover:underline flex items-center gap-0.5"
                    >
                      <span>Open Flow Builder</span>
                      <span>↗</span>
                    </Link>
                  </div>

                  {flowsLoading ? (
                    <div className="text-xs text-slate-400 py-2">Loading tenant flows…</div>
                  ) : flows.length === 0 ? (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
                      No visual flows found. Please create a flow in the Flow Builder first.
                    </div>
                  ) : (
                    <div>
                      {flows.length > 5 && (
                        <input
                          type="text"
                          placeholder="Filter flows by name…"
                          value={flowSearch}
                          onChange={(e) => setFlowSearch(e.target.value)}
                          className="w-full px-3 py-1.5 mb-2 bg-white border border-slate-200 rounded-lg text-xs"
                        />
                      )}
                      <select
                        value={formState.run_flow || ""}
                        onChange={(e) =>
                          setFormState({ ...formState, run_flow: e.target.value || null })
                        }
                        className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 outline-none focus:border-indigo-600"
                      >
                        <option value="">— Choose a flow —</option>
                        {filteredFlowChoices.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name} ({f.status === "active" ? "Published" : "Draft"})
                          </option>
                        ))}
                      </select>
                      {formState.run_flow && (
                        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-emerald-700 font-medium">
                          <span>✓</span>
                          <span>
                            Selected: {flows.find((f) => f.id === formState.run_flow)?.name}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  {flowsError && <p className="text-xs text-rose-600">{flowsError}</p>}
                </div>
              )}

              {/* Reply Text Field (When Action is Text) */}
              {formState.action_type === "text" && (
                <div className="bg-slate-50/80 p-3.5 rounded-2xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Auto-Reply Message Text
                    </label>
                    <span className="text-[10px] text-slate-400 font-semibold">
                      {formState.reply_text.length}/4096
                    </span>
                  </div>
                  <textarea
                    rows={3}
                    maxLength={4096}
                    value={formState.reply_text}
                    onChange={(e) => setFormState({ ...formState, reply_text: e.target.value })}
                    placeholder="Enter message to send automatically when keyword is triggered..."
                    className="w-full p-3 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-blue-600 resize-none"
                  />
                </div>
              )}

              {/* Channel Scope Note */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5 text-xs text-slate-600">
                <span className="text-base leading-none">🌐</span>
                <div className="leading-relaxed">
                  <strong className="text-slate-800">Channel Applicability:</strong> Inbound messages across WhatsApp, Web Chat, Instagram, and Facebook Messenger evaluate this rule deterministically.
                </div>
              </div>

              {/* Active Toggle */}
              <label className="flex items-center gap-3 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={formState.is_active}
                  onChange={(e) => setFormState({ ...formState, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-300 text-[#00b050] focus:ring-[#00b050]"
                />
                <div>
                  <span className="block text-xs font-bold text-slate-800">Active Rule</span>
                  <span className="text-[11px] text-slate-500">
                    Rule will evaluate immediately on newly received inbound customer messages
                  </span>
                </div>
              </label>

              {formError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
                  {formError}
                </div>
              )}

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
                  onClick={() => setFormOpen(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#00b050] hover:bg-[#009944] text-white rounded-xl text-xs font-bold shadow-xs transition disabled:opacity-50"
                  disabled={saving}
                >
                  {saving ? "Saving…" : formState.id ? "Save Changes" : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-2xl max-w-sm w-full space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-10 h-10 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center text-lg mx-auto font-bold">
              🗑
            </div>
            <div className="text-center">
              <h3 className="font-black text-slate-900 text-base">Delete Keyword Rule?</h3>
              <p className="text-xs text-slate-500 mt-1">
                Are you sure you want to delete the trigger for &ldquo;
                <strong className="text-slate-800">{deleteTarget.keyword_text}</strong>&rdquo;? Inbound messages matching this keyword will no longer trigger this rule.
              </p>
            </div>
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                type="button"
                className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition disabled:opacity-50"
                onClick={() => void confirmDelete()}
                disabled={deleting}
              >
                {deleting ? "Deleting…" : "Yes, Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
