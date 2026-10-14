import { FlowList } from "@/components/flow/flow-list";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Flow | Omniflow",
};

export default function FlowPage() {
  return <FlowList />;
}
