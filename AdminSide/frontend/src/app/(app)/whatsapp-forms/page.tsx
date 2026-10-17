import { FormsClient } from "@/components/whatsapp-forms/forms-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "WhatsApp Forms | Omniflow",
};

export default function WhatsAppFormsPage() {
  return <FormsClient />;
}
