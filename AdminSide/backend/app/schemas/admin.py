import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str | None
    is_active: bool
    is_verified: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminUserResponse


# --- Dashboard Stats ---
class AdminDashboardStats(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_users: int
    connected_channels: int
    total_conversations: int
    total_messages: int
    active_automations: int
    system_status: str
    database_status: str
    redis_status: str


# --- Tenants ---
class AdminTenantListItem(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    email: str | None
    phone: str | None
    is_active: bool
    is_deleted: bool
    user_count: int
    channel_count: int
    conversation_count: int
    plan: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminTenantListResponse(BaseModel):
    items: list[AdminTenantListItem]
    total: int
    page: int
    page_size: int


class AdminTenantDetail(AdminTenantListItem):
    description: str | None
    users: list[dict[str, Any]]
    channels: list[dict[str, Any]]


class AdminTenantStatusUpdate(BaseModel):
    is_active: bool


class AdminCreateTenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    description: str | None = None


# --- Users ---
class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str | None
    is_active: bool
    is_verified: bool
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime
    tenants: list[str]

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    page_size: int


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    is_platform_admin: bool = False
    tenant_id: uuid.UUID | None = None
    role_name: str | None = "AGENT"


# --- Channels ---
class AdminChannelListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    channel_type: str
    name: str
    status: str
    is_active: bool
    is_deleted: bool
    external_account_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminChannelListResponse(BaseModel):
    items: list[AdminChannelListItem]
    total: int
    page: int
    page_size: int


# --- Conversations ---
class AdminConversationListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    contact_name: str | None
    contact_phone: str | None
    channel_type: str
    status: str
    unread_count: int
    last_message_preview: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminConversationListResponse(BaseModel):
    items: list[AdminConversationListItem]
    total: int
    page: int
    page_size: int


# --- API Usage & Health ---
class AdminApiUsageResponse(BaseModel):
    total_api_requests: int
    total_messages_processed: int
    total_webhooks_received: int
    rate_limit_events: int
    tenant_usage: list[dict[str, Any]]


class AdminSystemHealthComponent(BaseModel):
    name: str
    status: str  # "healthy", "warning", "degraded", "down", "not available"
    details: str | None
    latency_ms: float | None = None


class AdminSystemHealthResponse(BaseModel):
    overall_status: str
    timestamp: datetime
    components: list[AdminSystemHealthComponent]


class AdminSettingsResponse(BaseModel):
    app_name: str
    app_env: str
    allowed_origins: list[str]
    meta_graph_version: str
    media_storage_backend: str
    jwt_expire_minutes: int
    max_automation_nodes: int
    rate_limiting_enabled: bool


class AdminMaintenanceResponse(BaseModel):
    maintenance_mode: bool
    message: str | None
    scheduled_at: datetime | None
    active_incidents: list[dict[str, Any]]


class AdminAuditLogItem(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    action: str
    target: str
    tenant: str | None
    result: str
    ip_address: str | None


class AdminAuditLogResponse(BaseModel):
    items: list[AdminAuditLogItem]
    total: int
