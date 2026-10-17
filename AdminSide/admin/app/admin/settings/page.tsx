import { AdminSettings } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { SettingsClient } from "./settings-client";

export default async function SettingsPage() {
  const initialSettings = await fetchAdminServer<AdminSettings>("/settings");
  return <SettingsClient initialSettings={initialSettings} />;
}
