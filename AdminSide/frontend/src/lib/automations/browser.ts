import type { PaginatedResponse } from "@/lib/api/client";

export type AutomationStatus = "draft" | "active" | "paused" | "archived";
export type NodeType = "trigger_message" | "message_contains" | "send_text" | "send_template" | "assign_conversation" | "change_conversation_status" | "delay" | "business_hours";
export interface FlowNode { id: string; node_type: NodeType; name: string; config: Record<string, unknown>; sort_order: number; created_at?: string; updated_at?: string }
export interface FlowEdge { id?: string; source_node_id: string; target_node_id: string; branch: "true" | "false" | null }
export interface Automation { id: string; name: string; description: string | null; status: AutomationStatus; trigger_type: string; version: number; created_at: string; updated_at: string }
export interface AutomationDetail extends Automation { nodes: FlowNode[]; edges: FlowEdge[] }
export interface Execution { id: string; automation_id: string; automation_name: string; automation_version: number; status: string; conversation_id: string; contact_id: string; trigger_message_id: string; current_node_id: string | null; attempt_count: number; max_attempts: number; step_count: number; next_retry_at: string | null; last_error_type: string | null; started_at: string | null; completed_at: string | null; error_summary: string | null; created_at: string }

export class AutomationApiError extends Error { constructor(public readonly status: number, message: string) { super(message); this.name = "AutomationApiError"; } }
async function request<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`/api/automations${path}`, { method: options.method ?? "GET", headers: { Accept: "application/json", ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}) }, ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}), cache: "no-store" }); }
  catch { throw new AutomationApiError(0, "Could not reach the automation service."); }
  if (response.status === 401 && typeof window !== "undefined") window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(location.pathname + location.search)}`);
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new AutomationApiError(response.status, payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string" ? payload.error : "The automation request failed.");
  return payload as T;
}
function query(params: Record<string, string | number | undefined>) { const search = new URLSearchParams(); for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") search.set(k, String(v)); return search.size ? `?${search}` : ""; }
const idPath = (id: string) => `/${encodeURIComponent(id)}`;
export const listAutomations = (filters: { status?: string; search?: string } = {}) => request<PaginatedResponse<Automation>>(query({ page: 1, page_size: 100, ...filters }));
export const createAutomation = (input: { name: string; description?: string }) => request<Automation>("", { method: "POST", body: input });
export const getAutomation = (id: string) => request<AutomationDetail>(idPath(id));
export const updateAutomation = (id: string, body: { name?: string; description?: string }) => request<Automation>(idPath(id), { method: "PATCH", body });
export const saveFlow = (id: string, nodes: FlowNode[], edges: FlowEdge[]) => request<AutomationDetail>(`${idPath(id)}/flow`, { method: "PUT", body: { nodes: nodes.map(({ id, node_type, name, config, sort_order }) => ({ id, node_type, name, config, sort_order })), edges: edges.map(({ source_node_id, target_node_id, branch }) => ({ source_node_id, target_node_id, branch })) } });
export const validateAutomation = (id: string) => request<{ valid: boolean; issues: { code: string; message: string; node_id: string | null }[] }>(`${idPath(id)}/validate`, { method: "POST", body: {} });
export const activateAutomation = (id: string) => request<Automation>(`${idPath(id)}/activate`, { method: "POST", body: {} });
export const pauseAutomation = (id: string) => request<Automation>(`${idPath(id)}/pause`, { method: "POST", body: {} });
export const archiveAutomation = (id: string) => request<Automation>(idPath(id), { method: "DELETE" });
export const simulateAutomation = (id: string, message: string) => request<{ valid: boolean; trigger_matched: boolean; steps: { node_id: string; node_type: NodeType; result: string; detail: string }[]; final_result: string }>(`${idPath(id)}/simulate`, { method: "POST", body: { message } });
export const listExecutions = (id: string) => request<PaginatedResponse<Execution>>(`${idPath(id)}/executions?page=1&page_size=20`);
export const getExecutionMetrics = (id: string) => request<{ total: number; completed: number; failed: number; running: number; retrying: number; queued: number; last_execution_at: string | null; last_failure: string | null }>(`${idPath(id)}/metrics`);
export const getWorkerHealth = () => request<{ status: "healthy" | "delayed" | "unavailable"; last_seen_at: string | null; processed_count: number }>("/worker-health");
export const getExecutionLogs = (automationId: string, executionId: string) => request<{ id: string; node_id: string | null; level: string; summary: string; created_at: string }[]>(`${idPath(automationId)}/executions/${encodeURIComponent(executionId)}/logs`);
