import { FormEditor } from "@/components/whatsapp-forms/form-editor";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "New WhatsApp Form | Omniflow",
};

export default function NewWhatsAppFormPage() {
  return <FormEditor />;
}
