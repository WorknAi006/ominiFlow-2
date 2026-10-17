import { apiRequest, type PaginatedResponse } from "./client";

/** Synced from Meta. Components keep Meta's structure. */
export interface MessageTemplate {
  id: string;
  channel_connection_id: string;
  external_template_id: string | null;
  name: string;
  language: string;
  category: string | null;
  /** Lowercase Meta status, e.g. approved, pending, rejected. */
  status: string;
  is_active: boolean;
  is_usable: boolean;
  components: Record<string, unknown>[];
  parameter_format: string | null;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateSyncResult {
  received: number;
  created: number;
  updated: number;
  deactivated: number;
  skipped: number;
}

export interface TemplateListParams {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
  include_inactive?: boolean;
}

export function listTemplates(
  token: string,
  channelId: string,
  params: TemplateListParams = {},
) {
  return apiRequest<PaginatedResponse<MessageTemplate>>(
    `/channels/${channelId}/templates`,
    { token, query: { ...params } },
  );
}

export function syncTemplates(token: string, channelId: string) {
  return apiRequest<TemplateSyncResult>(`/channels/${channelId}/templates/sync`, {
    method: "POST",
    token,
  });
}

export function getTemplate(token: string, templateId: string) {
  return apiRequest<MessageTemplate>(`/templates/${templateId}`, { token });
}
