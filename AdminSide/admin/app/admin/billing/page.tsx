import { fetchAdminServer } from "../../../lib/api/admin-server";
import { BillingClient } from "./billing-client";

interface BillingData {
  status: string;
  message: string;
  active_subscriptions: number;
  mrr_usd: number;
  billing_cycles: string[];
}

export default async function BillingPage() {
  const data = await fetchAdminServer<BillingData>("/billing");
  return <BillingClient initialBilling={data} />;
}
