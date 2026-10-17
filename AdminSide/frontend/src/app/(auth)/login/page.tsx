import { LoginView } from "@/components/auth/login-view";
import { safeInternalPath } from "@/lib/auth/session-utils";
import { redirect } from "next/navigation";

interface LoginPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export const metadata = {
  title: "Sign in — Omniflow",
  description: "Sign in to your Omniflow workspace",
  referrer: "no-referrer",
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const hasCredentialQuery = Object.keys(params).some((key) =>
    /(email|password|passwd|token|secret|authorization|credential|api[_-]?key)/i.test(key),
  );
  if (hasCredentialQuery) redirect("/login");

  const destination = safeInternalPath(typeof params.next === "string" ? params.next : undefined);
  const registered = params.registered === "1";
  const sessionExpired = params.reason === "session-expired";

  return (
    <LoginView
      destination={destination}
      registered={registered}
      sessionExpired={sessionExpired}
    />
  );
}
