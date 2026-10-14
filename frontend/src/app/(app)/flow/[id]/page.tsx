import { FlowBuilder } from "@/components/flow/flow-builder";

export const metadata = {
  title: "Flow Builder | Omniflow",
};

export default async function FlowBuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FlowBuilder flowId={id} />;
}
