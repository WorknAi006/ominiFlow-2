import { AdminAuditLogItem } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { AuditLogsClient } from "./audit-logs-client";

export default async function AuditLogsPage() {
  const data = await fetchAdminServer<{ items: AdminAuditLogItem[] }>("/audit-logs");
  return <AuditLogsClient initialLogs={data?.items || []} />;
}
