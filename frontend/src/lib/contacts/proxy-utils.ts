// Server-side allowlist for the Contacts proxy. Mirrors the channels proxy:
// only enumerated backend paths, methods, filters and request shapes are
// forwarded. The backend remains the authority on phone/email validation
// (its sanitized 422 messages are passed back to the client).

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface ContactProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
  body?: Record<string, unknown>;
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

function paginated(params: URLSearchParams, allowed: Set<string>): URLSearchParams | null {
  const query = new URLSearchParams();
  for (const key of params.keys()) if (!allowed.has(key)) return null;
  const page = positiveInt(params.get("page"), 1, 1_000_000);
  const pageSize = positiveInt(params.get("page_size"), 20, 100);
  if (page === null || pageSize === null) return null;
  query.set("page", String(page));
  query.set("page_size", String(pageSize));
  return query;
}

const NAME_FIELDS: Record<string, number> = {
  first_name: 100,
  last_name: 100,
  display_name: 150,
};

function buildCreateBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["phone_number", "email", "first_name", "last_name", "display_name"]);
  for (const key of Object.keys(body)) if (!allowed.has(key)) return null;

  const out: Record<string, unknown> = {};
  if ("phone_number" in body) {
    if (typeof body.phone_number !== "string") return null;
    const value = body.phone_number.trim();
    if (value.length < 1 || value.length > 32) return null;
    out.phone_number = value;
  }
  if ("email" in body) {
    if (typeof body.email !== "string") return null;
    const value = body.email.trim();
    if (value.length < 3 || value.length > 320) return null;
    out.email = value;
  }
  for (const [field, max] of Object.entries(NAME_FIELDS)) {
    if (!(field in body)) continue;
    if (typeof body[field] !== "string") return null;
    const value = (body[field] as string).trim();
    if (value.length < 1 || value.length > max) return null;
    out[field] = value;
  }
  if (out.phone_number === undefined && out.email === undefined) return null;
  return out;
}

function buildUpdateBody(body: unknown): Record<string, unknown> | null {
  if (!isRecord(body)) return null;
  const allowed = new Set(["phone_number", "email", "first_name", "last_name", "display_name", "is_blocked"]);
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  for (const key of keys) if (!allowed.has(key)) return null;

  const out: Record<string, unknown> = {};
  if ("phone_number" in body) {
    if (typeof body.phone_number !== "string") return null; // phone cannot be cleared to null
    const value = body.phone_number.trim();
    if (value.length < 1 || value.length > 32) return null;
    out.phone_number = value;
  }
  if ("email" in body) {
    if (body.email === null) out.email = null;
    else if (typeof body.email === "string") {
      const value = body.email.trim();
      if (value.length < 3 || value.length > 320) return null;
      out.email = value;
    } else return null;
  }
  for (const [field, max] of Object.entries(NAME_FIELDS)) {
    if (!(field in body)) continue;
    if (body[field] === null) out[field] = null;
    else if (typeof body[field] === "string") {
      const value = (body[field] as string).trim();
      if (value.length < 1 || value.length > max) return null;
      out[field] = value;
    } else return null;
  }
  if ("is_blocked" in body) {
    if (typeof body.is_blocked !== "boolean") return null;
    out.is_blocked = body.is_blocked;
  }
  return out;
}

function uuidList(value: unknown, max: number): string[] | null {
  if (!Array.isArray(value) || value.length > max) return null;
  const out: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !UUID_PATTERN.test(item)) return null;
    out.push(item);
  }
  return out;
}

function listFilters(params: URLSearchParams): URLSearchParams | null {
  const query = paginated(params, new Set(["page", "page_size", "search", "phone", "tag_id", "channel_type", "source"]));
  if (!query) return null;
  for (const key of ["search", "phone"] as const) {
    const value = params.get(key);
    if (value === null) continue;
    const max = key === "search" ? 100 : 32;
    if (value.length > max) return null;
    if (value) query.set(key, value);
  }
  const tagId = params.get("tag_id");
  if (tagId !== null) {
    if (!UUID_PATTERN.test(tagId)) return null;
    query.set("tag_id", tagId);
  }
  const channel = params.get("channel_type");
  if (channel !== null) {
    if (channel.length > 20 || !/^[a-z_]+$/.test(channel)) return null;
    query.set("channel_type", channel);
  }
  const source = params.get("source");
  if (source !== null) {
    if (source !== "inbox" && source !== "manual") return null;
    query.set("source", source);
  }
  return query;
}

