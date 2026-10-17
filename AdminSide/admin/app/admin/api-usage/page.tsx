import { AdminApiUsage } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { ApiUsageClient } from "./api-usage-client";

export default async function ApiUsagePage() {
  const initialUsage = await fetchAdminServer<AdminApiUsage>("/api-usage");
  return <ApiUsageClient initialUsage={initialUsage} />;
}
