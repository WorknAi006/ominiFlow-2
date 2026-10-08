// Browser-side client for Team Management. Calls the same-origin Next proxy
// (/api/team/...), which attaches the HttpOnly session token and forwards to
// the backend /users, /users/invite, /users/invitations and /roles APIs.

import type { PaginatedResponse } from "@/lib/api/client";

export const MEMBERSHIP_STATUSES = ["active", "suspended"] as const;
export type MembershipStatus = (typeof MEMBERSHIP_STATUSES)[number];

export interface TeamMember {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  role: string;
  role_id: string;
  membership_status: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  assignable: boolean;
}

/** invitation_token is stripped by the proxy and never reaches the client. */
export interface Invitation {
  id: string;
  email: string;
  role: string;
  role_id: string;
  expires_at: string;
  created_at: string;
}

export class TeamApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "TeamApiError";
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function request<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/team${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new TeamApiError(0, "Could not reach the team service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new TeamApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The team request could not be completed.";
    throw new TeamApiError(response.status, message);
  }
  return payload as T;
}

export function listMembers(params: { page?: number; page_size?: number; search?: string } = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request<PaginatedResponse<TeamMember>>(suffix);
}

export function listRoles() {
  return request<Role[]>("/roles");
}

export function listInvitations() {
  return request<Invitation[]>("/invitations");
}

export function inviteMember(input: { email: string; role_id: string }) {
  return request<Invitation>("/invite", { method: "POST", body: input });
}

export function revokeInvitation(invitationId: string) {
  return request<void>(`/invitations/${encodeURIComponent(invitationId)}`, { method: "DELETE" });
}

export function updateMember(userId: string, input: { role_id?: string; status?: MembershipStatus }) {
  return request<TeamMember>(`/${encodeURIComponent(userId)}`, { method: "PATCH", body: input });
}

export function removeMember(userId: string) {
  return request<void>(`/${encodeURIComponent(userId)}`, { method: "DELETE" });
}
