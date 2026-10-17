# Omniflow frontend

Next.js App Router frontend for the Omniflow API.

## Local setup

Use Node.js 20 or later. From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The example points to the local API at `http://127.0.0.1:8000`. Configure
`OMNIFLOW_API_URL` to an API origin reachable by the Next.js server. The
existing browser API/WebSocket client uses `NEXT_PUBLIC_API_URL`; the backend
must allow the frontend origin through `FRONTEND_ORIGINS` (or `FRONTEND_URL`).

## Authentication

Login and registration are forwarded through same-origin Next.js route
handlers to `/api/v1/auth/login` and `/api/v1/auth/register`. Login stores the
backend access token in an HttpOnly, SameSite=Lax cookie (Secure in production)
whose lifetime is bounded by the token expiry. Protected route layouts verify
that token against the backend's current tenant and member endpoints before
rendering workspace pages. The browser never receives the JWT from these
handlers.

Registration follows the backend response but deliberately does not establish
a session; sign in after creating the workspace. Logout removes the browser's
session cookie. The backend has no refresh-token or token-revocation endpoint,
so expired sessions require signing in again and logout cannot revoke a copied
token before its normal expiry.

## Checks

```powershell
npx tsc --noEmit
npx eslint src scripts
npm run test:auth
npm run test:realtime
```
