import { AutomationEditor } from "@/components/automations/automation-editor";
export default async function AutomationPage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <AutomationEditor id={id} />; }
