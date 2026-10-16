// Browser-side client for Templates. Calls the same-origin Next proxy
// (/api/templates/...), which attaches the HttpOnly session token and
// forwards to the backend. Sync reuses the existing Channel Management
// endpoint; no sync logic is reimplemented here.

import type { PaginatedResponse } from "@/lib/api/client";
import type { MessageTemplate, TemplateSyncResult } from "@/lib/api/templates";

export type { MessageTemplate, TemplateSyncResult };

export interface TemplateFilters {
  page?: number;
  page_size?: number;
  channel_id?: string;
  status?: string;
  category?: string;
  language?: string;
  search?: string;
  include_inactive?: boolean;
}

export class TemplateApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "TemplateApiError";
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function request<T>(path: string, options: { method?: "GET" | "POST"; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/templates${path}`, {
      method: options.method ?? "GET",
      headers: { Accept: "application/json", ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}) },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new TemplateApiError(0, "Could not reach the templates service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new TemplateApiError(401, "Your session has expired. Sign in again.");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The templates request could not be completed.";
    throw new TemplateApiError(response.status, message);
  }
  return payload as T;
}

async function multipartRequest<T>(path: string, form: FormData): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/templates${path}`, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: form,
      cache: "no-store",
    });
  } catch {
    throw new TemplateApiError(0, "Could not reach the templates service. Try again.");
  }
  if (response.status === 401) {
    redirectToLogin();
    throw new TemplateApiError(401, "Your session has expired. Sign in again.");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The templates request could not be completed.";
    throw new TemplateApiError(response.status, message);
  }
  return payload as T;
}

export function listTemplates(filters: TemplateFilters = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request<PaginatedResponse<MessageTemplate>>(suffix);
}

export function getTemplate(templateId: string) {
  return request<MessageTemplate>(`/${encodeURIComponent(templateId)}`);
}

export interface LocalTemplateInput {
  channel_connection_id: string;
  name: string;
  language: string;
  category?: string | null;
  header_format?: "NONE" | "TEXT" | "IMAGE" | "VIDEO" | "DOCUMENT";
  header_text?: string | null;
  body_text: string;
  footer_text?: string | null;
  buttons?: string[];
}

export function createTemplate(input: LocalTemplateInput) {
  return request<MessageTemplate>("", { method: "POST", body: input });
}

export interface SubmitTemplateInput extends LocalTemplateInput {
  category: string;
  body_examples: string[];
  header_file?: File;
}

export function submitTemplate(input: SubmitTemplateInput) {
  const form = new FormData();
  form.set("channel_connection_id", input.channel_connection_id);
  form.set("name", input.name);
  form.set("language", input.language);
  form.set("category", input.category);
  form.set("header_format", input.header_format ?? "NONE");
  if (input.header_text) form.set("header_text", input.header_text);
  form.set("body_text", input.body_text);
  if (input.footer_text) form.set("footer_text", input.footer_text);
  form.set("buttons_json", JSON.stringify(input.buttons ?? []));
  form.set("body_examples_json", JSON.stringify(input.body_examples));
  if (input.header_file) form.set("header_file", input.header_file);
  return multipartRequest<MessageTemplate>("/submit", form);
}

export function uploadTemplateMedia(channelId: string, mediaType: "image" | "video" | "document", file: File) {
  const form = new FormData();
  form.set("media_type", mediaType);
  form.set("file", file);
  return multipartRequest<{ id: string; type: string; filename: string }>(
    `/channels/${encodeURIComponent(channelId)}/media-upload`,
    form,
  );
}

export function syncTemplates(channelId: string) {
  return request<TemplateSyncResult>(`/sync/${encodeURIComponent(channelId)}`, { method: "POST" });
}

export interface AiTemplateDraft {
  name: string;
  category: string;
  language: string;
  header_type: string;
  header_text: string | null;
  body_text: string;
  footer_text: string | null;
  buttons: string[];
}

export interface AiTemplateGenerateResult {
  items: AiTemplateDraft[];
  credits_used: number;
  balance: number;
}

export interface PlatformTemplate {
  id: string;
  name: string;
  label: string;
  language: string;
  category: string;
  body_text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlatformTemplateSubmission {
  channel_connection_id: string;
  body_text: string;
  examples: string[];
}

export function getPlatformTemplateAdminStatus() {
  return request<{ is_platform_super_admin: boolean }>("/platform-template-library/admin-status");
}

export function listPlatformTemplates() {
  return request<{ items: PlatformTemplate[]; total: number }>("/platform-template-library");
}

export function createPlatformTemplate(input: Omit<PlatformTemplate, "id" | "is_active" | "created_at" | "updated_at">) {
  return request<PlatformTemplate>("/platform-template-library", { method: "POST", body: input });
}

export function setPlatformTemplateActive(id: string, active: boolean) {
  return request<PlatformTemplate>(`/platform-template-library/${encodeURIComponent(id)}/${active ? "activate" : "deactivate"}`, { method: "POST" });
}

export function submitPlatformTemplate(id: string, input: PlatformTemplateSubmission) {
  return request<{ template: MessageTemplate; message: string }>(
    `/platform-template-library/${encodeURIComponent(id)}/submit`,
    { method: "POST", body: input },
  );
}

export function generateTemplatesAi(input: { prompt: string; count?: number; category?: string | null; language?: string | null }) {
  return request<AiTemplateGenerateResult>("/ai-generate", { method: "POST", body: input });
}
