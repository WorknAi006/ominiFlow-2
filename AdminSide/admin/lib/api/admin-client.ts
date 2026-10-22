import {
  AdminApiUsage,
  AdminAuditLogItem,
  AdminAuthResponse,
  AdminChannelItem,
  AdminConversationItem,
  AdminDashboardStats,
  AdminMaintenance,
  AdminSettings,
  AdminSystemHealth,
  AdminTenantDetail,
  AdminTenantItem,
  AdminUser,
  AdminUserItem,
} from "../types/admin";

const API_BASE_URL =
  typeof window !== "undefined"
    ? ""
    : (process.env.OMNIFLOW_API_URL ||
       process.env.NEXT_PUBLIC_API_URL ||
       "http://127.0.0.1:8000");

export class AdminApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.data = data;
  }
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  // Read from cookie first, fallback to localStorage
  const match = document.cookie.match(/(?:^|;\s*)omniflow_admin_token=([^;]+)/);
  if (match) {
    const token = decodeURIComponent(match[1]);
    if (!localStorage.getItem("omniflow_admin_token")) {
      localStorage.setItem("omniflow_admin_token", token);
    }
    return token;
  }
  const local = localStorage.getItem("omniflow_admin_token");
  if (local) {
    setAdminToken(local);
    return local;
  }
  return null;
}

export function setAdminToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    // 8-hour cookie
    const maxAge = 8 * 60 * 60;
    document.cookie = `omniflow_admin_token=${encodeURIComponent(token)}; path=/; max-age=${maxAge}; SameSite=Lax`;
    localStorage.setItem("omniflow_admin_token", token);
  } else {
    document.cookie = "omniflow_admin_token=; path=/; max-age=0; SameSite=Lax";
    localStorage.removeItem("omniflow_admin_token");
  }
}

const inFlightRequests = new Map<string, Promise<unknown>>();
const getCache = new Map<string, { data: unknown; expires: number }>();

export function clearAdminApiCache() {
  getCache.clear();
  inFlightRequests.clear();
}

async function fetchAdmin<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const token = getAdminToken();
  const url = `${API_BASE_URL.replace(/\/$/, "")}/api/v1/admin${endpoint}`;

  if (method === "GET") {
    const cacheKey = `${token || "anon"}:${url}`;
    const cached = getCache.get(cacheKey);
    if (cached && cached.expires > Date.now()) {
      return cached.data as T;
    }

    if (inFlightRequests.has(cacheKey)) {
      return inFlightRequests.get(cacheKey) as Promise<T>;
    }

    const promise = (async () => {
      try {
        const data = await executeFetch<T>(url, token, options);
        getCache.set(cacheKey, { data, expires: Date.now() + 3000 });
        return data;
      } finally {
        inFlightRequests.delete(cacheKey);
      }
    })();

    inFlightRequests.set(cacheKey, promise);
    return promise;
  }

  // Mutations invalidate cached GET data
  clearAdminApiCache();
  return executeFetch<T>(url, token, options);
}

async function executeFetch<T>(
  url: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    throw new AdminApiError(503, "Admin API is currently unreachable. Ensure backend is running.", err);
  }

  if (response.status === 401) {
    setAdminToken(null);
    clearAdminApiCache();
    let errorDetail = "Admin session has expired.";
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/admin/login")) {
      window.location.href = `/admin/login?reason=session_expired`;
    }
    throw new AdminApiError(401, errorDetail);
  }

  if (response.status === 403) {
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/unauthorized")) {
      window.location.href = `/unauthorized`;
    }
    throw new AdminApiError(403, "Super Admin authorization required.");
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new AdminApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}

