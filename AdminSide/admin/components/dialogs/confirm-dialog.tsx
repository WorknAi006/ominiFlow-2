"use client";

import React from "react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm Action",
  cancelLabel = "Cancel",
  isDestructive = false,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-[#0f172a] border border-slate-800 rounded-xl p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-3">
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0 ${
              isDestructive
                ? "bg-rose-500/10 border border-rose-500/30 text-rose-400"
                : "bg-sky-500/10 border border-sky-500/30 text-sky-400"
            }`}
          >
            {isDestructive ? "⚠️" : "ℹ️"}
          </div>
          <h3 className="text-base font-semibold text-white">{title}</h3>
        </div>

        <p className="text-xs text-slate-400 mb-6 leading-relaxed">
          {description}
        </p>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800/80">
          <button
            type="button"
            disabled={isLoading}
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-2 ${
              isDestructive
                ? "bg-rose-600 hover:bg-rose-500 text-white shadow-sm shadow-rose-950"
                : "bg-sky-600 hover:bg-sky-500 text-white shadow-sm shadow-sky-950"
            }`}
          >
            {isLoading && (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            <span>{confirmLabel}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
