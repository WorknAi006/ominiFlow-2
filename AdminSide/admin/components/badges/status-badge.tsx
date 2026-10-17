import React from "react";

export function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();

  if (s === "active" || s === "connected" || s === "healthy" || s === "open" || s === "success") {
    return (
      <span className="admin-badge admin-badge-success">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        {status}
      </span>
    );
  }

  if (s === "pending" || s === "warning" || s === "pending_integration") {
    return (
      <span className="admin-badge admin-badge-warning">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        {status}
      </span>
    );
  }

  if (s === "suspended" || s === "disconnected" || s === "error" || s === "failed" || s === "down" || s === "closed") {
    return (
      <span className="admin-badge admin-badge-danger">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
        {status}
      </span>
    );
  }

  return (
    <span className="admin-badge admin-badge-neutral">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
      {status}
    </span>
  );
}
