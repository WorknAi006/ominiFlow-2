const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const STATUSES = new Set(["draft", "active", "paused", "archived"]);
export type AutomationMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export function buildAutomationTarget(method: string, segments: string[], params: URLSearchParams) {
  if (!["GET", "POST", "PATCH", "PUT", "DELETE"].includes(method)) return null;
  if (method === "GET" && segments.length === 1 && segments[0] === "worker-health" && params.size === 0) {
    return { backendPath: "/automations/worker-health", method: "GET" as AutomationMethod, query: new URLSearchParams() };
  }
  let path = "/automations";
  if (segments.length) {
    if (!UUID.test(segments[0])) return null;
    path += `/${segments[0]}`;
    const tail = segments.slice(1);
    if (tail.length) {
      const valid = (tail.length === 1 && ["validate", "activate", "pause", "simulate", "nodes", "flow", "executions", "metrics"].includes(tail[0])) ||
        (tail.length === 2 && tail[0] === "nodes" && UUID.test(tail[1]) && ["PATCH", "DELETE"].includes(method)) ||
        (tail.length === 3 && tail[0] === "executions" && UUID.test(tail[1]) && tail[2] === "logs" && method === "GET");
      if (!valid) return null;
      path += `/${tail.join("/")}`;
    }
  }
  const allowed = new Set(["page", "page_size", "status", "search"]);
  for (const key of params.keys()) if (!allowed.has(key)) return null;
  const query = new URLSearchParams();
  const page = params.get("page") ?? "1", size = params.get("page_size") ?? "20";
  if (!/^\d+$/.test(page) || Number(page) < 1 || Number(page) > 1000000 || !/^\d+$/.test(size) || Number(size) < 1 || Number(size) > 100) return null;
  if (params.has("page")) query.set("page", page);
  if (params.has("page_size")) query.set("page_size", size);
  const status = params.get("status"), search = params.get("search");
  if (status && !STATUSES.has(status)) return null;
  if (search && search.length > 100) return null;
  if (status) query.set("status", status);
  if (search) query.set("search", search);
  const last = segments.at(-1);
  const ok = method === "GET" ? !last || segments.length === 1 || ["nodes", "executions", "metrics"].includes(last) || (last === "logs" && segments.length === 4)
    : method === "POST" ? !last || ["validate", "activate", "pause", "simulate", "nodes"].includes(last)
      : method === "PATCH" ? segments.length === 1 || (segments.length === 2 && last === "nodes")
        : method === "PUT" ? segments.length === 2 && last === "flow"
          : method === "DELETE" ? segments.length === 1 || (segments.length === 2 && last === "nodes") : false;
  return ok ? { backendPath: path, method: method as AutomationMethod, query } : null;
}
