// Server-side allowlist for the Tags proxy. Mirrors the contacts proxy:
// only enumerated backend paths, methods and request shapes are forwarded.
// The backend remains the authority on validation.

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const COLOR_PATTERN = /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/;

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface TagProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function name(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length >= 1 && trimmed.length <= 60 ? trimmed : null;
}

function color(value: unknown): string | null {
  if (typeof value !== "string" || !COLOR_PATTERN.test(value)) return null;
  return value;
}

export function buildTagProxyTarget(
  method: string,
  segments: string[],
  body?: unknown,
): TagProxyTarget | null {
  const empty = new URLSearchParams();

  if (segments.length === 0) {
    if (method === "GET") {
      return { backendPath: "/tags", method: "GET", query: empty };
    }
    if (method === "POST") {
      if (!isRecord(body)) return null;
      const tagName = name(body.name);
      if (!tagName) return null;
      const out: Record<string, unknown> = { name: tagName };
      if ("color" in body) {
        const c = color(body.color);
        if (!c) return null;
        out.color = c;
      }
      return { backendPath: "/tags", method: "POST", query: empty, body: out };
    }
    return null;
  }

  const id = segments[0];
  if (segments.length === 1 && UUID_PATTERN.test(id)) {
    if (method === "PATCH") {
      if (!isRecord(body)) return null;
      const out: Record<string, unknown> = {};
      if ("name" in body) {
        const tagName = name(body.name);
        if (!tagName) return null;
        out.name = tagName;
      }
      if ("color" in body) {
        const c = color(body.color);
        if (!c) return null;
        out.color = c;
      }
      if (Object.keys(out).length === 0) return null;
      return { backendPath: `/tags/${id}`, method: "PATCH", query: empty, body: out };
    }
    if (method === "DELETE") {
      return { backendPath: `/tags/${id}`, method: "DELETE", query: empty };
    }
  }

  return null;
}
