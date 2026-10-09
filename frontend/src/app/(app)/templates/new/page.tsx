import { TemplateEditor } from "@/components/templates/template-editor";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Template | Omniflow",
};

export default function NewTemplatePage() {
  return <TemplateEditor />;
}
