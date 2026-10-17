export interface AdminUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_platform_admin: boolean;
  created_at: string;
}

export interface AdminAuthResponse {
  access_token: string;
  token_type: string;
  user: AdminUser;
}

export interface AdminDashboardStats {
  total_tenants: number;
  active_tenants: number;
  suspended_tenants: number;
  total_users: number;
  connected_channels: number;
  total_conversations: number;
  total_messages: number;
  active_automations: number;
  system_status: "healthy" | "warning" | "degraded" | "down";
  database_status: string;
  redis_status: string;
}

export interface AdminTenantItem {
  id: string;
  name: string;
  slug: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_deleted: boolean;
  user_count: number;
  channel_count: number;
  conversation_count: number;
  plan: string;
  created_at: string;
  updated_at: string;
}

export interface AdminTenantDetail extends AdminTenantItem {
  description: string | null;
  users: Array<{
    id: string;
    email: string;
    name: string;
    role_id: string;
    status: string;
  }>;
  channels: Array<{
    id: string;
    name: string;
    type: string;
    status: string;
    created_at: string | null;
  }>;
}

export interface AdminUserItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_platform_admin: boolean;
  created_at: string;
  updated_at: string;
  tenants: string[];
}

export interface AdminChannelItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  channel_type: string;
  name: string;
  status: string;
  is_active: boolean;
  is_deleted: boolean;
  external_account_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminConversationItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  contact_name: string | null;
  contact_phone: string | null;
  channel_type: string;
  status: string;
  unread_count: number;
  last_message_preview: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminApiUsage {
  total_api_requests: number;
  total_messages_processed: number;
  total_webhooks_received: number;
  rate_limit_events: number;
  tenant_usage: Array<{
    tenant_id: string;
    tenant_name: string;
    messages: number;
    webhooks: number;
    quota_limit: number;
    usage_percentage: number;
  }>;
}

export interface AdminSystemHealth {
  overall_status: "healthy" | "warning" | "degraded" | "down";
  timestamp: string;
  components: Array<{
    name: string;
    status: "healthy" | "warning" | "degraded" | "down" | "not available";
    details: string | null;
    latency_ms: number | null;
  }>;
}

export interface AdminSettings {
  app_name: string;
  app_env: string;
  allowed_origins: string[];
  meta_graph_version: string;
  media_storage_backend: string;
  jwt_expire_minutes: number;
  max_automation_nodes: number;
  rate_limiting_enabled: boolean;
}

export interface AdminMaintenance {
  maintenance_mode: boolean;
  message: string | null;
  scheduled_at: string | null;
  active_incidents: Array<Record<string, unknown>>;
}

export interface AdminAuditLogItem {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  target: string;
  tenant: string | null;
  result: string;
  ip_address: string | null;
}
