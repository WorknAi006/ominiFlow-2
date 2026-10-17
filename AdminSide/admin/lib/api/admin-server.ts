import { cookies } from "next/headers";

const API_BASE = (
  process.env.OMNIFLOW_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function fetchAdminServer<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T | null> {
  let token: string | undefined;
  try {
    const cookieStore = await cookies();
    token = cookieStore.get("omniflow_admin_token")?.value;
  } catch {
    // If called outside request context
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/admin${endpoint}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
      cache: "no-store",
    });

    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
