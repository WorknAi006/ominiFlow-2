import { AiConfigClient } from "@/components/ai/ai-config-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Configuration | Omniflow",
};

export default function AiConfigPage() {
  return <AiConfigClient />;
}
