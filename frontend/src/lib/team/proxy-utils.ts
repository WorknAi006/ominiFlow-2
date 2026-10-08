// Server-side allowlist for the Team Management proxy. Maps the same-origin
// /api/team/* paths onto the existing backend /users, /users/invite,
// /users/invitations and /roles endpoints. Only enumerated shapes pass; the
// backend stays the authority on RBAC, owner protection and validation.

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const MEMBERSHIP_STATUSES = ["active", "suspended"] as const;

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface TeamProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
  expectsNoContent?: boolean;
  // Response fields the route must strip before returning to the browser.
  redact?: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function positiveInt(value: string | null, fallback: number, maximum: number) {
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= maximum ? number : null;
}

function listQuery(params: URLSearchParams): URLSearchParams | null {
  const allowed = new Set(["page", "page_size", "search"]);
  const query = new URLSearchParams();
  for (const key of params.keys()) if (!allowed.has(key)) return null;
  const page = positiveInt(params.get("page"), 1, 1_000_000);
  const pageSize = positiveInt(params.get("page_size"), 20, 100);
  if (page === null || pageSize === null) return null;
  query.set("page", String(page));
  query.set("page_size", String(pageSize));
  const search = params.get("search");
  if (search !== null) {
    if (search.length > 100) return null;
    if (search) query.set("search", search);
  }
  return query;
}

function buildInviteBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const keys = Object.keys(body);
  if (keys.length !== 2 || !("email" in body) || !("role_id" in body)) return null;
  if (typeof body.email !== "string") return null;
  const email = body.email.trim().toLowerCase();
  if (email.length < 3 || email.length > 320 || !email.includes("@")) return null;
  if (typeof body.role_id !== "string" || !UUID_PATTERN.test(body.role_id)) return null;
  return { email, role_id: body.role_id };
}

function buildUpdateBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["role_id", "status"]);
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  for (const key of keys) if (!allowed.has(key)) return null;
  const out: Record<string, unknown> = {};
  if ("role_id" in body) {
    if (typeof body.role_id !== "string" || !UUID_PATTERN.test(body.role_id)) return null;
    out.role_id = body.role_id;
  }
  if ("status" in body) {
    if (typeof body.status !== "string" || !(MEMBERSHIP_STATUSES as readonly string[]).includes(body.status)) return null;
    out.status = body.status;
  }
  return out;
}

export function buildTeamProxyTarget(
  method: string,
  segments: string[],
  params: URLSearchParams,
  body?: unknown,
): TeamProxyTarget | null {
  const empty = new URLSearchParams();

  if (segments.length === 0) {
    if (method === "GET") {
      const query = listQuery(params);
      if (!query) return null;
      return { backendPath: "/users", method: "GET", query };
    }
    return null;
  }

  if (segments.length === 1) {
    const [first] = segments;
    if (first === "roles" && method === "GET" && params.size === 0) {
      return { backendPath: "/roles", method: "GET", query: empty };
    }
    if (first === "invitations" && method === "GET" && params.size === 0) {
      return { backendPath: "/users/invitations", method: "GET", query: empty, redact: ["invitation_token"] };
    }
    if (first === "invite" && method === "POST" && params.size === 0) {
      const invite = buildInviteBody(body);
      if (!invite) return null;
      // The invitation token is never surfaced to the browser.
      return { backendPath: "/users/invite", method: "POST", query: empty, body: invite, redact: ["invitation_token"] };
    }
    if (UUID_PATTERN.test(first)) {
      if (method === "PATCH") {
        const update = buildUpdateBody(body);
        if (!update) return null;
        return { backendPath: `/users/${first}`, method: "PATCH", query: empty, body: update };
      }
      if (method === "DELETE" && params.size === 0) {
        return { backendPath: `/users/${first}`, method: "DELETE", query: empty, expectsNoContent: true };
      }
    }
    return null;
  }

  if (
    segments.length === 2 &&
    segments[0] === "invitations" &&
    UUID_PATTERN.test(segments[1]) &&
    method === "DELETE" &&
    params.size === 0
  ) {
    return { backendPath: `/users/invitations/${segments[1]}`, method: "DELETE", query: empty, expectsNoContent: true };
  }

  return null;
}
