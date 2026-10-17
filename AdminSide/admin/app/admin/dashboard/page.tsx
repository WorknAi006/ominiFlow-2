import { AdminDashboardStats } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { AdminDashboardClient } from "./dashboard-client";

export default async function AdminDashboardPage() {
  const initialStats = await fetchAdminServer<AdminDashboardStats>("/dashboard");
  return <AdminDashboardClient initialStats={initialStats} />;
}
