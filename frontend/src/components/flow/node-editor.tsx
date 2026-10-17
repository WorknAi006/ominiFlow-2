"use client";

import { useEffect, useRef, useState } from "react";
import {
  CHANNEL_TYPES, MEDIA_MESSAGE_TYPES, MESSAGE_TYPES, VARIABLES, flowsApi,
  type FlowNode,
} from "@/lib/flows/browser";
import { listTemplates } from "@/lib/templates/browser";
import type { MessageTemplate } from "@/lib/api/templates";

const OPERATORS = [
  { value: "is", label: "is" },
  { value: "is_not", label: "is not" },
  { value: "contains", label: "contains" },
  { value: "doesnt_contain", label: "doesn't contain" },
  { value: "starts_with", label: "starts with" },
  { value: "ends_with", label: "ends with" },
  { value: "has_value", label: "has value" },
  { value: "has_no_value", label: "has no value" },
];

type ButtonKind = "reply" | "url" | "call";
type ButtonOpt = { id: string; title: string; kind?: ButtonKind; url?: string; phoneNumber?: string };
type ListOpt = { id: string; title: string; description?: string };
type Condition = { source?: string; operator?: string; value?: string };
type HeaderData = { type?: "none" | "text" | "image" | "video" | "document"; text?: string; mediaKey?: string; mediaUrl?: string; mediaName?: string };

const BUTTON_KINDS: { value: ButtonKind; label: string }[] = [
  { value: "reply", label: "Custom (Reply)" },
  { value: "url", label: "Visit website" },
  { value: "call", label: "Call Us" },
];
const HEADER_TYPES: { value: NonNullable<HeaderData["type"]>; label: string }[] = [
  { value: "none", label: "No header" },
  { value: "text", label: "Text" },
  { value: "image", label: "Image" },
  { value: "video", label: "Video" },
  { value: "document", label: "Document" },
];

const newId = () => (crypto.randomUUID ? crypto.randomUUID().slice(0, 8) : String(Date.now()));

