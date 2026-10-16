"use client";

import { useState } from "react";
import { generateTemplatesAi, type AiTemplateDraft } from "@/lib/templates/browser";

export const AI_TEMPLATE_DRAFT_KEY = "omniflow:ai-template-draft";

const CATEGORIES = ["Any", "MARKETING", "UTILITY", "AUTHENTICATION"];
const LANGUAGES = [
  { label: "English (en_US)", value: "en_US" },
  { label: "Hindi (hi)", value: "hi" },
  { label: "Spanish (es)", value: "es" },
];

export function AiTemplateModal({
  open,
  onClose,
  onUse,
}: {
  open: boolean;
  onClose: () => void;
  onUse: (draft: AiTemplateDraft) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const [category, setCategory] = useState("Any");
  const [language, setLanguage] = useState("en_US");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [drafts, setDrafts] = useState<AiTemplateDraft[]>([]);
  const [creditsUsed, setCreditsUsed] = useState<number | null>(null);

  if (!open) return null;

  async function generate() {
    if (prompt.trim().length < 3) {
      setError("Describe what the template is for (at least a few words).");
      return;
    }
    setLoading(true);
    setError("");
    setDrafts([]);
    setCreditsUsed(null);
    try {
      const res = await generateTemplatesAi({
        prompt: prompt.trim(),
        count: 10,
        category: category === "Any" ? null : category,
        language,
      });
      setDrafts(res.items);
      setCreditsUsed(res.credits_used);
      if (res.items.length === 0) setError("No templates were generated. Try a different description.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate templates.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-3xl max-h-[88vh] overflow-hidden rounded-2xl bg-white shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#aa42d4] text-white">✦</span>
            <h3 className="text-lg font-bold text-slate-900">Create with AI</h3>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">✕</button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          <label className="block text-sm font-bold text-slate-700 mb-2">Describe your template</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            maxLength={1000}
            placeholder="e.g. A festive Diwali sale announcement with a discount code and a shop-now button, plus a utility order-confirmation."
            className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-800 outline-none focus:border-[#aa42d4] focus:ring-1 focus:ring-[#aa42d4] resize-none"
          />
          <div className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                {CATEGORIES.map((c) => <option key={c} value={c}>{c === "Any" ? "Any" : c.charAt(0) + c.slice(1).toLowerCase()}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Language</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
          </div>

          {error && <div className="mt-3 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-800">{error}</div>}

          <button
            onClick={() => void generate()}
            disabled={loading}
            className="mt-4 flex items-center gap-2 rounded-lg bg-[#aa42d4] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#9333c0] disabled:opacity-60"
          >
            {loading ? "Generating 10 templates…" : drafts.length ? "Regenerate" : "✦ Generate 10 templates"}
          </button>

          {creditsUsed !== null && (
            <p className="mt-2 text-xs text-slate-400">Used {creditsUsed.toFixed(2)} AI credits.</p>
          )}

          {drafts.length > 0 && (
            <div className="mt-5 space-y-3">
              <p className="text-sm font-bold text-slate-700">Pick one to edit:</p>
              {drafts.map((d, i) => (
                <div key={i} className="rounded-xl border border-slate-200 p-4 hover:border-[#aa42d4]/50 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-slate-900 truncate">{d.name}</span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-500 uppercase">{d.category}</span>
                        {d.header_type !== "none" && (
                          <span className="rounded bg-purple-50 px-1.5 py-0.5 text-[10px] font-bold text-purple-600 uppercase">{d.header_type}</span>
                        )}
                      </div>
                      {d.header_text && <div className="text-xs font-semibold text-slate-700 mb-1">{d.header_text}</div>}
                      <div className="text-sm text-slate-600 whitespace-pre-wrap line-clamp-4">{d.body_text}</div>
                      {d.footer_text && <div className="mt-1 text-xs text-slate-400">{d.footer_text}</div>}
                      {d.buttons.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {d.buttons.map((b, bi) => (
                            <span key={bi} className="rounded border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600">{b}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => onUse(d)}
                      className="shrink-0 rounded-lg bg-[#00b050] px-3 py-1.5 text-sm font-bold text-white hover:bg-[#009040]"
                    >
                      Use this
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
