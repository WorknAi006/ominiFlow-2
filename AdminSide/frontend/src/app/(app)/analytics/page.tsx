import { AnalyticsClient } from "@/components/analytics/analytics-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Analytics | Omniflow",
};

export default function AnalyticsPage() {
  return <AnalyticsClient />;
}
