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
  { value: "reply", label: "Custom" },
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
  // Header + footer are shown for every message-body node. On button messages
  // they map to a real WhatsApp interactive header/footer; on text / media /
  // list they are composed into the body (a bold first line + a footer line),
  // since WhatsApp only supports native header/footer on interactive messages.
  const showHeaderFooter = showMessageBox;
  // Media header types (image/video/document) are only deliverable on button
  // (interactive) messages; elsewhere only a text header is composed in.
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

  // ----- header (interactive messages) -----
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

  // ----- buttons -----
  const buttons = (d.buttons as ButtonOpt[] | undefined) ?? [];
  const setButtons = (next: ButtonOpt[]) => onChange({ buttons: next });
  // ----- list -----
  const listItems = (d.listItems as ListOpt[] | undefined) ?? [];
  const setListItems = (next: ListOpt[]) => onChange({ listItems: next });
  // ----- condition -----
  const cond = (d.condition as Condition | undefined) ?? {};
  const setCond = (patch: Partial<Condition>) => onChange({ condition: { ...cond, ...patch } });
  const condSource = String(cond.source ?? "last_input");
  const condKind = condSource.startsWith("variable:") ? "variable" : condSource;

  const label = (text: string) => <span className="font-medium text-slate-700 text-sm block mb-1">{text}</span>;
  const input = "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";

  return (
    <aside className="flex h-full w-80 flex-col overflow-y-auto border-r border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h3 className="text-sm font-bold text-slate-800">{MESSAGE_TYPES.find((t) => t.value === messageType)?.label ?? "Message"}</h3>
        <div className="flex items-center gap-1">
          <button onClick={onDuplicate} title="Duplicate" className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">⧉</button>
          <button onClick={onClose} title="Close" className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">✕</button>
        </div>
      </div>

      <div className="space-y-5 px-4 py-4">
        <label className="block">{label("Channel Type")}
          <select value={String(d.channel ?? "whatsapp")} onChange={(e) => onChange({ channel: e.target.value })} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
            {CHANNEL_TYPES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>

        <label className="block">{label("Message Type")}
          <select value={messageType} onChange={(e) => onChange({ messageType: e.target.value })} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
            {MESSAGE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </label>

        {/* Media upload */}
        {isMedia && (
          <div>
            {label("Upload file")}
            <input ref={fileRef} type="file" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); }} />
            <button onClick={() => fileRef.current?.click()} disabled={uploading} className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-6 text-sm text-slate-500 hover:border-blue-400 hover:text-blue-600">
              {uploading ? "Uploading…" : d.mediaName ? `📎 ${String(d.mediaName)}` : "⬆ Click to upload a file"}
            </button>
            {d.mediaUrl && <a href={String(d.mediaUrl)} target="_blank" rel="noreferrer" className="mt-2 block text-xs font-semibold text-blue-600 hover:underline">Preview uploaded file ↗</a>}
            {uploadError && <p className="mt-1 text-xs text-rose-600">{uploadError}</p>}
          </div>
        )}

        {/* Header (interactive button / list messages) */}
        {showHeaderFooter && (
          <div>
            {label("Header (optional)")}
            <select value={headerType} onChange={(e) => setHeader({ type: e.target.value as HeaderData["type"] })} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
              {headerOptions.map((h) => <option key={h.value} value={h.value}>{h.label}</option>)}
            </select>
            {messageType !== "button" && headerType === "text" && (
              <span className="mt-1 block text-xs text-slate-400">Added as a bold first line (WhatsApp shows native headers only on button messages).</span>
            )}
            {headerType === "text" && (
              <input value={String(header.text ?? "")} onChange={(e) => setHeader({ text: e.target.value })} maxLength={60} placeholder="Header text (max 60)" className={input} />
            )}
            {(headerType === "image" || headerType === "video" || headerType === "document") && (
              <div className="mt-2">
                <input ref={headerFileRef} type="file" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void uploadHeader(f); }} />
                <button onClick={() => headerFileRef.current?.click()} disabled={headerUploading} className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-4 text-sm text-slate-500 hover:border-blue-400 hover:text-blue-600">
                  {headerUploading ? "Uploading…" : header.mediaName ? `📎 ${String(header.mediaName)}` : `⬆ Upload ${headerType}`}
                </button>
                {header.mediaUrl && <a href={String(header.mediaUrl)} target="_blank" rel="noreferrer" className="mt-1 block text-xs font-semibold text-blue-600 hover:underline">Preview ↗</a>}
                {headerUploadError && <p className="mt-1 text-xs text-rose-600">{headerUploadError}</p>}
              </div>
            )}
          </div>
        )}

        {/* Message / prompt / menu body */}
        {showMessageBox && (
          <div>
            <div className="flex items-center justify-between">
              {label(messageType === "get_user_data" ? "Question to ask" : isMedia ? "Caption" : messageType === "button" || messageType === "list" ? "Menu text" : "Message")}
              <div className="relative">
                <button onClick={() => setVarOpen((v) => !v)} className="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50">+ Variable</button>
                {varOpen && (
                  <div className="absolute right-0 z-10 mt-1 w-44 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                    {VARIABLES.map((v) => <button key={v.value} onClick={() => insertVariable(v.value)} className="block w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50">{v.label}</button>)}
                  </div>
                )}
              </div>
            </div>
            <textarea value={message} onChange={(e) => onChange({ message: e.target.value })} placeholder="Type a message..." maxLength={4096} rows={4} className={input} />
            {isText && !message.trim() && <p className="text-xs text-rose-600">Body is required for a text message.</p>}
            {messageType === "button" && !message.trim() && <p className="text-xs text-rose-600">Body is required for a button message.</p>}
          </div>
        )}

        {/* Footer (interactive button / list messages) */}
        {showHeaderFooter && (
          <label className="block">{label("Footer (optional, max 60)")}
            <input value={String(d.footer ?? "")} onChange={(e) => onChange({ footer: e.target.value })} maxLength={60} placeholder="e.g. Tap a button to continue" className={input} />
          </label>
        )}

        {/* Buttons */}
        {messageType === "button" && (
          <div>
            {label("Buttons")}
            <div className="space-y-2">
              {buttons.map((b, i) => {
                const kind = (b.kind ?? "reply") as ButtonKind;
                const upd = (patch: Partial<ButtonOpt>) => setButtons(buttons.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
                return (
                  <div key={b.id} className="space-y-2 rounded-lg border border-slate-200 p-2">
                    <div className="flex items-center gap-2">
                      <select value={kind} onChange={(e) => upd({ kind: e.target.value as ButtonKind })} className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm">
                        {BUTTON_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
                      </select>
                      <input value={b.title} onChange={(e) => upd({ title: e.target.value })} maxLength={20} placeholder={`Button ${i + 1}`} className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                      <button onClick={() => setButtons(buttons.filter((_, idx) => idx !== i))} className="rounded p-1.5 text-slate-400 hover:text-rose-600">🗑</button>
                    </div>
                    {kind === "url" && (
                      <input value={String(b.url ?? "")} onChange={(e) => upd({ url: e.target.value })} placeholder="https://example.com" className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    )}
                    {kind === "call" && (
                      <input value={String(b.phoneNumber ?? "")} onChange={(e) => upd({ phoneNumber: e.target.value })} placeholder="+1 555 123 4567" className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    )}
                  </div>
                );
              })}
            </div>
            <button onClick={() => setButtons([...buttons, { id: newId(), title: "", kind: "reply" }])} className="mt-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">+ Add button</button>
            <p className="mt-1.5 text-xs text-slate-400">Only <b>Custom</b> buttons are tappable replies that create branches. Website / Call buttons open a link or dial a number.</p>
          </div>
        )}

        {/* List */}
        {messageType === "list" && (
          <div>
            {label("List items (each becomes a branch)")}
            <div className="space-y-2">
              {listItems.map((it, i) => (
                <div key={it.id} className="flex items-center gap-2">
                  <input value={it.title} onChange={(e) => setListItems(listItems.map((x, idx) => idx === i ? { ...x, title: e.target.value } : x))} placeholder={`Item ${i + 1}`} className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <button onClick={() => setListItems(listItems.filter((_, idx) => idx !== i))} className="rounded p-1.5 text-slate-400 hover:text-rose-600">🗑</button>
                </div>
              ))}
            </div>
            <button onClick={() => setListItems([...listItems, { id: newId(), title: "" }])} className="mt-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">+ Add item</button>
          </div>
        )}

        {/* Condition */}
        {messageType === "condition" && (
          <div className="space-y-3">
            <label className="block">{label("Check")}
              <select value={condKind} onChange={(e) => setCond({ source: e.target.value === "variable" ? "variable:" : e.target.value })} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="last_input">User last input</option>
                <option value="variable">A variable</option>
                <option value="contact_name">Contact name</option>
                <option value="contact_phone">Contact phone</option>
              </select>
            </label>
            {condKind === "variable" && (
              <label className="block">{label("Variable name")}
                <input value={condSource.replace("variable:", "")} onChange={(e) => setCond({ source: `variable:${e.target.value}` })} placeholder="e.g. city" className={input} />
              </label>
            )}
            <label className="block">{label("Operator")}
              <select value={String(cond.operator ?? "is")} onChange={(e) => setCond({ operator: e.target.value })} className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label className="block">{label("Value")}
              <input value={String(cond.value ?? "")} onChange={(e) => setCond({ value: e.target.value })} placeholder="compare to…" className={input} />
            </label>
            <p className="text-xs text-slate-400">Connect the <b>True</b> and <b>False</b> handles to the next steps.</p>
          </div>
        )}

        {/* Delay */}
        {messageType === "delay" && (
          <div className="grid grid-cols-2 gap-3">
            <label className="block">{label("Wait")}
              <input type="number" min={1} value={Number(d.delayValue ?? 1)} onChange={(e) => onChange({ delayValue: Number(e.target.value), delaySeconds: undefined })} className={input} />
            </label>
            <label className="block">{label("Unit")}
              <select value={String(d.delayUnit ?? "minutes")} onChange={(e) => onChange({ delayUnit: e.target.value, delaySeconds: undefined })} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
                <option value="seconds">Seconds</option>
                <option value="minutes">Minutes</option>
                <option value="hours">Hours</option>
              </select>
            </label>
          </div>
        )}

        {/* Get user data */}
        {messageType === "get_user_data" && (
          <label className="block">{label("Save reply to variable")}
            <input value={String(d.variable ?? "")} onChange={(e) => onChange({ variable: e.target.value })} placeholder="e.g. city" className={input} />
            <span className="mt-1 block text-xs text-slate-400">Use it later as {"{{"}{String(d.variable || "variable")}{"}}"}.</span>
          </label>
        )}

        {/* Template */}
        {messageType === "template" && (
          <div className="space-y-3">
            {label("Approved template")}
            {templates.length === 0 ? (
              <p className="text-sm text-slate-500 border border-dashed border-slate-200 rounded p-3">No synced templates. Sync from Templates page first.</p>
            ) : (
              <select
                value={String(d.templateName ?? "")}
                onChange={(e) => {
                  const t = templates.find((x) => x.name === e.target.value);
                  onChange({ templateName: t?.name ?? "", templateLanguage: t?.language ?? "en_US" });
                }}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Select a template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.name} disabled={!t.is_usable}>
                    {t.name} · {t.language}{t.is_usable ? "" : ` (${t.status})`}
                  </option>
                ))}
              </select>
            )}
            {d.templateName ? <p className="text-xs text-slate-500">Sends <b>{String(d.templateName)}</b> ({String(d.templateLanguage ?? "")}).</p> : null}
          </div>
        )}

        {/* Show link preview for text */}
        {isText && (
          <label className="flex items-start gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={d.showLinkPreview !== false} onChange={(e) => onChange({ showLinkPreview: e.target.checked })} className="mt-0.5 h-4 w-4 rounded border-slate-300" />
            <span>Show link preview <span className="text-slate-400">(renders the first http/https URL in the body)</span></span>
          </label>
        )}
      </div>
    </aside>
  );
}
