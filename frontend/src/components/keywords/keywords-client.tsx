"use client";

import { useState, useEffect, useCallback, type FormEvent } from "react";
import {
  KeywordApiError,
  createKeyword,
  deleteKeyword,
  listKeywords,
  updateKeyword,
  type Keyword,
} from "@/lib/keywords/browser";

type ViewMode = "grid" | "list";

interface KeywordForm {
  id: string | null;
  keyword_text: string;
  match_type: "exact" | "contains" | "starts_with";
  run_flow: string | null;
  reply_text: string;
}

export function KeywordsClient() {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [search, setSearch] = useState("");
  
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [formOpen, setFormOpen] = useState(false);
  const [formState, setFormState] = useState<KeywordForm | null>(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listKeywords();
      setKeywords(data);
    } catch (err) {
      setError(err instanceof KeywordApiError ? err.message : "Could not load keywords.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreateForm = () => {
    setFormError("");
    setFormState({
      id: null,
      keyword_text: "",
      match_type: "exact",
      run_flow: null,
      reply_text: "",
    });
    setFormOpen(true);
  };

  const openEditForm = (k: Keyword) => {
    setFormError("");
    setFormState({
      id: k.id,
      keyword_text: k.keyword_text,
      match_type: k.match_type,
      run_flow: k.flow_id,
      reply_text: k.reply_text || "",
    });
    setFormOpen(true);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!formState) return;

    if (!formState.keyword_text.trim()) {
      return setFormError("Enter a keyword.");
    }

    setSaving(true);
    setFormError("");

    try {
      const payload = {
        keyword_text: formState.keyword_text,
        match_type: formState.match_type,
        flow_id: formState.run_flow,
        reply_text: formState.reply_text.trim() || null,
        is_active: true,
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

  const handleDelete = async (k: Keyword) => {
    if (!confirm(`Are you sure you want to delete the keyword "${k.keyword_text}"?`)) return;
    setWorking(true);
    try {
      await deleteKeyword(k.id);
      await load();
    } catch (err) {
      alert("Could not delete keyword.");
    } finally {
      setWorking(false);
    }
  };

  const toggleActive = async (k: Keyword) => {
    try {
      const updated = await updateKeyword(k.id, { is_active: !k.is_active });
      setKeywords(prev => prev.map(x => x.id === k.id ? updated : x));
    } catch (err) {
      alert("Could not update keyword status.");
    }
  };

  const filtered = keywords.filter(k => 
    search ? k.keyword_text.toLowerCase().includes(search.toLowerCase()) : true
  );

  return (
    <section className="page-enter">
      <header className="channel-header">
        <div className="flex items-center justify-between w-full">
          <div>
            <h1 className="page-title">Keywords</h1>
            <p className="page-subtitle mt-1">Auto-reply triggers</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center rounded-lg border border-slate-200 bg-white p-1">
              <button 
                type="button"
                className={`px-3 py-1 text-sm rounded ${viewMode === "grid" ? "bg-slate-100 font-medium" : "text-slate-600 hover:bg-slate-50"}`}
                onClick={() => setViewMode("grid")}
              >
                Grid
              </button>
              <button 
                type="button"
                className={`px-3 py-1 text-sm rounded ${viewMode === "list" ? "bg-slate-100 font-medium" : "text-slate-600 hover:bg-slate-50"}`}
                onClick={() => setViewMode("list")}
              >
                List
              </button>
            </div>
            <div className="relative">
              <span className="absolute left-3 top-2 text-slate-400">⌕</span>
              <input 
                type="text" 
                placeholder="Search keywords..." 
                className="channel-input pl-8" 
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <button type="button" className="channel-primary-btn" onClick={openCreateForm}>
              <span aria-hidden="true">+</span> Add Keyword
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="channel-state channel-state-error mt-6">
          <strong>Could not load keywords.</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="mt-6">
          {viewMode === "grid" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <button 
                type="button" 
                className="flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors h-[200px]"
                onClick={openCreateForm}
              >
                <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xl mb-3">+</div>
                <h3 className="font-semibold text-slate-800">Create new keyword</h3>
                <p className="text-sm text-slate-500 mt-1">Auto-reply when a message matches</p>
              </button>
              
              {filtered.map(k => (
                <div key={k.id} className="rounded-xl border border-slate-200 bg-white p-5 flex flex-col h-[200px] relative group">
                  <div className="flex items-start justify-between mb-2">
                    <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/><path d="m21 12-9.6 9.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L13 4"/></svg>
                    </div>
                    <div className="relative">
                      <button type="button" className="text-slate-400 hover:text-slate-700" onClick={() => openEditForm(k)}>
                        <span className="sr-only">Edit</span>
                        ⋮
                      </button>
                      <button type="button" className="absolute top-6 right-0 bg-white shadow-md border rounded text-sm px-2 py-1 text-red-600 hidden group-hover:block" onClick={() => void handleDelete(k)}>Delete</button>
                    </div>
                  </div>
                  
                  <h3 className="font-semibold text-slate-900 text-lg line-clamp-1 mt-1">{k.keyword_text}</h3>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded capitalize">{k.match_type.replace("_", " ")}</span>
                    <button type="button" onClick={() => void toggleActive(k)} className={`text-xs font-medium px-2 py-0.5 rounded flex items-center gap-1 ${k.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${k.is_active ? "bg-emerald-500" : "bg-slate-400"}`}></span>
                      {k.is_active ? "Active" : "Inactive"}
                    </button>
                  </div>
                  
                  <div className="mt-auto border-t border-slate-100 pt-3">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider block mb-1">Action:</span>
                    <span className="text-sm text-slate-700">{k.flow_id ? "Run flow" : "user messages"}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="contacts-table" role="table">
              <div className="contacts-grid contacts-head" role="row" style={{ gridTemplateColumns: "2fr 1fr 1fr 2fr 1fr" }}>
                <span role="columnheader">Keyword</span>
                <span role="columnheader">Match Type</span>
                <span role="columnheader">Status</span>
                <span role="columnheader">Action</span>
                <span role="columnheader" className="text-right">Actions</span>
              </div>
              {filtered.map(k => (
                <div key={k.id} className="contacts-grid contacts-body-row" role="row" style={{ gridTemplateColumns: "2fr 1fr 1fr 2fr 1fr" }}>
                  <span role="cell"><strong>{k.keyword_text}</strong></span>
                  <span role="cell" className="capitalize">{k.match_type.replace("_", " ")}</span>
                  <span role="cell">
                    <button type="button" onClick={() => void toggleActive(k)} className={`text-xs font-medium px-2 py-0.5 rounded inline-flex items-center gap-1 ${k.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${k.is_active ? "bg-emerald-500" : "bg-slate-400"}`}></span>
                      {k.is_active ? "Active" : "Inactive"}
                    </button>
                  </span>
                  <span role="cell" className="text-sm text-slate-600">{k.flow_id ? "Run Flow" : "Reply Text"}</span>
                  <span role="cell" className="text-right">
                    <button type="button" className="text-indigo-600 hover:underline mr-3 text-sm" onClick={() => openEditForm(k)}>Edit</button>
                    <button type="button" className="text-red-600 hover:underline text-sm" onClick={() => void handleDelete(k)} disabled={working}>Delete</button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Form Modal */}
      {formOpen && formState && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true">
          <div className="channel-modal channel-modal-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{formState.id ? "Edit keyword" : "Add keyword"}</h2>
              <button type="button" className="text-slate-400 hover:text-slate-600" onClick={() => setFormOpen(false)}>✕</button>
            </div>
            
            <form onSubmit={handleSave} className="channel-form">
              <label className="channel-field">
                <span className="font-medium text-slate-700 text-sm block mb-1">Keyword</span>
                <input 
                  type="text" 
                  value={formState.keyword_text} 
                  onChange={e => setFormState({ ...formState, keyword_text: e.target.value })} 
                  placeholder="e.g. Hello Raj" 
                  autoFocus 
                  className="channel-input w-full"
                />
              </label>
              
              <label className="channel-field mt-3">
                <span className="font-medium text-slate-700 text-sm block mb-1">Match type</span>
                <select 
                  value={formState.match_type} 
                  onChange={e => setFormState({ ...formState, match_type: e.target.value as any })}
                  className="channel-input w-full"
                >
                  <option value="exact">Exact</option>
                  <option value="contains">Contains</option>
                  <option value="starts_with">Starts with</option>
                </select>
              </label>

              <label className="channel-field mt-3">
                <span className="font-medium text-slate-700 text-sm block mb-1">Run flow (optional)</span>
                <select 
                  value={formState.run_flow || ""} 
                  onChange={e => setFormState({ ...formState, run_flow: e.target.value || null })}
                  className="channel-input w-full"
                >
                  <option value="">None</option>
                  {/* Later on: populate with automations/flows */}
                </select>
              </label>

              <label className="channel-field mt-3">
                <span className="font-medium text-slate-700 text-sm block mb-1">Or send text (optional)</span>
                <input 
                  type="text" 
                  value={formState.reply_text} 
                  onChange={e => setFormState({ ...formState, reply_text: e.target.value })} 
                  placeholder="Reply text when no flow selected" 
                  className="channel-input w-full"
                />
              </label>

              {formError && <p className="channel-form-error mt-2">{formError}</p>}
              
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" className="px-4 py-2 border rounded font-medium text-slate-700 hover:bg-slate-50" onClick={() => setFormOpen(false)} disabled={saving}>Cancel</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded font-medium hover:bg-indigo-700" disabled={saving}>{saving ? "Saving…" : (formState.id ? "Save" : "Create")}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
