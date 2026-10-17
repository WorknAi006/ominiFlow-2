import { AdminTenantItem } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { TenantsClient } from "./tenants-client";

export default async function TenantsPage() {
  const initialData = await fetchAdminServer<{
    items: AdminTenantItem[];
    total: number;
    page: number;
    page_size: number;
  }>("/tenants?page=1&page_size=15");

  return <TenantsClient initialData={initialData} />;
}
