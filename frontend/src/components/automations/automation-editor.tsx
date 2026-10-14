"use client";

import { AutomationBuilder } from "@/components/automations/automation-builder";

export function AutomationEditor({ id }: { id: string }) {
  return <AutomationBuilder id={id} />;
}
