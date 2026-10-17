import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { validateRegistration } from "@/lib/auth/validation";

export async function POST(request: NextRequest) {
  const body: unknown = await request.json().catch(() => null);
  if (
    !isRecord(body) ||
    typeof body.email !== "string" ||
    typeof body.password !== "string" ||
    typeof body.first_name !== "string" ||
    typeof body.tenant_name !== "string" ||
    (body.last_name !== undefined && typeof body.last_name !== "string")
  ) {
    return NextResponse.json({ error: "Complete the required fields to continue." }, { status: 400 });
  }

  const validationError = validateRegistration({
    email: body.email,
    password: body.password,
    confirmPassword: body.password,
    firstName: body.first_name,
    lastName: typeof body.last_name === "string" ? body.last_name : "",
    tenantName: body.tenant_name,
  });
  if (validationError) return NextResponse.json({ error: validationError }, { status: 400 });

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        email: body.email,
        password: body.password,
        first_name: body.first_name,
        last_name: body.last_name || null,
        tenant_name: body.tenant_name,
      }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "Registration is temporarily unavailable. Please try again." },
      { status: 503 },
    );
  }

  const payload: unknown = await parseJson(upstream);
  if (!upstream.ok) {
    const fallback = upstream.status === 409
      ? "An account or workspace with those details already exists."
      : upstream.status === 422
        ? "Check the required fields and try again."
        : "Unable to create your account right now. Please try again.";
    return NextResponse.json(
      { error: fallback },
      { status: upstream.status >= 400 && upstream.status < 500 ? upstream.status : 503 },
    );
  }

  if (!isRecord(payload) || typeof payload.access_token !== "string") {
    return NextResponse.json({ error: "The registration response was invalid." }, { status: 502 });
  }

  // The backend returns a token on registration, but this UI requires an
  // explicit sign-in. Strip it and do not establish a session here.
  return NextResponse.json({ success: true }, { status: 201 });
}
