import { apiRequest, type PaginatedResponse } from "./client";

export const CHANNEL_TYPES = ["whatsapp", "instagram", "facebook"] as const;
export type ChannelType = (typeof CHANNEL_TYPES)[number];

export const CHANNEL_STATUSES = [
  "pending",
  "connected",
  "disconnected",
  "error",
  "revoked",
] as const;
export type ChannelStatus = (typeof CHANNEL_STATUSES)[number];

/** Mirrors backend ChannelConnectionResponse. Never contains credentials. */
export interface ChannelConnection {
  id: string;
  name: string;
  channel_type: ChannelType;
  status: ChannelStatus;
  external_account_id: string | null;
  external_business_id: string | null;
  has_credentials: boolean;
  token_expires_at: string | null;
  is_active: boolean;
  last_connected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelListParams {
  page?: number;
  page_size?: number;
  search?: string;
  channel_type?: ChannelType;
  status?: ChannelStatus;
}

export interface ChannelCreateInput {
  channel_type: ChannelType;
  name: string;
  external_account_id?: string;
  external_business_id?: string;
}

/** Credentials are intentionally not editable here (provider flows only). */
export interface ChannelUpdateInput {
  name?: string;
  is_active?: boolean;
}

export function listChannels(token: string, params: ChannelListParams = {}) {
  return apiRequest<PaginatedResponse<ChannelConnection>>("/channels", {
    token,
    query: { ...params },
  });
}

export function getChannel(token: string, channelId: string) {
  return apiRequest<ChannelConnection>(`/channels/${channelId}`, { token });
}

export function createChannel(token: string, input: ChannelCreateInput) {
  return apiRequest<ChannelConnection>("/channels", {
    method: "POST",
    token,
    body: input,
  });
}

export function updateChannel(
  token: string,
  channelId: string,
  input: ChannelUpdateInput,
) {
  return apiRequest<ChannelConnection>(`/channels/${channelId}`, {
    method: "PATCH",
    token,
    body: input,
  });
}

export function disconnectChannel(token: string, channelId: string) {
  return apiRequest<ChannelConnection>(`/channels/${channelId}/disconnect`, {
    method: "POST",
    token,
  });
}

export function deleteChannel(token: string, channelId: string) {
  return apiRequest<void>(`/channels/${channelId}`, {
    method: "DELETE",
    token,
  });
}
