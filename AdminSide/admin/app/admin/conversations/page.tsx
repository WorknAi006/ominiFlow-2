import { AdminConversationItem } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { ConversationsClient } from "./conversations-client";

export default async function ConversationsPage() {
  const initialData = await fetchAdminServer<{
    items: AdminConversationItem[];
    total: number;
    page: number;
    page_size: number;
  }>("/conversations?page=1&page_size=15");

  return <ConversationsClient initialData={initialData} />;
}
