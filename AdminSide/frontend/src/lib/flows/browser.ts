export type FlowStatus = "draft" | "active";

export interface FlowNodeData {
  label?: string;
  channel?: string;
  messageType?: string;
  message?: string;
  showLinkPreview?: boolean;
  mediaUrl?: string;
  mediaName?: string;
  isStart?: boolean;
  [key: string]: unknown;
}
export interface FlowNode {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: FlowNodeData;
  [key: string]: unknown;
}
export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  [key: string]: unknown;
}

export interface FlowSummary {
  id: string;
  name: string;
  status: FlowStatus;
  channels: string[];
  created_at: string;
  updated_at: string;
}
export interface Flow extends FlowSummary {
  nodes: FlowNode[];
  edges: FlowEdge[];
  created_by_user_id: string | null;
}
export interface FlowListResponse { items: FlowSummary[]; total: number }
export interface FlowUploadResponse { key: string; url: string; filename: string; content_type: string; size: number }

// ---- Builder catalogue (matches the reference dropdowns) --------------------
export const CHANNEL_TYPES: { value: string; label: string }[] = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "messenger", label: "Messenger" },
  { value: "instagram", label: "Instagram" },
  { value: "omnichannel", label: "OmniChannel" },
];

export const CREATE_CHANNELS: { value: string; label: string }[] = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
  { value: "messenger", label: "Facebook Messenger" },
];

export const MESSAGE_TYPES: { value: string; label: string }[] = [
  { value: "text", label: "Text Message" },
  { value: "video", label: "Video Message" },
  { value: "image", label: "Image Message" },
  { value: "audio", label: "Audio Message" },
  { value: "document", label: "Document Message" },
  { value: "button", label: "Button Message" },
  { value: "list", label: "List Message" },
  { value: "template", label: "Template Message" },
  { value: "carousel", label: "Carousel Template" },
  { value: "get_user_data", label: "Get User Data" },
  { value: "external_api", label: "External API Request" },
  { value: "condition", label: "Condition" },
  { value: "delay", label: "Delay" },
  { value: "actions", label: "Actions" },
  { value: "razorpay", label: "Razorpay Payment" },
  { value: "whatsapp_form", label: "WhatsApp Form" },
  { value: "zoho_crm", label: "Zoho CRM" },
  { value: "send_email", label: "Send Email" },
];

// Message types that accept an uploaded file.
export const MEDIA_MESSAGE_TYPES = new Set(["audio", "document", "image", "video"]);

export const VARIABLES: { value: string; label: string }[] = [
  { value: "{{contact_name}}", label: "Contact Name" },
  { value: "{{contact_phone}}", label: "Contact Phone" },
  { value: "{{user_last_input}}", label: "User last input" },
];

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, { cache: "no-store", ...options });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.replace(`/login?reason=session-expired&next=${encodeURIComponent(location.pathname)}`);
  }
  if (!res.ok) {
    let msg = "The flow request failed.";
    try { const d = await res.json(); msg = d.error || d.detail || msg; } catch { /* keep default */ }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const flowsApi = {
  list: (search?: string) =>
    api<FlowListResponse>(`/api/flows${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  get: (id: string) => api<Flow>(`/api/flows/${id}`),
  create: (name: string, channels: string[]) =>
    api<Flow>("/api/flows", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, channels }) }),
  update: (id: string, body: Partial<Pick<Flow, "name" | "status" | "channels" | "nodes" | "edges">>) =>
    api<Flow>(`/api/flows/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  remove: (id: string) => api<void>(`/api/flows/${id}`, { method: "DELETE" }),
  copy: (id: string) => api<Flow>(`/api/flows/${id}/copy`, { method: "POST" }),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api<FlowUploadResponse>("/api/flows/upload", { method: "POST", body: form });
  },
};
