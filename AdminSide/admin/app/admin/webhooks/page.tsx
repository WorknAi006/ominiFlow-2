import { fetchAdminServer } from "../../../lib/api/admin-server";
import { WebhooksClient } from "./webhooks-client";

interface WebhookEndpoint {
  provider: string;
  path: string;
  status: string;
  subscribed_events: string[];
  total_received: number;
  processed: number;
  failed: number;
}

export default async function WebhooksPage() {
  const data = await fetchAdminServer<{ endpoints: WebhookEndpoint[] }>("/webhooks");
  return <WebhooksClient initialEndpoints={data?.endpoints || []} />;
}