export const adminApi = {
  // Auth
  async login(email: string, password: string): Promise<AdminAuthResponse> {
    const res = await fetchAdmin<AdminAuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAdminToken(res.access_token);
    return res;
  },

  async getMe(): Promise<AdminUser> {
    return fetchAdmin<AdminUser>("/auth/me");
  },

  logout() {
    setAdminToken(null);
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
  },

  // Dashboard
  async getDashboard(): Promise<AdminDashboardStats> {
    return fetchAdmin<AdminDashboardStats>("/dashboard");
  },

  // Tenants
  async getTenants(params?: { page?: number; page_size?: number; search?: string; status?: string }) {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.search) q.set("search", params.search);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAdmin<{ items: AdminTenantItem[]; total: number; page: number; page_size: number }>(`/tenants${qs}`);
  },

  async createTenant(data: {
    name: string;
    slug?: string;
    email?: string;
    phone?: string;
    description?: string;
    owner_email: string;
    owner_first_name: string;
    owner_last_name?: string;
    owner_password?: string;
    owner_phone?: string;
    plan?: string;
    initial_credits?: number;
    is_active?: boolean;
  }): Promise<{
    tenant: AdminTenantItem;
    owner_user: AdminUser;
    temporary_password: string | null;
    initial_credits: number;
    message: string;
  }> {
    return fetchAdmin<{
      tenant: AdminTenantItem;
      owner_user: AdminUser;
      temporary_password: string | null;
      initial_credits: number;
      message: string;
    }>("/tenants", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getTenant(id: string): Promise<AdminTenantDetail> {

    return fetchAdmin<AdminTenantDetail>(`/tenants/${id}`);
  },

  async updateTenantStatus(id: string, isActive: boolean) {
    return fetchAdmin<{ status: string; is_active: boolean }>(`/tenants/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
  },

  async deleteTenant(id: string) {
    return fetchAdmin<{ status: string; deleted: boolean }>(`/tenants/${id}`, {
      method: "DELETE",
    });
  },

  // Users
  async getUsers(params?: { page?: number; page_size?: number; search?: string; status?: string }) {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.search) q.set("search", params.search);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAdmin<{ items: AdminUserItem[]; total: number; page: number; page_size: number }>(`/users${qs}`);
  },

  async updateUserStatus(id: string, isActive: boolean) {
    return fetchAdmin<{ status: string; is_active: boolean }>(`/users/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
  },

  async createUser(data: {
    email: string;
    password: string;
    first_name: string;
    last_name?: string;
    is_platform_admin?: boolean;
    tenant_id?: string;
    role_name?: string;
  }): Promise<AdminUserItem> {
    return fetchAdmin<AdminUserItem>("/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteUser(id: string) {
    return fetchAdmin<{ status: string; deleted: boolean }>(`/users/${id}`, {
      method: "DELETE",
    });
  },

  // Channels
  async getChannels(params?: { page?: number; page_size?: number; search?: string; channel_type?: string; status?: string }) {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.search) q.set("search", params.search);
    if (params?.channel_type) q.set("channel_type", params.channel_type);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAdmin<{ items: AdminChannelItem[]; total: number; page: number; page_size: number }>(`/channels${qs}`);
  },

  // Conversations
  async getConversations(params?: { page?: number; page_size?: number; search?: string; tenant_id?: string; status?: string }) {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.search) q.set("search", params.search);
    if (params?.tenant_id) q.set("tenant_id", params.tenant_id);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return fetchAdmin<{ items: AdminConversationItem[]; total: number; page: number; page_size: number }>(`/conversations${qs}`);
  },

  // Api Usage
  async getApiUsage(): Promise<AdminApiUsage> {
    return fetchAdmin<AdminApiUsage>("/api-usage");
  },

  // Plans & Billing
  async getPlans() {
    return fetchAdmin<{
      items: Array<{
        id: string;
        name: string;
        price: string;
        limits: Record<string, number>;
        active_tenants: number;
        features: string[];
      }>;
      total: number;
    }>("/plans");
  },

  async getBilling() {
    return fetchAdmin<{
      status: string;
      message: string;
      active_subscriptions: number;
      mrr_usd: number;
      billing_cycles: string[];
    }>("/billing");
  },

  // Security
  async getSecurity() {
    return fetchAdmin<{
      status: string;
      mfa_enforced: boolean;
      super_admins_count: number;
      failed_logins_24h: number;
      rate_limiting_active: boolean;
      active_security_alerts: unknown[];
    }>("/security");
  },

  // Audit Logs
  async getAuditLogs(): Promise<{ items: AdminAuditLogItem[]; total: number }> {
    return fetchAdmin<{ items: AdminAuditLogItem[]; total: number }>("/audit-logs");
  },

  // Webhooks
  async getWebhooks() {
    return fetchAdmin<{
      endpoints: Array<{
        provider: string;
        path: string;
        status: string;
        subscribed_events: string[];
        total_received: number;
        processed: number;
        failed: number;
      }>;
    }>("/webhooks");
  },

  // System Health
  async getSystemHealth(): Promise<AdminSystemHealth> {
    return fetchAdmin<AdminSystemHealth>("/system-health");
  },

  // Settings
  async getSettings(): Promise<AdminSettings> {
    return fetchAdmin<AdminSettings>("/settings");
  },

  // Maintenance
  async getMaintenance(): Promise<AdminMaintenance> {
    return fetchAdmin<AdminMaintenance>("/maintenance");
  },
};
