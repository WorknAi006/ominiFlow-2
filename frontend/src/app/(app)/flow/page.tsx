import { FlowClient } from "@/components/flow/flow-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Flow | Omniflow",
};

export default function FlowPage() {
  return <FlowClient />;
}
