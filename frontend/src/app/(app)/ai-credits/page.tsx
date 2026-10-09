import { AiCreditsClient } from "@/components/ai/ai-credits-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Credits | Omniflow",
};

export default function AiCreditsPage() {
  return <AiCreditsClient />;
}
