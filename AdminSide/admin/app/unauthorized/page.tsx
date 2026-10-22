"use client";

import Link from "next/link";
import { useAdminAuth } from "../../lib/auth/context";

export default function UnauthorizedPage() {
  const { logout } = useAdminAuth();

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070b14] p-4 text-center">
      <div className="w-full max-w-md bg-[#0f172a] border border-slate-800 rounded-xl p-8 shadow-2xl">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
          <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>

        <h1 className="text-xl font-bold text-white mb-2">403 — Privileged Access Denied</h1>
        <p className="text-sm text-slate-400 mb-6">
          Your credentials were authenticated, but your account lacks Platform Super Admin privileges. Regular tenant members cannot access the Omniflow Control Plane.
        </p>

        <div className="space-y-3">
          <button
            onClick={logout}
            className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition-colors"
          >
            Sign in with Super Admin Account
          </button>
          <a
            href={process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"}
            className="block w-full py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition-colors"
          >
            Go to Customer Application
          </a>
        </div>
      </div>
    </div>
  );
}
