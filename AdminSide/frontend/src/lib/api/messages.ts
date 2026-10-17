import { API_BASE_URL, ApiError, apiRequest, type PaginatedResponse } from "./client";

export type MessageDirection = "inbound" | "outbound";

export type MessageType =
  | "text"
  | "image"
  | "video"
  | "audio"
  | "document"
  | "location"
  | "template"
  | "interactive"
  | "reaction"
  | "unknown";

export type MessageStatus =
  | "pending"
  | "sent"
  | "delivered"
  | "read"
  | "failed"
  | "received";

export interface Message {
  id: string;
  conversation_id: string;
  contact_id: string;
  channel_connection_id: string;
  direction: MessageDirection;
  message_type: MessageType;
  status: MessageStatus;
  external_message_id: string | null;
  text: string | null;
  /** Authenticated API path (e.g. /api/v1/messages/{id}/media) once downloaded. */
  media_url: string | null;
  media_type: string | null;
  media_metadata: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  reply_to_message_id: string | null;
  sent_by_user_id: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
}

export const MAX_TEXT_LENGTH = 4096;

export interface SendTextMessageInput {
  type: "text";
  text: string;
  reply_to_message_id?: string;
}

export interface TemplateParameterInput {
  type: "text" | "image" | "video" | "document" | "payload";
  text?: string;
  parameter_name?: string;
  /** Public https URL for media headers. */
  link?: string;
  filename?: string;
  payload?: string;
}

export interface TemplateComponentInput {
  type: "header" | "body" | "button";
  sub_type?: "url" | "quick_reply";
  index?: number;
  parameters: TemplateParameterInput[];
}

/** Approved templates may be sent outside the 24h customer service window. */
export interface SendTemplateMessageInput {
  type: "template";
  template_name: string;
  language: string;
  components?: TemplateComponentInput[];
}

export type SendMessageInput = SendTextMessageInput | SendTemplateMessageInput;

/** Newest first. */
export function listMessages(
  token: string,
  conversationId: string,
  params: { page?: number; page_size?: number } = {},
) {
  return apiRequest<PaginatedResponse<Message>>(
    `/conversations/${conversationId}/messages`,
    { token, query: { ...params } },
  );
}

export function getMessage(token: string, messageId: string) {
  return apiRequest<Message>(`/messages/${messageId}`, { token });
}

export function sendMessage(
  token: string,
  conversationId: string,
  input: SendMessageInput,
) {
  return apiRequest<Message>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    token,
    body: input,
  });
}

/**
 * Fetch downloaded media as a Blob (the endpoint requires the bearer
 * token, so it cannot be used directly as an <img src>).
 */
export async function fetchMessageMedia(token: string, messageId: string): Promise<Blob> {
  const response = await fetch(new URL(`/api/v1/messages/${messageId}/media`, API_BASE_URL), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const detail =
      data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : null;
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}
