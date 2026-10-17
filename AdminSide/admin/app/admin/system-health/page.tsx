import { cookies } from "next/headers";
import { AdminSystemHealth } from "../../../lib/types/admin";
import { SystemHealthClient } from "./system-health-client";

async function fetchSystemHealthServer(): Promise<{ health: AdminSystemHealth | null; error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get("omniflow_admin_token")?.value;
  const baseUrl = (process.env.OMNIFLOW_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

  try {
    const res = await fetch(`${baseUrl}/api/v1/admin/system-health`, {
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      return { health: null, error: `System health probe returned status ${res.status}` };
    }

    const data: AdminSystemHealth = await res.json();
    return { health: data, error: null };
  } catch {
    return { health: null, error: "Backend API is currently unreachable. Ensure backend service is running." };
  }
}

export default async function SystemHealthPage() {
  const { health, error } = await fetchSystemHealthServer();
  return <SystemHealthClient initialHealth={health} initialError={error} />;
}
