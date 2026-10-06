import type { ChannelType } from "./channels";
import { apiRequest, type PaginatedResponse } from "./client";
import type { MessageDirection, MessageStatus, MessageType } from "./messages";

export const CONVERSATION_STATUSES = [
  "open",
  "pending",
  "resolved",
  "closed",
] as const;
export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export interface Conversation {
  id: string;
  status: ConversationStatus;
  subject: string | null;
  unread_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  contact: { id: string; name: string | null; phone_number: string | null };
  channel: { id: string; name: string; channel_type: ChannelType };
  assigned_user: { id: string; first_name: string; last_name: string | null } | null;
  last_message: {
    id: string;
    direction: MessageDirection;
    message_type: MessageType;
    status: MessageStatus;
    /** Truncated preview. */
    text: string | null;
    created_at: string;
  } | null;
}

export interface ConversationListParams {
  page?: number;
  page_size?: number;
  status?: ConversationStatus;
  channel_id?: string;
  assigned_user_id?: string;
  unassigned?: boolean;
  unread?: boolean;
  search?: string;
}

export function listConversations(
  token: string,
  params: ConversationListParams = {},
) {
  return apiRequest<PaginatedResponse<Conversation>>("/conversations", {
    token,
    query: { ...params },
  });
}

export function getConversation(token: string, conversationId: string) {
  return apiRequest<Conversation>(`/conversations/${conversationId}`, { token });
}

export function updateConversation(
  token: string,
  conversationId: string,
  input: { subject?: string | null },
) {
  return apiRequest<Conversation>(`/conversations/${conversationId}`, {
    method: "PATCH",
    token,
    body: input,
  });
}

export function markConversationRead(token: string, conversationId: string) {
  return apiRequest<Conversation>(`/conversations/${conversationId}/read`, {
    method: "POST",
    token,
  });
}

/** Pass null to unassign. */
export function assignConversation(
  token: string,
  conversationId: string,
  assignedUserId: string | null,
) {
  return apiRequest<Conversation>(`/conversations/${conversationId}/assign`, {
    method: "POST",
    token,
    body: { assigned_user_id: assignedUserId },
  });
}

export function changeConversationStatus(
  token: string,
  conversationId: string,
  status: ConversationStatus,
) {
  return apiRequest<Conversation>(`/conversations/${conversationId}/status`, {
    method: "POST",
    token,
    body: { status },
  });
}
