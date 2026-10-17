import { AdminChannelItem } from "../../../lib/types/admin";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { ChannelsClient } from "./channels-client";

export default async function ChannelsPage() {
  const initialData = await fetchAdminServer<{
    items: AdminChannelItem[];
    total: number;
    page: number;
    page_size: number;
  }>("/channels?page=1&page_size=15");

  return <ChannelsClient initialData={initialData} />;
}
