type AiConfigResponse = {
  provider: "platform" | "openai";
  model: string;
  has_api_key: boolean;
  is_verified: boolean;
};

type AiConfigUpdate = {
  provider: "platform" | "openai";
  model: string;
  api_key?: string;
};

export async function fetchAiConfig(): Promise<AiConfigResponse> {
  const response = await fetch("/api/ai-config", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load AI configuration.");
  }
  return payload;
}

export async function updateAiConfig(update: AiConfigUpdate): Promise<AiConfigResponse> {
  const response = await fetch("/api/ai-config", {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(update),
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  
  if (!response.ok) {
    throw new Error(payload.error || "Failed to update AI configuration.");
  }
  return payload;
}

export type ValidateResponse = {
  status: "valid" | "invalid" | "temporary_failure" | "rate_limited" | "none";
  message: string;
};

export async function validateAiConfig(): Promise<ValidateResponse> {
  const response = await fetch("/api/ai-config", {
    method: "POST",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  
  const payload = await response.json().catch(() => ({}));
  
  if (!response.ok) {
    throw new Error(payload.error || "Failed to validate AI configuration.");
  }
  return payload;
}
