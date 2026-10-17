"use client";

import { useEffect, useState } from "react";

/**
 * Live AI credit balance for the current tenant, fetched from the payments
 * backend. Returns null until loaded (or on error), so callers can show a
 * placeholder.
 */
export function useCreditBalance(): number | null {
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/payments/balance", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data && typeof data.balance === "number") setBalance(data.balance);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return balance;
}
