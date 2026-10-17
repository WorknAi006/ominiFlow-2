import { AdminUserItem, AdminTenantItem } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { UsersClient } from "./users-client";

export default async function UsersPage() {
  const [initialUsers, initialTenants] = await Promise.all([
    fetchAdminServer<{
      items: AdminUserItem[];
      total: number;
      page: number;
      page_size: number;
    }>("/users?page=1&page_size=15"),
    fetchAdminServer<{
      items: AdminTenantItem[];
      total: number;
    }>("/tenants?page=1&page_size=100"),
  ]);

  return <UsersClient initialUsers={initialUsers} initialTenants={initialTenants} />;
}
