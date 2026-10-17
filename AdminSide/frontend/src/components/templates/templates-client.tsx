"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  TemplateApiError,
  getTemplate,
  listTemplates,
  syncTemplates,
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
    <section className="page-enter max-w-5xl">
      <header className="channel-header">
        <div>
          <p className="eyebrow">OMNIFLOW WORKSPACE</p>
          <h1 className="page-title mt-2">Templates</h1>
          <p className="page-subtitle mt-2">Approved WhatsApp message templates for your connected channels.</p>
        </div>
        <button type="button" className="channel-primary-btn" onClick={() => { setSyncChannel(connectedWhatsApp[0]?.id ?? ""); setSyncOpen(true); }}>
          <span aria-hidden="true">↻</span> Sync templates
        </button>
      </header>

      {notice && (
        <div className={`channel-notice channel-notice-${notice.kind}`} role="status">
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="tpl-filters">
        <label className="contact-search tpl-search">
          <span className="sr-only">Search templates</span>
          <span className="contact-search-icon" aria-hidden="true">⌕</span>
          <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Search by name" maxLength={100} />
        </label>
        <select aria-label="Channel" value={channelId} onChange={(e) => changeFilter(setChannelId, e.target.value)}>
          <option value="">All channels</option>
          {whatsappChannels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select aria-label="Status" value={status} onChange={(e) => changeFilter(setStatus, e.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
        </select>
        <select aria-label="Category" value={category} onChange={(e) => changeFilter(setCategory, e.target.value)}>
          <option value="">All categories</option>
          {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
        </select>
        <input aria-label="Language" className="tpl-lang" value={language} onChange={(e) => changeFilter(setLanguage, e.target.value.trim())} placeholder="Language (e.g. en_US)" maxLength={12} />
      </div>

      <div className="contact-toolbar tpl-range-row">
        <span className="contact-range" aria-live="polite">{rangeLabel}</span>
      </div>

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
    </section>
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
