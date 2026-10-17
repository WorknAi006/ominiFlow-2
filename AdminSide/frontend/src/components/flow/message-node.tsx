"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { MESSAGE_TYPES } from "@/lib/flows/browser";
import { useBuilder } from "@/components/flow/builder-context";

const CHANNEL_ICON: Record<string, { glyph: string; className: string }> = {
  whatsapp: { glyph: "✆", className: "bg-green-100 text-green-600" },
  instagram: { glyph: "◎", className: "bg-pink-100 text-pink-600" },
  messenger: { glyph: "✉", className: "bg-blue-100 text-blue-600" },
  omnichannel: { glyph: "⊛", className: "bg-violet-100 text-violet-600" },
};

interface OutHandle { id: string; label: string; tone: "default" | "true" | "false" }

function outHandles(messageType: string, data: Record<string, unknown>): OutHandle[] {
  if (messageType === "condition") {
    return [
      { id: "true", label: "True", tone: "true" },
      { id: "false", label: "False", tone: "false" },
    ];
  }
  if (messageType === "button") {
    const buttons = (data.buttons as { id: string; title?: string; kind?: string }[] | undefined) ?? [];
    // Only Custom (quick-reply) buttons create branches; URL / Call buttons
    // open a link or dial and do not continue to another node.
    const reply = buttons.filter((b) => (b.kind ?? "reply") === "reply");
    return reply.length
      ? reply.map((b, i) => ({ id: `btn:${b.id}`, label: b.title || `Button ${i + 1}`, tone: "default" as const }))
      : [{ id: "continue", label: "Continue", tone: "default" }];
  }
  if (messageType === "list") {
    const items = (data.listItems as { id: string; title?: string }[] | undefined) ?? [];
    return items.length
      ? items.map((it, i) => ({ id: `item:${it.id}`, label: it.title || `Item ${i + 1}`, tone: "default" as const }))
      : [{ id: "continue", label: "Continue", tone: "default" }];
  }
  return [{ id: "continue", label: "Continue", tone: "default" }];
}

function preview(messageType: string, data: Record<string, unknown>): string {
  const msg = String(data.message ?? "").trim();
  if (messageType === "condition") {
    const c = (data.condition as { source?: string; operator?: string; value?: string } | undefined) ?? {};
    return `If ${c.source ?? "last_input"} ${c.operator ?? "is"} “${c.value ?? ""}”`;
  }
  if (messageType === "delay") {
    return `Wait ${data.delaySeconds ?? data.delayValue ?? ""} ${data.delaySeconds ? "sec" : String(data.delayUnit ?? "")}`.trim();
  }
  if (messageType === "template") return `Template: ${String(data.templateName ?? data.template_name ?? "—")}`;
  if (messageType === "get_user_data") return msg || `Ask → save to {{${String(data.variable ?? "input")}}}`;
  return msg;
}

const toneDot: Record<string, string> = {
  default: "!border-emerald-400 !bg-emerald-400",
  true: "!border-emerald-500 !bg-emerald-500",
  false: "!border-rose-400 !bg-rose-400",
};

export function MessageNode({ id, data, selected }: NodeProps) {
  const { onEdit, onDuplicate, onDelete } = useBuilder();
  const d = data as Record<string, unknown>;
  const channel = String(d.channel ?? "whatsapp");
  const messageType = String(d.messageType ?? "text");
  const mediaName = d.mediaName ? String(d.mediaName) : "";
  const isStart = Boolean(d.isStart);
  const icon = CHANNEL_ICON[channel] ?? CHANNEL_ICON.whatsapp;
  const typeLabel = MESSAGE_TYPES.find((t) => t.value === messageType)?.label ?? "Text Message";
  const handles = outHandles(messageType, d);
  const body = preview(messageType, d);

  return (
    <div className="group relative">
      {isStart && (
        <div className="absolute -top-7 left-0 flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">▶ Start</div>
      )}
      <div className="absolute -top-7 right-0 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
        <button onClick={() => onEdit(id)} title="Edit" className="rounded bg-white px-1.5 py-0.5 text-xs text-slate-500 shadow hover:text-blue-600">✎</button>
        <button onClick={() => onDuplicate(id)} title="Duplicate" className="rounded bg-white px-1.5 py-0.5 text-xs text-slate-500 shadow hover:text-blue-600">⧉</button>
        {!isStart && <button onClick={() => onDelete(id)} title="Delete" className="rounded bg-white px-1.5 py-0.5 text-xs text-slate-500 shadow hover:text-rose-600">🗑</button>}
      </div>

      {!isStart && <Handle type="target" position={Position.Left} className="!h-3 !w-3 !border-2 !border-slate-300 !bg-white" />}

      <div
        onClick={() => onEdit(id)}
        className={`w-64 cursor-pointer rounded-xl border bg-white shadow-sm transition ${selected ? "border-blue-500 ring-2 ring-blue-100" : "border-slate-200"}`}
      >
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
          <span className={`flex h-7 w-7 items-center justify-center rounded-full text-sm ${icon.className}`}>{icon.glyph}</span>
          <span className="text-sm font-bold text-slate-700">{typeLabel}</span>
        </div>
        <div className="px-4 py-3">
          {body ? (
            <p className="line-clamp-3 text-sm text-slate-700">{body}</p>
          ) : mediaName ? (
            <p className="text-sm text-slate-500">📎 {mediaName}</p>
          ) : (
            <p className="rounded-md border border-dashed border-slate-200 px-3 py-2 text-sm italic text-slate-400">No message — click to edit</p>
          )}
        </div>
        {/* One source handle per branch, rendered inline on the right. */}
        <div className="border-t border-slate-100">
          {handles.map((h) => (
            <div key={h.id} className="flex items-center justify-end gap-2 px-4 py-1.5 text-sm font-medium text-slate-500">
              {h.label}
              <Handle
                type="source"
                position={Position.Right}
                id={h.id}
                className={`!relative !right-0 !top-0 !transform-none !h-3 !w-3 !border-2 ${toneDot[h.tone]}`}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
