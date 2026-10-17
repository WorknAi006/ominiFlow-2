import React from "react";
import { fetchAdminServer } from "../../../lib/api/admin-server";
import { SecurityClient, SecurityData } from "./security-client";

export default async function SecurityPage() {
  const initialSec = await fetchAdminServer<SecurityData>("/security");
  return <SecurityClient initialSec={initialSec} />;
}
