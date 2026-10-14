const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export type AutomationMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

/**
 * Whitelist the rule-based automation routes the browser may reach through
 * the Next proxy. Anything not listed here is rejected before it leaves the
 * edge.
 */
export function buildAutomationTarget(method: string, segments: string[], params: URLSearchParams) {
  if (!["GET", "POST", "PATCH", "DELETE"].includes(method)) return null;

  const query = new URLSearchParams();
  const allowed = new Set(["page", "page_size", "search"]);
  for (const key of params.keys()) if (!allowed.has(key)) return null;
  const page = params.get("page");
  const size = params.get("page_size");
  if (page !== null && (!/^\d+$/.test(page) || Number(page) < 1 || Number(page) > 1_000_000)) return null;
  if (size !== null && (!/^\d+$/.test(size) || Number(size) < 1 || Number(size) > 100)) return null;
  const search = params.get("search");
  if (search !== null && search.length > 100) return null;
  if (page !== null) query.set("page", page);
  if (size !== null) query.set("page_size", size);
  if (search) query.set("search", search);

  const build = (path: string) => ({ backendPath: path, method: method as AutomationMethod, query });

  // Collection-level routes.
  if (segments.length === 0) {
    if (method === "GET" || method === "POST") return build("/automations");
    return null;
  }

  // Fixed sub-resources: /automations/options|metrics|runs (GET only).
  if (segments.length === 1 && ["options", "metrics", "runs"].includes(segments[0])) {
    return method === "GET" ? build(`/automations/${segments[0]}`) : null;
  }

  // Everything else is scoped to one automation id.
  if (!UUID.test(segments[0])) return null;
  const tail = segments.slice(1);

  if (tail.length === 0) {
    if (["GET", "PATCH", "DELETE"].includes(method)) return build(`/automations/${segments[0]}`);
    return null;
  }
  if (tail.length === 1 && ["activate", "pause"].includes(tail[0]) && method === "POST") {
    return build(`/automations/${segments[0]}/${tail[0]}`);
  }
  if (tail.length === 1 && tail[0] === "runs" && method === "GET") {
    return build(`/automations/${segments[0]}/runs`);
  }
  return null;
}
