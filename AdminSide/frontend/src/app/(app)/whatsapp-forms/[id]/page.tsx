import { FormEditor } from "@/components/whatsapp-forms/form-editor";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Edit WhatsApp Form | Omniflow",
};

export default function EditWhatsAppFormPage({ params }: { params: { id: string } }) {
  return <FormEditor id={params.id} />;
}
