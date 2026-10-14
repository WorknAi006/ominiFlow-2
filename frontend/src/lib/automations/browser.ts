import type { PaginatedResponse } from "@/lib/api/client";

export type TriggerType = "new_contact_created" | "tag_added_to_contact" | "chat_status_changed" | "chat_stuck_in_mode";
export type MatchType = "all" | "any";
export type ThenMode = "run_actions" | "start_flow";
export type RunStatus = "success" | "failed" | "skipped";

export interface Condition { field: string; operator: string; value: string }
export interface Action { type: string; config: Record<string, unknown> }

export interface Automation {
  id: string;
  name: string;
  trigger_type: TriggerType;
  trigger_config: Record<string, unknown>;
  match_type: MatchType;
  conditions: Condition[];
  then_mode: ThenMode;
  flow_ref: string | null;
  actions: Action[];
  is_active: boolean;
  runs_first: number;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OptionItem { value: string; label: string }
export interface ConfigField { key: string; label: string; type: string }
export interface ActionOption extends OptionItem { config_fields: ConfigField[] }
export interface AutomationOptions {
  triggers: OptionItem[];
  condition_fields: OptionItem[];
  operators: OptionItem[];
  actions: ActionOption[];
  chat_statuses: OptionItem[];
}

export interface AutomationRun {
  id: string;
  automation_id: string;
  trigger_type: TriggerType;
  contact_id: string | null;
  conversation_id: string | null;
  status: RunStatus;
  matched: boolean;
  actions_run: number;
  detail: string | null;
  created_at: string;
}

export interface AutomationMetrics {
  total_rules: number;
  active_rules: number;
  runs_total: number;
  runs_success: number;
  runs_failed: number;
  runs_skipped: number;
  last_run_at: string | null;
}

export type AutomationInput = {
  name: string;
  trigger_type: TriggerType;
  trigger_config?: Record<string, unknown>;
  match_type?: MatchType;
  conditions?: Condition[];
  then_mode?: ThenMode;
  flow_ref?: string | null;
  actions?: Action[];
  is_active?: boolean;
  runs_first?: number;
};

export class AutomationApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "AutomationApiError";
  }
}

async function request<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/automations${path}`, {
      method: options.method ?? "GET",
      headers: { Accept: "application/json", ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}) },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new AutomationApiError(0, "Could not reach the automation service.");
  }
  if (response.status === 401 && typeof window !== "undefined") {
    window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(location.pathname + location.search)}`);
  }
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new AutomationApiError(
      response.status,
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string" ? payload.error : "The automation request failed.",
    );
  }
  return payload as T;
}

export const listAutomations = (search?: string) =>
  request<PaginatedResponse<Automation>>(`?page=1&page_size=100${search ? `&search=${encodeURIComponent(search)}` : ""}`);
export const getAutomation = (id: string) => request<Automation>(`/${encodeURIComponent(id)}`);
export const createAutomation = (body: AutomationInput) => request<Automation>("", { method: "POST", body });
export const updateAutomation = (id: string, body: Partial<AutomationInput>) => request<Automation>(`/${encodeURIComponent(id)}`, { method: "PATCH", body });
export const deleteAutomation = (id: string) => request<void>(`/${encodeURIComponent(id)}`, { method: "DELETE" });
export const activateAutomation = (id: string) => request<Automation>(`/${encodeURIComponent(id)}/activate`, { method: "POST", body: {} });
export const pauseAutomation = (id: string) => request<Automation>(`/${encodeURIComponent(id)}/pause`, { method: "POST", body: {} });
export const getAutomationOptions = () => request<AutomationOptions>("/options");
export const getAutomationMetrics = () => request<AutomationMetrics>("/metrics");
export const listRuns = () => request<PaginatedResponse<AutomationRun>>("/runs?page=1&page_size=20");
export const listAutomationRuns = (id: string) => request<PaginatedResponse<AutomationRun>>(`/${encodeURIComponent(id)}/runs?page=1&page_size=20`);
