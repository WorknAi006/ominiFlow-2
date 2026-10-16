"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCreditBalance } from "@/lib/credits/use-credit-balance";
import { AiTemplateModal, AI_TEMPLATE_DRAFT_KEY } from "@/components/templates/ai-template-modal";
import { PlatformTemplateLibrary } from "@/components/templates/platform-template-library";

import {
  TemplateApiError,
  getTemplate,
  listTemplates,
  syncTemplates,
  type AiTemplateDraft,
  type MessageTemplate,
} from "@/lib/templates/browser";
import { listChannels, type ChannelConnection } from "@/lib/channels/browser";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = ["approved", "pending", "rejected", "paused", "disabled"] as const;
const CATEGORY_OPTIONS = ["marketing", "utility", "authentication"] as const;
const PLACEHOLDER_RE = /\{\{\s*([a-z0-9_]+)\s*\}\}/gi;

type Notice = { kind: "success" | "error"; text: string } | null;

const STATUS_TONE: Record<string, string> = {
  approved: "channel-pill-ok",
  pending: "channel-pill-warn",
  rejected: "channel-pill-bad",
  paused: "channel-pill-muted",
  disabled: "channel-pill-muted",
};

function titleCase(value: string | null | undefined) {
  if (!value) return "—";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
}

// Render text with {{placeholders}} visually highlighted.
function renderWithPlaceholders(text: string): ReactNode {
  const parts: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(PLACEHOLDER_RE);
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(<Fragment key={last}>{text.slice(last, match.index)}</Fragment>);
    parts.push(<mark className="tpl-var" key={`${match.index}-v`}>{match[0]}</mark>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(<Fragment key={last}>{text.slice(last)}</Fragment>);
  return parts;
}

function uniquePlaceholders(template: MessageTemplate): string[] {
  const found = new Set<string>();
  for (const component of template.components) {
    const text = typeof component.text === "string" ? component.text : "";
    for (const m of text.matchAll(PLACEHOLDER_RE)) found.add(m[1]);
  }
  return [...found];
}

interface Part { header?: Record<string, unknown>; body?: Record<string, unknown>; footer?: Record<string, unknown>; buttons: Record<string, unknown>[]; }

function splitComponents(template: MessageTemplate): Part {
  const part: Part = { buttons: [] };
  for (const component of template.components) {
    const kind = String(component.type ?? "").toUpperCase();
    if (kind === "HEADER") part.header = component;
    else if (kind === "BODY") part.body = component;
    else if (kind === "FOOTER") part.footer = component;
    else if (kind === "BUTTONS" && Array.isArray(component.buttons)) part.buttons = component.buttons as Record<string, unknown>[];
  }
  return part;
}

export function TemplatesClient() {
  const router = useRouter();
  const creditBalance = useCreditBalance();
  const [aiOpen, setAiOpen] = useState(false);

  function useAiDraft(draft: AiTemplateDraft) {
    try {
      sessionStorage.setItem(AI_TEMPLATE_DRAFT_KEY, JSON.stringify(draft));
    } catch {
      // sessionStorage may be unavailable; the editor just starts blank.
    }
    setAiOpen(false);
    router.push("/templates/new");
  }
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [channels, setChannels] = useState<ChannelConnection[]>([]);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [channelId, setChannelId] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [language, setLanguage] = useState("");

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const [detail, setDetail] = useState<MessageTemplate | null>(null);
  const [syncOpen, setSyncOpen] = useState(false);
  const [syncChannel, setSyncChannel] = useState("");
  const [syncing, setSyncing] = useState(false);

  const channelsById = useMemo(() => {
    const map = new Map<string, ChannelConnection>();
    for (const c of channels) map.set(c.id, c);
    return map;
  }, [channels]);
  const whatsappChannels = useMemo(() => channels.filter((c) => c.channel_type === "whatsapp"), [channels]);
  const connectedWhatsApp = useMemo(() => whatsappChannels.filter((c) => c.status === "connected"), [whatsappChannels]);
  const hasActiveFilters = Boolean(search || channelId || status || category || language);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const result = await listTemplates({
        page, page_size: PAGE_SIZE,
        channel_id: channelId || undefined,
        status: status || undefined,
        category: category || undefined,
        language: language || undefined,
        search: search || undefined,
      });
      setTemplates(result.items);
      setTotal(result.total);
    } catch (error) {
      if (!(error instanceof TemplateApiError && error.status === 401)) setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [page, channelId, status, category, language, search]);

  useEffect(() => {
    void Promise.resolve().then(() => load());
  }, [load]);

  useEffect(() => {
    void Promise.resolve().then(async () => {
      try {
        const result = await listChannels({ page: 1, page_size: 100, channel_type: "whatsapp" });
        setChannels(result.items);
      } catch {
        // Channel list is only used for labels/filters; failure is non-fatal.
      }
    });
  }, []);

  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const handle = setTimeout(() => {
      setPage(1);
      setSearch(searchInput.trim());
    }, 350);
    return () => clearTimeout(handle);
  }, [searchInput]);

  function changeFilter(setter: (v: string) => void, value: string) {
    setPage(1);
    setter(value);
  }

  async function openDetail(template: MessageTemplate) {
    setDetail(template);
    try {
      const fresh = await getTemplate(template.id);
      setDetail(fresh);
    } catch {
      // Keep the list row's copy if the detail fetch fails.
    }
  }

  async function runSync() {
    if (!syncChannel) return;
    setSyncing(true);
    setNotice(null);
    try {
      const result = await syncTemplates(syncChannel);
      setSyncOpen(false);
      setSyncChannel("");
      setNotice({
        kind: "success",
        text: `Sync complete — ${result.received} received, ${result.created} new, ${result.updated} updated, ${result.deactivated} deactivated.`,
      });
      await load();
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof TemplateApiError ? error.message : "Could not synchronize templates." });
    } finally {
      setSyncing(false);
    }
  }

  const rangeLabel = total === 0 ? "No templates" : `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total}`;

  return (
    <div className="bg-[#f8f9fa] min-h-screen text-slate-800 font-sans pb-10">
      {/* Top Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="px-6 py-4 flex items-center justify-between mx-auto max-w-7xl">
          <div>
            <h1 className="text-[26px] font-bold text-slate-900 leading-tight">Message Templates</h1>
            <p className="text-[15px] text-slate-500 mt-0.5">Create, manage and monitor your WhatsApp message templates</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#e8f5e9] text-[#2e7d32] px-4 py-2 rounded-full font-semibold text-sm border border-[#c8e6c9]">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
              <span>{creditBalance === null ? "…" : creditBalance.toFixed(2)} AI Credits</span>
            </div>
            <button className="p-2.5 bg-white border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg>
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 mx-auto max-w-7xl">
        {notice && (
          <div className={`p-4 rounded-lg mb-6 text-sm font-semibold flex justify-between ${notice.kind === 'success' ? 'bg-[#e8f5e9] text-[#2e7d32]' : 'bg-rose-50 text-rose-700'}`}>
            <span>{notice.text}</span>
            <button type="button" onClick={() => setNotice(null)}>×</button>
          </div>
        )}

        <PlatformTemplateLibrary />
        
        {/* Actions Row */}
        <div className="flex items-center justify-between mb-8">
          <div className="relative w-80">
            <svg className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input 
              type="search" 
              value={searchInput} 
              onChange={(e) => setSearchInput(e.target.value)} 
              placeholder="Search templates..." 
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:border-[#00b050] focus:ring-1 focus:ring-[#00b050]"
            />
          </div>

          <div className="flex items-center gap-3">
            <button onClick={() => { setSyncChannel(connectedWhatsApp[0]?.id ?? ""); setSyncOpen(true); }} className="p-2.5 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600 shadow-sm">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-lg font-bold text-sm text-slate-700 hover:bg-slate-50 shadow-sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg> Filter
            </button>
            <button onClick={() => setAiOpen(true)} className="flex items-center gap-2 px-4 py-2.5 bg-purple-50 border border-purple-100 rounded-lg font-bold text-sm text-purple-700 hover:bg-purple-100 shadow-sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> Create with AI
            </button>
            <Link href="/templates/new" className="flex items-center gap-2 px-4 py-2.5 bg-[#00b050] hover:bg-[#009040] text-white rounded-lg font-bold text-sm shadow-sm">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg> Create New Template
            </Link>
          </div>
        </div>

        {/* Big Cards */}
        <div className="grid grid-cols-2 gap-6 mb-10">
          <button onClick={() => setAiOpen(true)} className="flex flex-col items-center justify-center py-12 px-6 bg-white border-2 border-dashed border-purple-200 rounded-2xl hover:border-purple-400 hover:bg-purple-50/30 transition-all text-center">
            <div className="w-14 h-14 bg-[#aa42d4] rounded-full flex items-center justify-center text-white mb-4 shadow-sm">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create with AI</h3>
            <p className="text-sm text-slate-500">generate 10 templates, pick one to edit &rarr;</p>
          </button>

          <Link href="/templates/new" className="flex flex-col items-center justify-center py-12 px-6 bg-white border-2 border-dashed border-slate-200 rounded-2xl hover:border-[#00b050] hover:bg-emerald-50/30 transition-all text-center">
            <div className="w-14 h-14 bg-[#00b050] rounded-full flex items-center justify-center text-white mb-4 shadow-sm">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create new template</h3>
            <p className="text-sm text-slate-500">or start from our library &rarr;</p>
          </Link>
        </div>

        <AiTemplateModal open={aiOpen} onClose={() => setAiOpen(false)} onUse={useAiDraft} />

        {/* Existing filters for table */}
        {(hasActiveFilters || templates.length > 0) && (
          <div className="flex gap-4 mb-6">
            <select className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm outline-none shadow-sm" aria-label="Channel" value={channelId} onChange={(e) => changeFilter(setChannelId, e.target.value)}>
              <option value="">All channels</option>
              {whatsappChannels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm outline-none shadow-sm" aria-label="Status" value={status} onChange={(e) => changeFilter(setStatus, e.target.value)}>
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
            </select>
            <select className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm outline-none shadow-sm" aria-label="Category" value={category} onChange={(e) => changeFilter(setCategory, e.target.value)}>
              <option value="">All categories</option>
              {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
            </select>
            <input className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm outline-none shadow-sm" aria-label="Language" value={language} onChange={(e) => changeFilter(setLanguage, e.target.value.trim())} placeholder="Language (e.g. en_US)" maxLength={12} />
          </div>
        )}

        <div className="mb-4 text-sm font-semibold text-slate-500" aria-live="polite">{rangeLabel}</div>

      {loading ? (
        <div className="channel-state" role="status">Loading templates…</div>
      ) : loadError ? (
        <div className="channel-state channel-state-error" role="alert">
          <strong>Templates could not be loaded.</strong>
          <p>The templates service did not respond. Please try again.</p>
          <button type="button" className="channel-secondary-btn" onClick={() => void load()}>Try again</button>
        </div>
      ) : templates.length === 0 ? (
        <div className="channel-state channel-empty">
          <span className="channel-empty-mark" aria-hidden="true">▤</span>
          <strong>{hasActiveFilters ? "No matching templates" : "No templates yet"}</strong>
          <p>{hasActiveFilters ? "Adjust your search or filters." : "Sync a connected WhatsApp channel to import its approved templates."}</p>
          {!hasActiveFilters && connectedWhatsApp.length > 0 && (
            <button type="button" className="channel-primary-btn" onClick={() => { setSyncChannel(connectedWhatsApp[0].id); setSyncOpen(true); }}>Sync templates</button>
          )}
        </div>
      ) : (
        <>
          <div className="contact-table" role="table" aria-label="Templates">
            <div className="contact-row tpl-row contact-head" role="row">
              <span role="columnheader">Name</span>
              <span role="columnheader">Channel</span>
              <span role="columnheader">Language</span>
              <span role="columnheader">Category</span>
              <span role="columnheader">Status</span>
              <span role="columnheader">Updated</span>
              <span role="columnheader" className="contact-actions-col">Actions</span>
            </div>
            {templates.map((template) => (
              <div className="contact-row tpl-row" role="row" key={template.id}>
                <span role="cell" data-label="Name"><button type="button" className="contact-link" onClick={() => void openDetail(template)}>{template.name}</button></span>
                <span role="cell" data-label="Channel">{channelsById.get(template.channel_connection_id)?.name ?? "—"}</span>
                <span role="cell" data-label="Language">{template.language}</span>
                <span role="cell" data-label="Category">{titleCase(template.category)}</span>
                <span role="cell" data-label="Status"><span className={`channel-pill ${STATUS_TONE[template.status] ?? "channel-pill-muted"}`}>{titleCase(template.status)}</span></span>
                <span role="cell" data-label="Updated">{formatDate(template.updated_at)}</span>
                <span role="cell" data-label="Actions" className="contact-actions-col">
                  <button type="button" className="channel-action" onClick={() => void openDetail(template)}>Preview</button>
                </span>
              </div>
            ))}
          </div>

          <nav className="contact-pagination" aria-label="Pagination">
            <button type="button" className="channel-secondary-btn" disabled={page <= 1 || loading} onClick={() => setPage((p) => Math.max(1, p - 1))}>← Previous</button>
            <span>Page {page} of {totalPages}</span>
            <button type="button" className="channel-secondary-btn" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>Next →</button>
          </nav>
        </>
      )}

      {/* Preview modal */}
      {detail && <TemplatePreview template={detail} channelName={channelsById.get(detail.channel_connection_id)?.name ?? null} onClose={() => setDetail(null)} />}

      {/* Sync modal */}
      {syncOpen && (
        <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="sync-title">
          <div className="channel-modal channel-modal-sm">
            <h2 id="sync-title">Sync WhatsApp templates</h2>
            <p className="channel-modal-sub">Fetch the latest approved templates from Meta for a connected channel.</p>
            {connectedWhatsApp.length === 0 ? (
              <p className="channel-form-error" role="alert">No connected WhatsApp channel is available. Connect one from Channels first.</p>
            ) : (
              <label className="channel-field team-manage-field">
                <span>Channel</span>
                <select value={syncChannel} onChange={(e) => setSyncChannel(e.target.value)}>
                  {connectedWhatsApp.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </label>
            )}
            <div className="channel-modal-actions">
              <button type="button" className="channel-secondary-btn" onClick={() => setSyncOpen(false)} disabled={syncing}>Cancel</button>
              <button type="button" className="channel-primary-btn" onClick={() => void runSync()} disabled={syncing || !syncChannel}>{syncing ? "Syncing…" : "Sync now"}</button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}

function TemplatePreview({ template, channelName, onClose }: { template: MessageTemplate; channelName: string | null; onClose: () => void }) {
  const part = splitComponents(template);
  const variables = uniquePlaceholders(template);
  const headerText = typeof part.header?.text === "string" ? part.header.text : null;
  const headerFormat = typeof part.header?.format === "string" ? part.header.format.toUpperCase() : null;
  const bodyText = typeof part.body?.text === "string" ? part.body.text : "";
  const footerText = typeof part.footer?.text === "string" ? part.footer.text : null;

  return (
    <div className="channel-modal-scrim" role="dialog" aria-modal="true" aria-labelledby="tpl-title">
      <div className="channel-modal contact-detail-modal">
        <div className="contact-detail-head">
          <div>
            <h2 id="tpl-title">{template.name}</h2>
            <span className={`channel-pill ${STATUS_TONE[template.status] ?? "channel-pill-muted"}`}>{titleCase(template.status)}</span>
          </div>
          <button type="button" className="contact-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <dl className="channel-facts contact-detail-facts">
          <div><dt>Channel</dt><dd>{channelName ?? "—"}</dd></div>
          <div><dt>Language</dt><dd>{template.language}</dd></div>
          <div><dt>Category</dt><dd>{titleCase(template.category)}</dd></div>
          <div><dt>Template ID</dt><dd>{template.external_template_id ?? "—"}</dd></div>
        </dl>

        <div className="tpl-preview">
          <h3>Preview</h3>
          <div className="tpl-bubble">
            {part.header && (
              headerFormat && headerFormat !== "TEXT"
                ? <div className="tpl-media-header">{titleCase(headerFormat.toLowerCase())} header</div>
                : headerText && <div className="tpl-header">{renderWithPlaceholders(headerText)}</div>
            )}
            {bodyText && <div className="tpl-body">{renderWithPlaceholders(bodyText)}</div>}
            {footerText && <div className="tpl-footer">{footerText}</div>}
            {part.buttons.length > 0 && (
              <div className="tpl-buttons">
                {part.buttons.map((button, index) => (
                  <span className="tpl-button" key={index}>{typeof button.text === "string" ? button.text : "Button"}</span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="tpl-vars">
          <h3>Variables</h3>
          {variables.length > 0 ? (
            <ul className="tpl-var-list">
              {variables.map((v) => <li key={v}><code className="tpl-var">{`{{${v}}}`}</code> — required when sending</li>)}
            </ul>
          ) : (
            <p className="contact-muted">This template has no variables.</p>
          )}
        </div>

        <p className="tpl-send-note">
          To send this template, open a conversation with the contact in the Inbox and choose it there — the 24-hour window and recipient are handled per conversation.
        </p>

        <div className="channel-modal-actions">
          <button type="button" className="channel-secondary-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