export function NodeEditor({
  node, onChange, onClose, onDuplicate,
}: {
  node: FlowNode;
  onChange: (patch: Record<string, unknown>) => void;
  onClose: () => void;
  onDuplicate: () => void;
}) {
  const d = node.data;
  const messageType = String(d.messageType ?? "text");
  const message = String(d.message ?? "");
  const [varOpen, setVarOpen] = useState(false);
  const [mediaMode, setMediaMode] = useState<"upload" | "url">("upload");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const headerFileRef = useRef<HTMLInputElement>(null);
  const [headerUploading, setHeaderUploading] = useState(false);
  const [headerUploadError, setHeaderUploadError] = useState("");
  const isMedia = MEDIA_MESSAGE_TYPES.has(messageType);
  const isText = messageType === "text";
  const showMessageBox = ["text", "button", "list", "get_user_data", "audio", "document", "image", "video"].includes(messageType);
  const showHeaderFooter = showMessageBox;
  const headerOptions = messageType === "button" ? HEADER_TYPES : HEADER_TYPES.filter((h) => h.value === "none" || h.value === "text");

  useEffect(() => {
    if (messageType === "template" && templates.length === 0) {
      listTemplates({ page_size: 100 }).then((r) => setTemplates(r.items)).catch(() => setTemplates([]));
    }
  }, [messageType, templates.length]);

  async function upload(file: File) {
    setUploading(true);
    setUploadError("");
    try {
      const res = await flowsApi.upload(file);
      onChange({ mediaUrl: res.url, mediaKey: res.key, mediaName: res.filename, mediaContentType: res.content_type });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function insertVariable(token: string) {
    onChange({ message: message + token });
    setVarOpen(false);
  }

  // Header config
  const header = (d.header as HeaderData | undefined) ?? {};
  const headerType = String(header.type ?? "none");
  const setHeader = (patch: Partial<HeaderData>) => onChange({ header: { ...header, ...patch } });

  async function uploadHeader(file: File) {
    setHeaderUploading(true);
    setHeaderUploadError("");
    try {
      const res = await flowsApi.upload(file);
      setHeader({ mediaKey: res.key, mediaUrl: res.url, mediaName: res.filename });
    } catch (e) {
      setHeaderUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setHeaderUploading(false);
    }
  }

  // Buttons config
  const buttons = (d.buttons as ButtonOpt[] | undefined) ?? [];
  const setButtons = (next: ButtonOpt[]) => onChange({ buttons: next });

  // List config
  const listItems = (d.listItems as ListOpt[] | undefined) ?? [];
  const setListItems = (next: ListOpt[]) => onChange({ listItems: next });
  const listMenuButton = String(d.listMenuButton ?? "Options");

  // Condition config
  const cond = (d.condition as Condition | undefined) ?? {};
  const setCond = (patch: Partial<Condition>) => onChange({ condition: { ...cond, ...patch } });
  const condSource = String(cond.source ?? "last_input");
  const condKind = condSource.startsWith("variable:") ? "variable" : condSource;

  const currentTypeMeta = MESSAGE_TYPES.find((t) => t.value === messageType);

  return (
    <aside className="flex h-full w-84 sm:w-96 flex-col border-r border-slate-200 bg-white shadow-xl z-10 transition-all animate-in slide-in-from-left duration-200">
      {/* Drawer Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5 bg-slate-50/50">
        <h3 className="text-base font-bold text-slate-900">
          {currentTypeMeta?.label ?? "Configure Node"}
        </h3>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onDuplicate}
            title="Duplicate Node"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          </button>
          <button
            type="button"
            onClick={onClose}
            title="Close Panel"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>

      {/* Drawer Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
        {/* Channel Type */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Channel Type</label>
          <select
            value={String(d.channel ?? "whatsapp")}
            onChange={(e) => onChange({ channel: e.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            {CHANNEL_TYPES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>

        {/* Message Type */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Message Type</label>
          <select
            value={messageType}
            onChange={(e) => onChange({ messageType: e.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            {MESSAGE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>

        {/* Media Upload / URL Selector for Media nodes */}
        {isMedia && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl">
              <button
                type="button"
                onClick={() => setMediaMode("upload")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-bold rounded-lg transition ${
                  mediaMode === "upload" ? "bg-white text-blue-600 shadow-xs" : "text-slate-500 hover:text-slate-800"
                }`}
              >
                <span>⬆</span> Upload File
              </button>
              <button
                type="button"
                onClick={() => setMediaMode("url")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-bold rounded-lg transition ${
                  mediaMode === "url" ? "bg-white text-blue-600 shadow-xs" : "text-slate-500 hover:text-slate-800"
                }`}
              >
                <span>🔗</span> Paste URL
              </button>
            </div>

            {mediaMode === "upload" ? (
              <div>
                <input
                  ref={fileRef}
                  type="file"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); }}
                />
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  className="w-full flex flex-col items-center justify-center p-6 border-2 border-dashed border-purple-200 rounded-2xl bg-purple-50/30 hover:bg-purple-50/60 transition group cursor-pointer"
                >
                  <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 mb-2 group-hover:scale-105 transition">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  </div>
                  <span className="text-sm font-bold text-slate-800">
                    {uploading ? "Uploading file..." : d.mediaName ? String(d.mediaName) : `Click to upload ${messageType}`}
                  </span>
                  <span className="text-xs text-slate-400 mt-1">
                    PDF, DOCX, JPG, MP4 · Max 100MB
                  </span>
                </button>
                {d.mediaUrl && (
                  <a href={String(d.mediaUrl)} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline">
                    View uploaded file ↗
                  </a>
                )}
                {uploadError && <p className="mt-1.5 text-xs font-medium text-rose-600">{uploadError}</p>}
              </div>
            ) : (
              <div>
                <input
                  type="url"
                  value={String(d.mediaUrl ?? "")}
                  onChange={(e) => onChange({ mediaUrl: e.target.value, mediaName: e.target.value.split("/").pop() || "media" })}
                  placeholder="https://example.com/asset.pdf"
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
                />
              </div>
            )}
          </div>
        )}

        {/* Header Configuration (Button messages / interactive) */}
        {showHeaderFooter && (
          <div className="space-y-2 pt-1 border-t border-slate-100">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">Header (Optional)</label>
            <select
              value={headerType}
              onChange={(e) => setHeader({ type: e.target.value as HeaderData["type"] })}
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-blue-500"
            >
              {headerOptions.map((h) => <option key={h.value} value={h.value}>{h.label}</option>)}
            </select>

            {headerType === "text" && (
              <div className="relative mt-2">
                <input
                  value={String(header.text ?? "")}
                  onChange={(e) => setHeader({ text: e.target.value })}
                  maxLength={60}
                  placeholder="Header text (max 60)"
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
                />
                <span className="absolute right-3 top-3 text-[10px] font-semibold text-slate-400">
                  {String(header.text ?? "").length}/60
                </span>
              </div>
            )}

            {(headerType === "image" || headerType === "video" || headerType === "document") && (
              <div className="mt-2">
                <input ref={headerFileRef} type="file" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void uploadHeader(f); }} />
                <button
                  type="button"
                  onClick={() => headerFileRef.current?.click()}
                  disabled={headerUploading}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 p-4 text-xs font-semibold text-slate-600 hover:border-blue-400 hover:bg-slate-50 transition"
                >
                  {headerUploading ? "Uploading..." : header.mediaName ? `📎 ${String(header.mediaName)}` : `⬆ Upload sample ${headerType}`}
                </button>
                {headerUploadError && <p className="mt-1 text-xs text-rose-600">{headerUploadError}</p>}
              </div>
            )}
          </div>
        )}

        {/* Message / Caption / Menu Body Editor */}
        {showMessageBox && (
          <div className="space-y-1.5 pt-1 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                {messageType === "get_user_data" ? "Question to ask" : isMedia ? "Caption (Optional)" : "Message"}
              </label>

              {/* + Variable Button Popover */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setVarOpen((v) => !v)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
                >
                  <span className="text-blue-600 font-extrabold">+</span> Variable
                </button>
                {varOpen && (
                  <div className="absolute right-0 z-20 mt-1 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black/5">
                    <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                      Insert Variable
                    </div>
                    {VARIABLES.map((v) => (
                      <button
                        key={v.value}
                        type="button"
                        onClick={() => insertVariable(v.value)}
                        className="block w-full px-3 py-1.5 text-left text-xs font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition"
                      >
                        {v.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <textarea
              value={message}
              onChange={(e) => onChange({ message: e.target.value })}
              placeholder={isMedia ? "Add a caption for this media..." : "Type a message..."}
              maxLength={4096}
              rows={4}
              className={`w-full rounded-xl border p-3 text-sm leading-relaxed outline-none transition ${
                isText && !message.trim() ? "border-rose-300 focus:border-rose-500" : "border-slate-200 focus:border-blue-500"
              }`}
            />
            <div className="flex items-center justify-between text-[11px]">
              {isText && !message.trim() ? (
                <span className="text-rose-600 font-medium">Body is required for a text message.</span>
              ) : (
                <span />
              )}
              <span className="font-semibold text-slate-400 ml-auto">
                {message.length}/4096
              </span>
            </div>

            {/* Show link preview checkbox for text message */}
            {isText && (
              <label className="flex items-start gap-2.5 pt-2 text-xs text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={d.showLinkPreview !== false}
                  onChange={(e) => onChange({ showLinkPreview: e.target.checked })}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span>
                  Show link preview <span className="text-slate-400">(renders the first http/https URL in the body)</span>
                </span>
              </label>
            )}
          </div>
        )}

        {/* Footer Configuration */}
        {showHeaderFooter && (
          <div className="space-y-1.5 pt-1 border-t border-slate-100">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">Footer (Optional, Max 60)</label>
            <div className="relative">
              <input
                value={String(d.footer ?? "")}
                onChange={(e) => onChange({ footer: e.target.value })}
                maxLength={60}
                placeholder="e.g. Tap a button to proceed"
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
              />
              <span className="absolute right-3 top-3 text-[10px] font-semibold text-slate-400">
                {String(d.footer ?? "").length}/60
              </span>
            </div>
          </div>
        )}

        {/* Button Message Configuration */}
        {messageType === "button" && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Interactive Buttons</label>
              <span className="text-xs font-semibold text-slate-400">{buttons.length}/3</span>
            </div>

            <div className="space-y-2.5">
              {buttons.map((b, i) => {
                const kind = (b.kind ?? "reply") as ButtonKind;
                const upd = (patch: Partial<ButtonOpt>) => setButtons(buttons.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
                return (
                  <div key={b.id || i} className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/50 p-3 shadow-2xs">
                    <div className="flex items-center gap-2">
                      <select
                        value={kind}
                        onChange={(e) => upd({ kind: e.target.value as ButtonKind })}
                        className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 outline-none"
                      >
                        {BUTTON_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                      </select>
                      <input
                        value={b.title}
                        onChange={(e) => upd({ title: e.target.value })}
                        maxLength={20}
                        placeholder={`Button ${i + 1} text`}
                        className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium outline-none focus:border-blue-500"
                      />
                      <button
                        type="button"
                        onClick={() => setButtons(buttons.filter((_, idx) => idx !== i))}
                        className="rounded p-1 text-slate-400 hover:text-rose-600 transition"
                      >
                        🗑
                      </button>
                    </div>
                    {kind === "url" && (
                      <input
                        value={String(b.url ?? "")}
                        onChange={(e) => upd({ url: e.target.value })}
                        placeholder="https://example.com"
                        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-xs outline-none focus:border-blue-500"
                      />
                    )}
                    {kind === "call" && (
                      <input
                        value={String(b.phoneNumber ?? "")}
                        onChange={(e) => upd({ phoneNumber: e.target.value })}
                        placeholder="+1 555 123 4567"
                        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-xs outline-none focus:border-blue-500"
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {buttons.length < 3 && (
              <button
                type="button"
                onClick={() => setButtons([...buttons, { id: newId(), title: "", kind: "reply" }])}
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl border border-dashed border-blue-300 bg-blue-50/40 text-xs font-bold text-blue-700 hover:bg-blue-50 transition"
              >
                + Add Button
              </button>
            )}
            <p className="text-[11px] text-slate-400">
              Only <b>Custom (Reply)</b> buttons generate branch handles on the canvas. URL and Call buttons trigger external actions.
            </p>
          </div>
        )}

        {/* List Message Configuration (Sections & Rows) */}
        {messageType === "list" && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">List Menu Button (Required, Max 20)</label>
              <input
                value={listMenuButton}
                onChange={(e) => onChange({ listMenuButton: e.target.value })}
                maxLength={20}
                placeholder="e.g. Options or View Menu"
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">List Rows ({listItems.length}/10)</label>
              <span className="text-[11px] text-slate-400">Each row creates a branch handle</span>
            </div>

            <div className="space-y-2">
              {listItems.map((item, i) => (
                <div key={item.id || i} className="flex items-center gap-2 rounded-xl border border-slate-200 p-2 bg-slate-50/50">
                  <input
                    value={item.title}
                    onChange={(e) => setListItems(listItems.map((x, idx) => (idx === i ? { ...x, title: e.target.value } : x)))}
                    maxLength={24}
                    placeholder={`Row ${i + 1} title`}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setListItems(listItems.filter((_, idx) => idx !== i))}
                    className="rounded p-1 text-slate-400 hover:text-rose-600 transition"
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>

            {listItems.length < 10 && (
              <button
                type="button"
                onClick={() => setListItems([...listItems, { id: newId(), title: "" }])}
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl border border-dashed border-slate-300 text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
              >
                + Add Row
              </button>
            )}
          </div>
        )}

        {/* Condition Node Configuration */}
        {messageType === "condition" && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Check Field</span>
              <select
                value={condKind}
                onChange={(e) => setCond({ source: e.target.value === "variable" ? "variable:" : e.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium outline-none focus:border-blue-500"
              >
                <option value="last_input">User last input</option>
                <option value="variable">A variable</option>
                <option value="contact_name">Contact name</option>
                <option value="contact_phone">Contact phone</option>
              </select>
            </label>

            {condKind === "variable" && (
              <label className="block">
                <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Variable name</span>
                <input
                  value={condSource.replace("variable:", "")}
                  onChange={(e) => setCond({ source: `variable:${e.target.value}` })}
                  placeholder="e.g. city or language"
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
                />
              </label>
            )}

            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Operator</span>
              <select
                value={String(cond.operator ?? "is")}
                onChange={(e) => setCond({ operator: e.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium outline-none focus:border-blue-500"
              >
                {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>

            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Value</span>
              <input
                value={String(cond.value ?? "")}
                onChange={(e) => setCond({ value: e.target.value })}
                placeholder="Compare value..."
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </label>
            <p className="text-[11px] text-slate-400">
              Connect the <b>True (Match)</b> and <b>False (No match)</b> handles to the respective branches.
            </p>
          </div>
        )}

        {/* Delay Node Configuration */}
        {messageType === "delay" && (
          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Wait</span>
              <input
                type="number"
                min={1}
                value={Number(d.delayValue ?? 1)}
                onChange={(e) => onChange({ delayValue: Number(e.target.value), delaySeconds: undefined })}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </label>
            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Unit</span>
              <select
                value={String(d.delayUnit ?? "minutes")}
                onChange={(e) => onChange({ delayUnit: e.target.value, delaySeconds: undefined })}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium outline-none focus:border-blue-500"
              >
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
              </select>
            </label>
          </div>
        )}

        {/* Get User Data Configuration */}
        {messageType === "get_user_data" && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <label className="block">
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Save reply to variable</span>
              <input
                value={String(d.variable ?? "")}
                onChange={(e) => onChange({ variable: e.target.value })}
                placeholder="e.g. user_email or order_number"
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500"
              />
              <span className="mt-1 block text-xs text-slate-400">
                Use later as {`{{${String(d.variable || "variable")}}}`} in following nodes.
              </span>
            </label>
          </div>
        )}

        {/* Template Node Configuration */}
        {messageType === "template" && (
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">Approved Template</label>
            {templates.length === 0 ? (
              <p className="text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl p-4 text-center">
                No synced templates found. Sync from Templates page first.
              </p>
            ) : (
              <select
                value={String(d.templateName ?? "")}
                onChange={(e) => {
                  const t = templates.find((x) => x.name === e.target.value);
                  onChange({ templateName: t?.name ?? "", templateLanguage: t?.language ?? "en_US" });
                }}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-medium outline-none focus:border-blue-500"
              >
                <option value="">Select an approved template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.name} disabled={!t.is_usable}>
                    {t.name} · {t.language}{t.is_usable ? "" : ` (${t.status})`}
                  </option>
                ))}
              </select>
            )}
            {d.templateName ? (
              <p className="text-xs font-medium text-emerald-700 bg-emerald-50 p-2.5 rounded-lg border border-emerald-100">
                Sends <b>{String(d.templateName)}</b> ({String(d.templateLanguage ?? "en_US")}).
              </p>
            ) : null}
          </div>
        )}
      </div>
    </aside>
  );
}

