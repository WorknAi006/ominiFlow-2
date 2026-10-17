import type { Metadata } from "next";
import { KeywordsClient } from "@/components/keywords/keywords-client";

export const metadata: Metadata = {
  title: "Keywords | Omniflow",
  description: "Manage auto-reply triggers.",
};

export default function KeywordsPage() {
  return <KeywordsClient />;
}
