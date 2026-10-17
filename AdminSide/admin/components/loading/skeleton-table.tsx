import React from "react";

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="admin-table-container animate-pulse">
      <div className="p-4 bg-[#0b1329] border-b border-slate-800">
        <div className="h-4 w-48 bg-slate-800 rounded" />
      </div>
      <div className="divide-y divide-slate-800/60">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="px-4 py-3.5 flex items-center gap-4">
            {Array.from({ length: cols }).map((_, j) => (
              <div
                key={j}
                className="h-3.5 bg-slate-800/70 rounded"
                style={{ width: `${Math.max(15, (j + 1) * 20)}%` }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
