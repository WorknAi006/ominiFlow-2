import "server-only";

import { API_BASE_URL } from "@/lib/api/client";

const backendBaseUrl =
  process.env.OMNIFLOW_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? API_BASE_URL;

export function backendApiUrl(path: string) {
  return new URL(`/api/v1${path}`, backendBaseUrl);
}

export async function parseJson(response: Response): Promise<unknown> {
  return response.json().catch(() => null);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
