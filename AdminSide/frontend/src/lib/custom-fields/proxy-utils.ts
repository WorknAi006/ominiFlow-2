// Server-side allowlist for the Custom Fields proxy. Only enumerated backend
// paths, methods and request shapes are forwarded; the backend validates.

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const FIELD_TYPES = new Set(["text", "number", "date", "select", "multiselect", "boolean"]);

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface CustomFieldProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function options(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.length > 50) return null;
  const out: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || item.length > 100) return null;
    out.push(item);
  }
  return out;
}

export function buildCustomFieldProxyTarget(
  method: string,
  segments: string[],
  body?: unknown,
): CustomFieldProxyTarget | null {
  const empty = new URLSearchParams();

  if (segments.length === 0) {
    if (method === "GET") return { backendPath: "/custom-fields", method: "GET", query: empty };
    if (method === "POST") {
      if (!isRecord(body)) return null;
      if (typeof body.label !== "string" || body.label.trim().length < 1 || body.label.length > 60) return null;
      if (typeof body.field_type !== "string" || !FIELD_TYPES.has(body.field_type)) return null;
      const out: Record<string, unknown> = { label: body.label.trim(), field_type: body.field_type };
      if ("options" in body && body.options !== null && body.options !== undefined) {
        const opts = options(body.options);
        if (!opts) return null;
        out.options = opts;
      }
      return { backendPath: "/custom-fields", method: "POST", query: empty, body: out };
    }
    return null;
  }

  const id = segments[0];
  if (segments.length === 1 && UUID_PATTERN.test(id)) {
    if (method === "PATCH") {
      if (!isRecord(body)) return null;
      const out: Record<string, unknown> = {};
      if ("label" in body) {
        if (typeof body.label !== "string" || body.label.trim().length < 1 || body.label.length > 60) return null;
        out.label = body.label.trim();
      }
      if ("options" in body) {
        if (body.options === null) out.options = null;
        else { const opts = options(body.options); if (!opts) return null; out.options = opts; }
      }
      if (Object.keys(out).length === 0) return null;
      return { backendPath: `/custom-fields/${id}`, method: "PATCH", query: empty, body: out };
    }
    if (method === "DELETE") return { backendPath: `/custom-fields/${id}`, method: "DELETE", query: empty };
  }

  return null;
}
