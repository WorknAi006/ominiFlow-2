import { redirect } from "next/navigation";

import { PasswordResetAdmin } from "@/components/auth/password-reset-admin";
import { getAuthContext } from "@/lib/auth/session";

export default async function PasswordResetAdminPage() {
  const context = await getAuthContext();
  if (!context) redirect("/login?reason=session-expired");
  if (!context.user.is_platform_super_admin) redirect("/dashboard");

  return (
    <main className="mx-auto w-full max-w-4xl p-5 md:p-8">
      <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">Platform administration</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">Password reset requests</h1>
      <p className="mt-2 text-sm text-slate-600">Review account recovery requests from Omniflow users.</p>
      <PasswordResetAdmin />
    </main>
  );
}
