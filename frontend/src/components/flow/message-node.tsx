"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { MESSAGE_TYPES } from "@/lib/flows/browser";
import { useBuilder } from "@/components/flow/builder-context";

const CHANNEL_ICON: Record<string, { glyph: string; badgeClass: string }> = {
  whatsapp: { glyph: "WhatsApp", badgeClass: "bg-emerald-50 text-emerald-600 border-emerald-200" },
  instagram: { glyph: "Instagram", badgeClass: "bg-pink-50 text-pink-600 border-pink-200" },
  messenger: { glyph: "Messenger", badgeClass: "bg-blue-50 text-blue-600 border-blue-200" },
  omnichannel: { glyph: "Omnichannel", badgeClass: "bg-violet-50 text-violet-600 border-violet-200" },
};

export function MessageNode({ id, data, selected }: NodeProps) {
  const { onEdit, onDuplicate, onDelete } = useBuilder();
  const d = (data || {}) as Record<string, unknown>;
  const channel = String(d.channel ?? "whatsapp");
  const messageType = String(d.messageType ?? "text");
  const isStart = Boolean(d.isStart);
  const typeLabel = MESSAGE_TYPES.find((t) => t.value === messageType)?.label ?? "Text Message";
  
  const buttons = (d.buttons as { id: string; title?: string; kind?: string; url?: string; phoneNumber?: string }[] | undefined) ?? [];
  const listItems = (d.listItems as { id: string; title?: string; description?: string }[] | undefined) ?? [];
  const header = (d.header as { type?: string; text?: string; mediaName?: string } | undefined) ?? {};
  const mediaName = d.mediaName ? String(d.mediaName) : "";
  const mediaUrl = d.mediaUrl ? String(d.mediaUrl) : "";
  const footer = d.footer ? String(d.footer).trim() : "";
  const rawMsg = String(d.message ?? "").trim();
  const condition = (d.condition as { source?: string; operator?: string; value?: string } | undefined) ?? {};

  return (
    <div className="group relative">
      {/* Start Node Badge */}
      {isStart && (
        <div className="absolute -top-7 left-0 flex items-center gap-1.5 rounded-full bg-emerald-600 px-2.5 py-0.5 text-xs font-semibold text-white shadow-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
          <span>Start</span>
        </div>
      )}

      {/* Target Connection Handle (Input) */}
      {!isStart && (
        <Handle
          type="target"
          position={Position.Left}
          className="!h-3.5 !w-3.5 !-left-2 !border-2 !border-slate-400 !bg-white hover:!border-blue-600 transition-colors shadow-sm"
        />
      )}

      {/* Node Card */}
      <div
        onClick={() => onEdit(id)}
        className={`w-72 sm:w-80 cursor-pointer rounded-2xl border bg-white shadow-sm transition-all duration-150 hover:shadow-md ${
          selected
            ? "border-blue-500 ring-2 ring-blue-500/20 shadow-blue-500/5"
            : "border-slate-200/90 hover:border-slate-300"
        }`}
      >
        {/* Card Header */}
        <div className="flex items-center justify-between border-b border-slate-100/80 px-3.5 py-2.5 bg-slate-50/60 rounded-t-2xl">
          <div className="flex items-center gap-2 min-w-0">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-emerald-100/70 text-emerald-700 text-xs">
              💬
            </span>
            <span className="text-xs font-bold text-slate-800 truncate">{typeLabel}</span>
          </div>

          {/* Quick Actions (Hover toolbar) */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onEdit(id); }}
              title="Edit Node"
              className="rounded p-1 text-slate-400 hover:bg-slate-200/70 hover:text-blue-600 transition"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDuplicate(id); }}
              title="Duplicate Node"
              className="rounded p-1 text-slate-400 hover:bg-slate-200/70 hover:text-blue-600 transition"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
            {!isStart && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onDelete(id); }}
                title="Delete Node"
                className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            )}
          </div>
        </div>

        {/* Card Content */}
        <div className="p-3.5 space-y-2.5">
          {/* Header if configured */}
          {header.type && header.type !== "none" && (
            <div className="rounded-lg bg-slate-50 border border-slate-100 px-2.5 py-1.5 text-xs text-slate-600">
              {header.type === "text" && header.text ? (
                <span className="font-bold text-slate-900">{header.text}</span>
              ) : (
                <span className="font-medium text-slate-500 capitalize">📎 {header.type} Header</span>
              )}
            </div>
          )}

          {/* Media preview badge */}
          {mediaName && (
            <div className="flex items-center gap-2 rounded-lg bg-blue-50/70 border border-blue-100/70 p-2 text-xs text-blue-800">
              <span className="text-base">📄</span>
              <span className="truncate flex-1 font-medium">{mediaName}</span>
            </div>
          )}

          {/* Message Text */}
          {messageType === "condition" ? (
            <div className="rounded-lg bg-amber-50/70 border border-amber-100 p-2.5 text-xs text-amber-900 font-medium">
              If <span className="font-bold text-amber-950">{condition.source ?? "last_input"}</span> {condition.operator ?? "is"} &ldquo;{condition.value ?? ""}&rdquo;
            </div>
          ) : messageType === "delay" ? (
            <div className="flex items-center gap-2 rounded-lg bg-slate-50 border border-slate-200/80 p-2.5 text-xs text-slate-700">
              <span>⏱</span>
              <span className="font-medium">Wait {String(d.delayValue ?? d.delaySeconds ?? 1)} {String(d.delayUnit ?? (d.delaySeconds ? "sec" : "minutes"))}</span>
            </div>
          ) : messageType === "template" ? (
            <div className="rounded-lg bg-emerald-50/70 border border-emerald-100 p-2 text-xs text-emerald-800">
              <span className="font-bold">Template:</span> {String(d.templateName ?? d.template_name ?? "None selected")}
            </div>
          ) : messageType === "get_user_data" ? (
            <div className="space-y-1">
              <p className="line-clamp-2 text-xs text-slate-700">{rawMsg || "Question prompt..."}</p>
              <div className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                Save → {`{{${String(d.variable ?? "reply")}}}`}
              </div>
            </div>
          ) : messageType === "external_api" ? (
            <div className="rounded-lg bg-sky-50/70 border border-sky-100 p-2.5 text-xs text-sky-950 font-medium space-y-1">
              <div className="flex items-center gap-1.5 font-bold">
                <span className="rounded bg-sky-200 px-1.5 py-0.5 text-[10px] text-sky-800 uppercase">{String(d.apiMethod ?? "GET")}</span>
                <span className="truncate flex-1">{String(d.apiUrl || "https://api.example.com")}</span>
              </div>
              {d.responseVariable ? (
                <span className="text-[10px] text-sky-600 block">Saves to: <code>{`{{${String(d.responseVariable)}}}`}</code></span>
              ) : null}
            </div>
          ) : messageType === "actions" ? (
            <div className="rounded-lg bg-violet-50/70 border border-violet-100 p-2.5 text-xs text-violet-900 font-medium space-y-1">
              <span className="font-bold flex items-center gap-1">⚙ Actions</span>
              {Array.isArray(d.actions) && d.actions.length > 0 ? (
                <ul className="list-disc list-inside text-[11px] text-violet-700">
                  {(d.actions as { type?: string; config?: { value?: string; key?: string } }[]).slice(0, 3).map((a, i) => (
                    <li key={i} className="truncate">{a.type?.replace("_", " ")}: {a.config?.value || a.config?.key || "configured"}</li>
                  ))}
                  {d.actions.length > 3 && <li>+{d.actions.length - 3} more...</li>}
                </ul>
              ) : (
                <p className="text-[11px] italic text-violet-500">Click to configure actions</p>
              )}
            </div>
          ) : messageType === "send_email" ? (
            <div className="rounded-lg bg-rose-50/70 border border-rose-100 p-2.5 text-xs text-rose-900 font-medium space-y-1">
              <div className="font-bold">✉ Send Email</div>
              <div className="text-[11px] text-rose-700 truncate">To: {String(d.emailTo || "user@example.com")}</div>
              {d.emailSubject ? <div className="text-[11px] text-rose-600 truncate">Subject: {String(d.emailSubject)}</div> : null}
            </div>
          ) : messageType === "razorpay" ? (
            <div className="rounded-lg bg-emerald-50/80 border border-emerald-100 p-2.5 text-xs text-emerald-950 font-medium space-y-1">
              <div className="flex items-center justify-between font-bold">
                <span>💳 Razorpay Payment</span>
                <span className="rounded bg-emerald-200 px-1.5 py-0.5 text-[10px] text-emerald-800">{String(d.currency ?? "INR")} {String(d.amount ?? 100)}</span>
              </div>
              <p className="text-[11px] text-emerald-700 truncate">{String(d.description || "Payment Request")}</p>
            </div>
          ) : messageType === "whatsapp_form" ? (
            <div className="rounded-lg bg-teal-50/80 border border-teal-100 p-2.5 text-xs text-teal-950 font-medium space-y-1">
              <span className="font-bold flex items-center gap-1">📋 WhatsApp Form</span>
              <p className="text-[11px] text-teal-700 truncate">{String(d.formTitle || "Interactive Intake Form")}</p>
            </div>
          ) : messageType === "zoho_crm" ? (
            <div className="rounded-lg bg-amber-50/80 border border-amber-100 p-2.5 text-xs text-amber-950 font-medium space-y-1">
              <span className="font-bold flex items-center gap-1">👥 Zoho CRM Lead</span>
              <p className="text-[11px] text-amber-700 truncate">Lead: {String(d.leadName || "{{contact_name}}")}</p>
            </div>
          ) : messageType === "carousel" ? (
            <div className="rounded-lg bg-indigo-50/80 border border-indigo-100 p-2.5 text-xs text-indigo-950 font-medium space-y-1">
              <span className="font-bold flex items-center gap-1">🎠 Carousel Template</span>
              <p className="text-[11px] text-indigo-700 truncate">{String(d.templateName || "Select carousel template")}</p>
            </div>
          ) : rawMsg ? (
            <p className="line-clamp-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap">{rawMsg}</p>
          ) : (
            <p className="rounded-lg border border-dashed border-slate-200 px-3 py-2 text-xs italic text-slate-400 text-center">
              No message — click to edit
            </p>
          )}

          {/* Footer if present */}
          {footer && (
            <p className="text-[11px] text-slate-400 italic truncate border-t border-slate-50 pt-1">
              {footer}
            </p>
          )}

          {/* Buttons preview with individual source handles */}
          {messageType === "button" && buttons.length > 0 && (
            <div className="space-y-1.5 pt-1">
              {buttons.map((b, i) => {
                const isReply = (b.kind ?? "reply") === "reply";
                return (
                  <div
                    key={b.id || i}
                    className="relative flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/40 px-3 py-1.5 text-xs font-semibold text-blue-700 shadow-2xs hover:bg-blue-50 transition"
                  >
                    <span className="truncate flex-1 pr-2">
                      {b.kind === "call" ? "📞 " : b.kind === "url" ? "🔗 " : ""}{b.title || `Button ${i + 1}`}
                      {!isReply && <span className="ml-1 text-[10px] text-blue-400 font-normal">({b.kind})</span>}
                    </span>
                    {isReply && (
                      <Handle
                        type="source"
                        position={Position.Right}
                        id={`btn:${b.id}`}
                        className="!relative !right-0 !top-0 !transform-none !h-3.5 !w-3.5 !border-2 !border-emerald-500 !bg-white hover:!bg-emerald-500 transition shadow-xs"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* List items preview with individual source handles */}
          {messageType === "list" && listItems.length > 0 && (
            <div className="space-y-1.5 pt-1">
              {listItems.map((item, i) => (
                <div
                  key={item.id || i}
                  className="relative flex items-center justify-between rounded-lg border border-slate-200/90 bg-slate-50/70 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100/70 transition"
                >
                  <span className="truncate flex-1 pr-2">{item.title || `Option ${i + 1}`}</span>
                  <Handle
                    type="source"
                    position={Position.Right}
                    id={`item:${item.id}`}
                    className="!relative !right-0 !top-0 !transform-none !h-3.5 !w-3.5 !border-2 !border-emerald-500 !bg-white hover:!bg-emerald-500 transition shadow-xs"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Condition node True / False handles */}
          {messageType === "condition" && (
            <div className="space-y-1.5 pt-1">
              <div className="relative flex items-center justify-between rounded-lg bg-emerald-50 border border-emerald-200/80 px-3 py-1.5 text-xs font-bold text-emerald-700">
                <span>True (Match)</span>
                <Handle
                  type="source"
                  position={Position.Right}
                  id="true"
                  className="!relative !right-0 !top-0 !transform-none !h-3.5 !w-3.5 !border-2 !border-emerald-500 !bg-emerald-500 transition shadow-xs"
                />
              </div>
              <div className="relative flex items-center justify-between rounded-lg bg-rose-50 border border-rose-200/80 px-3 py-1.5 text-xs font-bold text-rose-700">
                <span>False (No match)</span>
                <Handle
                  type="source"
                  position={Position.Right}
                  id="false"
                  className="!relative !right-0 !top-0 !transform-none !h-3.5 !w-3.5 !border-2 !border-rose-400 !bg-rose-400 transition shadow-xs"
                />
              </div>
            </div>
          )}
        </div>

        {/* Bottom Continue Handle (For non-branching nodes or fallback) */}
        {messageType !== "condition" && (
          <div className="border-t border-slate-100 px-3.5 py-1.5 flex items-center justify-end gap-2 text-xs font-medium text-slate-400 bg-slate-50/30 rounded-b-2xl">
            <span>Continue</span>
            <Handle
              type="source"
              position={Position.Right}
              id="continue"
              className="!relative !right-0 !top-0 !transform-none !h-3.5 !w-3.5 !border-2 !border-slate-300 !bg-white hover:!border-emerald-500 hover:!bg-emerald-500 transition shadow-2xs"
            />
          </div>
        )}
      </div>
    </div>
  );
}

