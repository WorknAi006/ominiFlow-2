import { fetchAdminServer } from "../../../lib/api/admin-server";
import { PlansClient } from "./plans-client";

interface PlanItem {
  id: string;
  name: string;
  price: string;
  limits: Record<string, number>;
  active_tenants: number;
  features: string[];
}

export default async function PlansPage() {
  const data = await fetchAdminServer<{ items: PlanItem[] }>("/plans");
  return <PlansClient initialPlans={data?.items || []} />;
}
