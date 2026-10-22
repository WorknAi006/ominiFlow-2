# Repository deployment audit

This checkout is `WorknAi006/ominiFlow-2` and its application is named Omniflow.
FM Films is used for deployment resources and the requested domains; application
branding, UI and business behavior remain as supplied.

| Component | Detected source and production behavior |
| --- | --- |
| Main website | `frontend`, Next.js 16.3.8 App Router, React 19.2.8, npm with committed lockfile. `npm ci`, `npm run build`; `.next/standalone/server.js`, `.next/static`, `public`. Production runs `node server.js` on container port 3000. |
| Admin | `AdminSide/admin`, separate Next.js 16.3.8 App Router and npm lockfile. Same build/output/runtime as the main site. Existing `npm start` searches for a free port; Docker deliberately runs the standalone server on fixed port 3000. |
| Backend | Root `backend`, FastAPI, Python 3.11, SQLAlchemy, Alembic, pinned pip requirements; `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Root backend already includes `/api/v1/admin` used by the admin. |
| Duplicate trees | `AdminSide/frontend` and `AdminSide/backend` are older parallel copies. They are not extra production services. The root backend has the wider current integration and migration set. |
| Database | PostgreSQL 16, JSONB and PostgreSQL-specific migrations; the SQLite file in the repository is not a production database. Alembic migrations then idempotent system-role seed are required. |
| Realtime | Redis pub/sub and backend WebSocket `/api/v1/ws/inbox`. The main frontend exposes a cookie-authenticated SSE bridge at `/api/realtime/inbox`; it must remain on Next.js. |
| Workers | `whatsapp_events`, `whatsapp_media`, `automations`, `campaigns`, `flow_delivery`, `knowledge_base`, each run with `python -m app.workers.NAME --loop`. |
| Uploads | Shared local media storage used by inbound attachments and knowledge documents. Persistent volume mounted at `/app/var/media` in API and workers. Media is served through authenticated API routes, not public Nginx aliases. |
| Request size | App supports documents up to 100 MB for WhatsApp and 25 MB for knowledge documents. Gateway limit is 110 MB to allow multipart overhead. App validation still applies. |
| Health | Existing `/health` liveness and `/health/database` readiness. Container check also verifies Redis. Worker healthchecks verify dependencies and process survival; they do not prove that individual jobs are progressing. |

## API and environment decisions

- Gateway `/api/v1/*` goes unchanged to FastAPI. `/health` maps to the existing
  backend liveness endpoint. Other requests, including `/api/auth/*`, resource
  proxy routes and SSE, go to the appropriate Next.js server.
- Browser API helper uses the current origin. Production build-time API origins
  are HTTPS URLs. Server-only `OMNIFLOW_API_URL=http://fmfilms-backend:8000` stays
  inside Docker. `NEXT_PUBLIC_APP_URL` fixes the admin's development-only return link.
- Compose forces production mode, HTTPS browser origins, local persistent media
  and the production Meta OAuth callback. Optional SMTP, Meta, AI and Razorpay
  credentials remain in the VPS-only `.env`.
- API credentials require a strong JWT secret and Fernet channel encryption key;
  the existing backend validates these in production. `deploy/init-env.py`
  creates them once and never overwrites an existing `.env`.
- Added `python-multipart`, required by existing upload routes, and `websockets`,
  required by Uvicorn for the existing WebSocket endpoint. Removed a redundant
  unpinned `openai` entry while retaining its existing exact pin.
- Old root Compose exposed PostgreSQL/Redis and contained a password. New
  production resources use the isolated `fmfilms` project and new named volumes.
  Existing Omniflow volumes are never deleted or automatically imported.
  The duplicated legacy Compose password is also replaced with an environment
  requirement; that Compose file is not used for production.

## Verification and limits

Both frontend production builds were verified locally. The main build fetches
its existing Geist fonts from Google during compilation, so build hosts need
outbound access to Google Fonts in addition to package registries.

Backend dependencies resolve and pass `pip check`; the API imports with
production settings and passes non-database liveness/auth-boundary smoke checks.
The Alembic revision graph has one head. Eleven deployment regression tests pass.
Both standalone Next.js servers also pass local page and static asset smoke
checks; web additionally passes its unauthenticated cookie API and SSE checks.
The built browser bundles contain no development localhost HTTP endpoints.

The supplied main frontend test suite has existing automation allowlist/test
mismatches. Its authentication, inbox, channel and realtime suites pass and run
in deployment CI. Other passing suites cover AI form state, contacts, team and
templates. Admin tests expect a running backend with a particular pre-existing
test admin, so they are not standalone unit tests and are not used as CI gates.
Production setup does not create the hardcoded test account.

Local Docker is unavailable. Actual Linux image builds, migrations, service
readiness and startup are enforced by the GitHub Actions validation job before
it connects to the VPS. Live gateway configuration, DNS, certificates, database
contents, SSH access and final production responses require access to the VPS;
they cannot be certified from this checkout.
