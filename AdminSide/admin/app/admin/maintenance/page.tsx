import { AdminMaintenance } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { MaintenanceClient } from "./maintenance-client";

export default async function MaintenancePage() {
  const initialMaint = await fetchAdminServer<AdminMaintenance>("/maintenance");
  return <MaintenanceClient initialMaint={initialMaint} />;
}