export function buildContactProxyTarget(
  method: string,
  segments: string[],
  params: URLSearchParams,
  body?: unknown,
): ContactProxyTarget | null {
  const empty = new URLSearchParams();

  if (segments.length === 0) {
    if (method === "GET") {
      const query = listFilters(params);
      if (!query) return null;
      return { backendPath: "/contacts", method: "GET", query };
    }
    if (method === "POST") {
      const created = buildCreateBody(body);
      if (!created) return null;
      return { backendPath: "/contacts", method: "POST", query: empty, body: created };
    }
    return null;
  }

  // ---- collection-level literal routes (before the UUID check) ----
  const first = segments[0];

  if (first === "export" && segments.length === 1 && method === "GET") {
    const query = new URLSearchParams();
    for (const [key, max] of [["search", 100], ["channel_type", 20]] as const) {
      const value = params.get(key);
      if (value === null) continue;
      if (value.length > max) return null;
      if (key === "channel_type" && value && !/^[a-z_]+$/.test(value)) return null;
      if (value) query.set(key, value);
    }
    const tagId = params.get("tag_id");
    if (tagId !== null) {
      if (!UUID_PATTERN.test(tagId)) return null;
      query.set("tag_id", tagId);
    }
    return { backendPath: "/contacts/export", method: "GET", query };
  }

  if (first === "bulk-delete" && segments.length === 1 && method === "POST") {
    if (!isRecord(body)) return null;
    const ids = uuidList(body.contact_ids, 500);
    if (!ids || ids.length === 0) return null;
    return { backendPath: "/contacts/bulk-delete", method: "POST", query: empty, body: { contact_ids: ids } };
  }

  if (first === "tags" && segments.length === 1 && method === "POST") {
    if (!isRecord(body)) return null;
    const contactIds = uuidList(body.contact_ids, 500);
    const add = body.add_tag_ids === undefined ? [] : uuidList(body.add_tag_ids, 100);
    const remove = body.remove_tag_ids === undefined ? [] : uuidList(body.remove_tag_ids, 100);
    if (!contactIds || contactIds.length === 0 || add === null || remove === null) return null;
    return {
      backendPath: "/contacts/tags", method: "POST", query: empty,
      body: { contact_ids: contactIds, add_tag_ids: add, remove_tag_ids: remove },
    };
  }

  if (first === "all" && segments.length === 2 && segments[1] === "delete" && method === "POST") {
    if (!isRecord(body) || typeof body.confirm !== "string" || body.confirm.length > 20) return null;
    return { backendPath: "/contacts/all/delete", method: "POST", query: empty, body: { confirm: body.confirm } };
  }

  if (first === "import" && segments.length === 1 && method === "POST") {
    if (!isRecord(body) || !Array.isArray(body.rows) || body.rows.length === 0 || body.rows.length > 2000) return null;
    const allowed = new Set(["first_name", "last_name", "display_name", "phone_number", "email"]);
    const rows: Record<string, unknown>[] = [];
    for (const raw of body.rows) {
      if (!isRecord(raw)) return null;
      const out: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(raw)) {
        if (!allowed.has(k)) continue;
        if (v === null || v === undefined) continue;
        if (typeof v !== "string" || v.length > 320) return null;
        out[k] = v;
      }
      rows.push(out);
    }
    return { backendPath: "/contacts/import", method: "POST", query: empty, body: { rows } };
  }

  const id = segments[0];
  if (!UUID_PATTERN.test(id)) return null;

  if (segments.length === 1) {
    if (method === "GET" && params.size === 0) {
      return { backendPath: `/contacts/${id}`, method: "GET", query: empty };
    }
    if (method === "PATCH") {
      const updated = buildUpdateBody(body);
      if (!updated) return null;
      return { backendPath: `/contacts/${id}`, method: "PATCH", query: empty, body: updated };
    }
    if (method === "DELETE") {
      return { backendPath: `/contacts/${id}`, method: "DELETE", query: empty };
    }
    return null;
  }

  if (segments.length === 2 && segments[1] === "tags" && method === "POST") {
    if (!isRecord(body)) return null;
    const tagIds = uuidList(body.tag_ids, 100);
    if (tagIds === null) return null;
    return { backendPath: `/contacts/${id}/tags`, method: "POST", query: empty, body: { tag_ids: tagIds } };
  }

  if (segments.length === 2 && segments[1] === "fields" && method === "POST") {
    if (!isRecord(body) || !isRecord(body.values)) return null;
    const values: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(body.values)) {
      if (!UUID_PATTERN.test(k)) return null;
      values[k] = v; // value shape is validated by the backend per field type
    }
    return { backendPath: `/contacts/${id}/fields`, method: "POST", query: empty, body: { values } };
  }

  // A contact's related conversations, resolved through the tenant-scoped
  // conversations endpoint (contact_id filter). Navigation into a thread
  // reuses the existing /inbox routing on the client.
  if (segments.length === 2 && segments[1] === "conversations" && method === "GET") {
    const query = paginated(params, new Set(["page", "page_size"]));
    if (!query) return null;
    query.set("contact_id", id);
    return { backendPath: "/conversations", method: "GET", query };
  }

  return null;
}
