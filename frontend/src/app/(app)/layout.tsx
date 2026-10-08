import type { ReactNode } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { AuthBackendUnavailableError, getAuthContext } from "@/lib/auth/session";

export default async function AuthenticatedLayout({ children }: { children: ReactNode }) {
  let context: Awaited<ReturnType<typeof getAuthContext>>;
  try {
    context = await getAuthContext();
  } catch (error) {
    if (!(error instanceof AuthBackendUnavailableError)) throw error;
    return (
      <main className="service-state">
        <div className="service-state-card">
          <span className="status-dot" aria-hidden="true" />
          <p className="eyebrow mt-5">CONNECTION INTERRUPTED</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Your workspace is temporarily unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">We could not confirm your session with the service. Your workspace data remains hidden. Please try again shortly.</p>
          <a href="/dashboard" className="primary-link mt-6">Try again</a>
        </div>
      </main>
    );
  }

  if (!context) redirect("/login?reason=session-expired");
  return <AppShell user={context.user} tenant={context.tenant}>{children}</AppShell>;
}
