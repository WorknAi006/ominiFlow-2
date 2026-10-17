import { redirect } from "next/navigation";

import { TeamClient } from "@/components/team/team-client";
import { getAuthContext } from "@/lib/auth/session";

export default async function TeamPage() {
  const context = await getAuthContext();
  if (!context) redirect("/login?reason=session-expired");
  return <TeamClient currentUser={{ id: context.user.id, role: context.user.role }} />;
}
