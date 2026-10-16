// Browser-side client for Channel Management. Calls the same-origin Next
// proxy (/api/channels/...), which attaches the HttpOnly session token and
// forwards to the backend. No access token is ever held in client state.

import type {
  ChannelConnection,
  ChannelListParams,
  ChannelStatus,
  ChannelType,
} from "@/lib/api/channels";
import type { MessageTemplate, TemplateListParams, TemplateSyncResult } from "@/lib/api/templates";
import type { PaginatedResponse } from "@/lib/api/client";

export type { ChannelConnection, ChannelStatus, ChannelType, MessageTemplate, TemplateSyncResult };

export interface ConnectionCheck {
  healthy: boolean;
  detail: string;
  webhook_subscribed: boolean | null;
  display_phone_number: string | null;
  verified_name: string | null;
  quality_rating: string | null;
  last_event_at: string | null;
}

export interface WhatsAppConnectInput {
  phone_number_id: string;
  waba_id: string;
  access_token?: string;
  code?: string;
}

export interface WhatsAppEmbeddedSignupConfig {
  app_id: string;
  config_id: string;
  graph_api_version: string;
}

export interface FacebookConnectInput {
  page_id: string;
  access_token: string;
}

export interface FacebookConnectionCheck {
  healthy: boolean;
  detail: string;
  webhook_subscribed: boolean | null;
  page_name: string | null;
  last_event_at: string | null;
}

export interface InstagramConnectInput {
  instagram_id: string;
  page_id: string;
  access_token: string;
}

export interface InstagramConnectionCheck {
  healthy: boolean;
  detail: string;
  webhook_subscribed: boolean | null;
  username: string | null;
  account_id: string | null;
  last_event_at: string | null;
}

export class ChannelApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ChannelApiError";
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const destination = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(destination)}`);
}

async function request<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/channels${path}`, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      cache: "no-store",
    });
  } catch {
    throw new ChannelApiError(0, "Could not reach the channel service. Try again.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new ChannelApiError(401, "Your session has expired. Sign in again.");
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "The channel request could not be completed.";
    throw new ChannelApiError(response.status, message);
  }
  return payload as T;
}

export function listChannels(params: ChannelListParams = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request<PaginatedResponse<ChannelConnection>>(suffix);
}

export function getChannel(channelId: string) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}`);
}

export function createChannel(input: {
  channel_type: ChannelType;
  name: string;
  external_account_id?: string;
  external_business_id?: string;
}) {
  return request<ChannelConnection>("", { method: "POST", body: input });
}

export function renameChannel(channelId: string, input: { name?: string; is_active?: boolean }) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}`, { method: "PATCH", body: input });
}

export function disconnectChannel(channelId: string) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}/disconnect`, { method: "POST" });
}

export function deleteChannel(channelId: string) {
  return request<void>(`/${encodeURIComponent(channelId)}`, { method: "DELETE" });
}

export function connectWhatsApp(channelId: string, input: WhatsAppConnectInput) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}/whatsapp/connect`, {
    method: "POST",
    body: input,
  });
}

export function getWhatsAppEmbeddedSignupConfig() {
  return request<WhatsAppEmbeddedSignupConfig>("/whatsapp/embedded-signup/config");
}

export function testWhatsAppConnection(channelId: string) {
  return request<ConnectionCheck>(`/${encodeURIComponent(channelId)}/whatsapp/test`, { method: "POST" });
}

export function connectFacebook(channelId: string, input: FacebookConnectInput) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}/facebook/connect`, {
    method: "POST",
    body: input,
  });
}

export function testFacebookConnection(channelId: string) {
  return request<FacebookConnectionCheck>(`/${encodeURIComponent(channelId)}/facebook/test`, { method: "POST" });
}

export function connectInstagram(channelId: string, input: InstagramConnectInput) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}/instagram/connect`, {
    method: "POST",
    body: input,
  });
}

export function testInstagramConnection(channelId: string) {
  return request<InstagramConnectionCheck>(`/${encodeURIComponent(channelId)}/instagram/test`, { method: "POST" });
}

// ----- Meta OAuth self-service onboarding (Facebook / Instagram) -----

export type MetaOAuthProvider = "facebook" | "instagram";

export interface OAuthAssetItem {
  external_account_id: string;
  name: string;
  page_id: string | null;
  page_name: string | null;
}

export interface OAuthAssets {
  provider: string;
  assets: OAuthAssetItem[];
}

export function startMetaOAuth(provider: MetaOAuthProvider) {
  return request<{ authorization_url: string }>(`/oauth/${provider}/start`, { method: "POST" });
}

export function getMetaOAuthAssets(token: string) {
  return request<OAuthAssets>(`/oauth/assets?token=${encodeURIComponent(token)}`);
}

export function completeMetaOAuth(token: string, externalAccountId: string) {
  return request<ChannelConnection>("/oauth/select", {
    method: "POST",
    body: { token, external_account_id: externalAccountId },
  });
}

export function connectWebChat(channelId: string) {
  return request<ChannelConnection>(`/${encodeURIComponent(channelId)}/web-chat/connect`, { method: "POST" });
}

export function listChannelTemplates(channelId: string, params: TemplateListParams = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request<PaginatedResponse<MessageTemplate>>(`/${encodeURIComponent(channelId)}/templates${suffix}`);
}

export function syncChannelTemplates(channelId: string) {
  return request<TemplateSyncResult>(`/${encodeURIComponent(channelId)}/templates/sync`, { method: "POST" });
}
