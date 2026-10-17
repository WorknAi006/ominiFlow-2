import { InboxClient } from "@/components/inbox/inbox-client";

interface InboxPageProps {
  searchParams: Promise<{ conversation?: string }>;
}

export default async function InboxPage({ searchParams }: InboxPageProps) {
  const { conversation } = await searchParams;
  const initialConversationId = conversation &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(conversation)
    ? conversation
    : null;
  return <InboxClient initialConversationId={initialConversationId} />;
}
