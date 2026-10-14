// Server-side allowlist for the Templates proxy. Maps same-origin
// /api/templates/* onto the existing backend GET /templates,
// GET /templates/{id} and the Channel Management sync endpoint
// POST /channels/{id}/templates/sync. Sync logic is NOT duplicated — the
// proxy only forwards to the existing endpoint.

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const STATUS_PATTERN = /^[A-Za-z_]{1,30}$/;
const CATEGORY_PATTERN = /^[A-Za-z_]{1,30}$/;
const LANGUAGE_PATTERN = /^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,8})?$/;

export type ProxyMethod = "GET" | "POST";

export interface TemplateProxyTarget {
  backendPath: string;
  method: ProxyMethod;
  query: URLSearchParams;
}

function positiveInt(value: string | null, fallback: number, maximum: number) {
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return number >= 1 && number <= maximum ? number : null;
}

export function buildTemplateProxyTarget(
  method: string,
  segments: string[],
  params: URLSearchParams,
): TemplateProxyTarget | null {
  const empty = new URLSearchParams();

  // GET /templates — tenant-wide list with filters.
  if (segments.length === 0 && method === "GET") {
    const allowed = new Set([
      "page", "page_size", "channel_id", "status", "category", "language", "search", "include_inactive",
    ]);
    const query = new URLSearchParams();
    for (const key of params.keys()) if (!allowed.has(key)) return null;

    const page = positiveInt(params.get("page"), 1, 1_000_000);
    const pageSize = positiveInt(params.get("page_size"), 20, 100);
    if (page === null || pageSize === null) return null;
    query.set("page", String(page));
    query.set("page_size", String(pageSize));

    const channelId = params.get("channel_id");
    if (channelId !== null) {
      if (!UUID_PATTERN.test(channelId)) return null;
      query.set("channel_id", channelId);
    }
    const status = params.get("status");
    if (status !== null) {
      if (!STATUS_PATTERN.test(status)) return null;
      query.set("status", status);
    }
    const category = params.get("category");
    if (category !== null) {
      if (!CATEGORY_PATTERN.test(category)) return null;
      query.set("category", category);
    }
    const language = params.get("language");
    if (language !== null) {
      if (!LANGUAGE_PATTERN.test(language)) return null;
      query.set("language", language);
    }
    const search = params.get("search");
    if (search !== null) {
      if (search.length > 100) return null;
      if (search) query.set("search", search);
    }
    const includeInactive = params.get("include_inactive");
    if (includeInactive !== null) {
      if (includeInactive !== "true" && includeInactive !== "false") return null;
      query.set("include_inactive", includeInactive);
    }
    return { backendPath: "/templates", method: "GET", query };
  }

  if (segments.length === 1 && method === "GET" && params.size === 0 && UUID_PATTERN.test(segments[0])) {
    return { backendPath: `/templates/${segments[0]}`, method: "GET", query: empty };
  }

  // POST /templates — create a local (draft) template.
  if (segments.length === 0 && method === "POST" && params.size === 0) {
    return { backendPath: "/templates", method: "POST", query: empty };
  }

  // POST /templates/sync/{channel_id} — reuse the existing channel sync.
  if (segments.length === 2 && segments[0] === "sync" && method === "POST" && params.size === 0 && UUID_PATTERN.test(segments[1])) {
    return { backendPath: `/channels/${segments[1]}/templates/sync`, method: "POST", query: empty };
  }

  return null;
}
