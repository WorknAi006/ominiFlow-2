# Omniflow

Multi-tenant omnichannel SaaS platform.

- `backend/`: FastAPI, synchronous SQLAlchemy, PostgreSQL, Alembic
- `frontend/`: Next.js

## Backend

### Install and configure

Use Python 3.11.9, then install the pinned backend dependencies in a
virtual environment. From a fresh checkout, run:

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cd ..
Copy-Item .env.example .env
```

Set the required local values in `.env` for your environment before starting
the service. For normal runtime installations use `backend/requirements.txt`;
`backend/requirements-dev.txt` adds the pinned test runner.

The API allows browser origins from `FRONTEND_ORIGINS`, a comma-separated
list. If it is empty, the existing `FRONTEND_URL` value is used as a
single-origin fallback (default `http://localhost:3000`). The default CORS
policy permits only `GET`, `POST`, `PATCH`, and `DELETE`, with `Authorization`
and `Content-Type` headers. It does not enable cross-site cookies. Set
`NEXT_PUBLIC_API_URL` in the frontend environment to the backend API origin;
the frontend currently calls the API directly and has no proxy rewrite.

### Run

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m app.db.run_seed      # idempotent: roles, permissions, role permissions
uvicorn app.main:app --reload

# In a second terminal: turn stored WhatsApp events into inbox data
python -m app.workers.whatsapp_events --loop
# In a third terminal: download inbound WhatsApp media
python -m app.workers.whatsapp_media --loop
```

API docs: http://127.0.0.1:8000/docs

### Tests

Tests run against the configured PostgreSQL database inside a transaction
that is always rolled back, so no data is persisted.

```powershell
cd backend
python -m pytest -q
```

(`python -m unittest discover -s tests -t .` with `PYTHONPATH=.` also works.)

## API

All endpoints are under `/api/v1`. Authenticated endpoints need
`Authorization: Bearer <access_token>`.

| Method | Path | Permission |
|---|---|---|
| POST | `/auth/register` | public |
| POST | `/auth/login` | public |
| GET | `/tenants/current` | `tenant:read` |
| PATCH | `/tenants/current` | `tenant:update` |
| GET | `/users?page=1&page_size=20&search=` | `user:read` |
| GET | `/users/{user_id}` | `user:read` |
| PATCH | `/users/{user_id}` | `user:update` |
| DELETE | `/users/{user_id}` | `user:delete` |
| POST | `/users/invite` | `user:create` |
| GET | `/users/invitations` | `user:read` |
| DELETE | `/users/invitations/{invitation_id}` | `user:create` |
| POST | `/users/invitations/accept` | public (token) |
| GET | `/channels?page=&page_size=&search=&channel_type=&status=` | `channel:read` |
| GET | `/channels/{channel_id}` | `channel:read` |
| POST | `/channels` | `channel:create` |
| PATCH | `/channels/{channel_id}` | `channel:update` |
| POST | `/channels/{channel_id}/disconnect` | `channel:update` |
| DELETE | `/channels/{channel_id}` | `channel:delete` |
| POST | `/channels/{channel_id}/whatsapp/connect` | `channel:update` |
| GET | `/webhooks/whatsapp` | public (verify token) |
| POST | `/webhooks/whatsapp` | public (Meta signature) |
| GET | `/contacts?page=&page_size=&search=&phone=` | `contact:read` |
| GET | `/contacts/{contact_id}` | `contact:read` |
| POST | `/contacts` | `contact:create` |
| PATCH | `/contacts/{contact_id}` | `contact:update` |
| GET | `/conversations?status=&channel_id=&assigned_user_id=&unassigned=&unread=&search=` | `conversation:read` |
| GET | `/conversations/{id}` | `conversation:read` |
| PATCH | `/conversations/{id}` (subject) | `conversation:update` |
| POST | `/conversations/{id}/read` | `conversation:update` |
| POST | `/conversations/{id}/status` | `conversation:update` |
| POST | `/conversations/{id}/assign` | `conversation:assign` |
| GET | `/conversations/{id}/messages` (newest first) | `message:read` |
| POST | `/conversations/{id}/messages` (send) | `message:create` |
| GET | `/messages/{message_id}` | `message:read` |
| GET | `/messages/{message_id}/media` (stream) | `message:read` |
| GET | `/channels/{channel_id}/templates?status=&search=&include_inactive=` | `template:read` |
| POST | `/channels/{channel_id}/templates/sync` | `template:sync` |
| GET | `/templates/{template_id}` | `template:read` |

## Tenant isolation

The tenant is always taken from the `tenant_id` claim of the access token
and verified against an active `TenantMembership` on every request.
`tenant_id` sent in a query string is ignored and in a request body is
rejected (422). Members of other tenants return 404.

## Permissions

Permissions are stored in the database (`permissions`, `role_permissions`)
and seeded by `app/db/seed.py`. Endpoints only check permissions, never
role names.

| Role | tenant:read | tenant:update | user:read | user:create | user:update | user:delete |
|---|---|---|---|---|---|---|
| OWNER | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MANAGER | ✓ | | ✓ | ✓ | ✓ | |
| AGENT | ✓ | | ✓ | | | |
| VIEWER | ✓ | | ✓ | | | |
| DEVELOPER | ✓ | | ✓ | | | |

| Role | channel:read | channel:create | channel:update | channel:delete |
|---|---|---|---|---|
| OWNER | ✓ | ✓ | ✓ | ✓ |
| ADMIN | ✓ | ✓ | ✓ | ✓ |
| MANAGER | ✓ | ✓ | ✓ | |
| AGENT | ✓ | | | |
| VIEWER | ✓ | | | |
| DEVELOPER | ✓ | | | |

| Role | contact:read / conversation:read / message:read | contact:create, contact:update, conversation:update, message:create | conversation:assign |
|---|---|---|---|
| OWNER, ADMIN, MANAGER | ✓ | ✓ | ✓ |
| AGENT | ✓ | ✓ | |
| VIEWER, DEVELOPER | ✓ | | |

`template:read` is granted to every role. `template:sync` is granted to
OWNER, ADMIN and MANAGER. Sending a template requires `message:create`.

OWNER is always granted every permission in `SYSTEM_PERMISSIONS`.

## Channel connections

Channels (`whatsapp`, `instagram`, `facebook`) belong to one tenant.
Status is one of `pending`, `connected`, `disconnected`, `error` or
`revoked`.

- **Create** always produces `pending`. Only provider modules, after
  verifying the account with the provider, may set `connected`. These are
  not built yet.
- **PATCH** accepts only `name` and `is_active`. Credentials, status,
  type and external ids cannot be edited through the generic API.
- **Disconnect** wipes stored credentials and sets `disconnected`. The
  record is kept.
- **Delete** is a soft delete (`is_deleted`, `deleted_at`) because future
  conversations and messages will reference channels. Credentials are
  wiped and the channel is hidden from the API (404).
- **Uniqueness:** one live channel per `(tenant, type, external_account_id)`.
  An external account can be `connected` to only one tenant, so unverified
  `pending` records cannot hijack or block webhook routing.

### Credential security

- Tokens are encrypted with Fernet (authenticated encryption) through
  `ChannelCredentialService` (`app/services/credential_service.py`) before
  storage, in `access_token_encrypted` and `refresh_token_encrypted`.
- Keys come from `CHANNEL_CREDENTIAL_KEYS` (comma-separated, newest
  first) to support rotation. They are never hardcoded.
- If the key is missing or invalid, storing credentials fails with 503.
  It never falls back to plaintext.
- Tokens are never returned by the API. Responses only expose
  `has_credentials`. Tokens are never logged, and 422 validation errors
  do not echo them.

### Providers and webhooks

`app/integrations/base.py` defines `ChannelProvider` (`connect`,
`disconnect`, `refresh_token`, `validate_credentials`,
`get_account_info`). Implementations live in
`app/integrations/{whatsapp,instagram,facebook}/provider.py`, and
`app/integrations/registry.py` maps channel types to providers. WhatsApp
is implemented (see below). Instagram and Facebook still raise
`ProviderNotImplementedError`; nothing reports a fake connection.

Webhooks are per-provider endpoints that verify the provider signature
and resolve the tenant with
`channel_service.find_connected_channel(channel_type, external_account_id)`.
Webhooks never accept a `tenant_id` from the caller.

## WhatsApp Cloud API

### Configuration

| Variable | Purpose |
|---|---|
| `META_APP_ID`, `META_APP_SECRET` | Meta app credentials. Used for token verification, `appsecret_proof` and webhook signatures. |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Random string you also enter in the Meta dashboard. |
| `META_GRAPH_API_VERSION` | Default `v23.0`. |

In the Meta app dashboard, set the webhook callback URL to
`https://<host>/api/v1/webhooks/whatsapp` and subscribe to the `messages`
field. Without these values, connect and webhooks return 503 (fail
closed).

### Connect flow

1. Create a pending channel: `POST /channels` with `channel_type=whatsapp`.
2. `POST /channels/{id}/whatsapp/connect` (`channel:update`) with
   `phone_number_id`, `waba_id` and exactly one of `access_token` (system
   user token) or `code` (Embedded Signup code, exchanged server-side).
3. The backend verifies with Meta, then:
   - `debug_token`: the token is valid, issued for our app, not expired,
     and has `whatsapp_business_management` and
     `whatsapp_business_messaging`. If granular scopes list target ids,
     the WABA must be among them.
   - The WABA is readable with the token, and the phone number is listed
     under that WABA.
   - It subscribes the app to the WABA's webhooks (`subscribed_apps`).
4. Only then is the channel set to `connected`. The token is encrypted,
   `external_account_id` = phone_number_id, `external_business_id` = WABA
   id, and token expiry is stored when Meta reports one.

On failure: 400 with a sanitized reason, 502 if Meta is unreachable, 409
if the number is already connected elsewhere (the other tenant is not
revealed). A not-yet-connected channel moves to `error` with
`last_error`; an already connected channel is left untouched.

### Webhook (`/api/v1/webhooks/whatsapp`)

- **GET:** the subscription handshake. The challenge is returned only if
  `hub.mode=subscribe`, the verify token matches (constant-time
  comparison) and the challenge is alphanumeric. Otherwise 403.
- **POST:**
  - The body is capped at 1 MB (413).
  - `X-Hub-Signature-256` is verified (HMAC-SHA256 of the raw body with
    the app secret, constant-time) before parsing (403).
  - Each change is routed by `metadata.phone_number_id` through
    `find_connected_channel`, and the entry's WABA id must match the
    channel. Unroutable changes are dropped.
  - After signature verification and JSON parsing, NUL (U+0000)
    characters are removed from all string values and keys
    (`app/core/json_sanitize.py`). PostgreSQL text/JSONB cannot store them.
    All other content (Unicode, emoji, newlines) is unchanged.
  - Messages, statuses and errors are stored in `whatsapp_events` with a
    unique `(channel_id, dedupe_key)`, so Meta retries are idempotent.
  - Verified payloads return 200; storage failures return 500 so Meta
    retries. Database errors are logged by type only, never with payload
    content.

`whatsapp_events` rows (`processing_status=received`) are the input for
the future Unified Inbox, which will create contacts, conversations and
messages. Payloads contain customer data and are never logged.

## Unified Inbox

```
Meta -> webhook (signature verified) -> whatsapp_events
     -> worker: process_pending_events() -> Contact -> Conversation -> Message
Inbox API -> POST /conversations/{id}/messages -> WhatsApp provider -> Meta
```

### Data model

- **contacts:** tenant-scoped. Phone numbers are normalized to E.164
  (`app/core/phone.py`) and unique per tenant (partial unique index). The
  same customer can exist in several tenants. `profile_name` comes from
  WhatsApp; `display_name` and the name fields are set by the team.
- **conversations:** status is `open`, `pending`, `resolved` or `closed`.
  A partial unique index allows at most one active (`open`/`pending`)
  conversation per contact + channel. A message after `resolved`/`closed`
  starts a new conversation, and reopening an old one while another is
  active returns 409.
- **messages:** a unique `(tenant_id, channel_connection_id,
  external_message_id)` makes provider messages idempotent. `created_at`
  uses `clock_timestamp()`, so ordering is correct even within one
  transaction.

### Event processor (`app/services/whatsapp_event_processor.py`)

- **One transaction per event.** The event row is claimed with
  `FOR UPDATE SKIP LOCKED`, so several workers can run safely. Domain
  writes run in a savepoint: on any error they are rolled back and the
  event is marked `failed` with a sanitized `processing_error`.
- **Inbound** text, image, video, audio, document and location are mapped
  to messages. Other types are stored as `unknown`, with only the
  provider type in metadata (no invented content). Media is referenced
  by WhatsApp media id; it is not downloaded yet.
- **Statuses** (`sent`, `delivered`, `read`, `failed`) update the outbound
  message by external id. Status never moves backwards, and failed
  messages store a sanitized `error_code` and `error_message`.
- `ignored` covers events that are valid but not inbox data: account
  errors, unknown message ids and invalid sender numbers.
- Tenant and channel come from the event row, never from the payload.
  A channel that doesn't belong to the event's tenant fails the event.
- **Worker:** `python -m app.workers.whatsapp_events [--loop]`. A future
  Celery task should call `process_pending_events()`.

### Outbound

`POST /conversations/{id}/messages` with `{"type": "text", "text": "..."}`
(max 4096 characters):

- The conversation, channel and contact must belong to the tenant. The
  channel must be a connected, active WhatsApp channel, and the contact
  must not be blocked.
- The token is decrypted server-side only. A `pending` message is
  committed, then Meta is called with no DB transaction open, and the
  message becomes `sent` (with the wamid) or `failed` (sanitized error,
  502).
- Credentials never appear in responses or logs.

## Realtime inbox (message.created, message.status_changed, conversation.updated)

- After the event processor **commits** a new inbound message, it
  publishes `message.created` to Redis channel
  `omniflow:tenant:{tenant_id}:inbox`. The tenant comes from webhook
  routing, never from the payload.
- Publishing is best effort. If Redis is down, the message is still
  stored and the failure is logged without the Redis URL.
- The event has only safe fields: ids, direction, type, text, and the
  contact's id, name and phone. No credentials or raw webhook payload.
- **WebSocket** `/api/v1/ws/inbox`:
  1. Connect, then send `{"type": "auth", "token": "<access JWT>"}` within
     10 s. The token is never sent in the URL, so it can't reach access
     logs.
  2. The token is validated with the existing auth chain (JWT, user,
     active tenant membership, `message:read`).
  3. The server replies `{"event": "ready"}` and streams only that
     tenant's `message.created`, `message.status_changed` and
     `conversation.updated` events.
  4. The socket closes when the token expires.

  Close codes: 4401 unauthenticated/expired, 4403 forbidden, 4408 auth
  timeout, 1011 realtime unavailable.
- **`message.status_changed`:** published after the commit of a
  WhatsApp status webhook (`sent`, `delivered`, `read`, `failed`), and
  only when the message's status value actually changed:
  - Duplicates and stale or out-of-order statuses publish nothing (status
    never downgrades; `failed` is final and doesn't override delivered or
    read). Late timestamps are still recorded.
  - Payload `data`: `status`, `sent_at`, `delivered_at`, `read_at`,
    `failed_at`, `error_code`, `error_message` (control characters
    removed, at most 500 characters).
- **`conversation.updated`:** published right after `message.created`
  when an inbound message is committed. It is not published for
  duplicates, status events or ignored events.
  - Payload `data`: `status`, `unread_count`, `last_message_at`,
    `last_message_id`, `last_message_direction`, `last_message_type`,
    `last_message_preview` (single line, at most 200 characters). No
    contact details.
  - The latest message is chosen by `coalesce(sent_at, created_at)`, the
    same rule the conversation list uses. An older message that arrives
    late increments the unread count but never replaces the newer preview
    or `last_message_at`.
- **Frontend client:** `frontend/src/lib/realtime/inbox.ts`
  (`connect`, `disconnect`, `reconnect`, `onMessageCreated`,
  `onMessageStatusChanged`, `onConversationUpdated`, `parseRealtimeEvent`;
  exponential backoff with jitter; no retry on 4403). Tests:
  `cd frontend && npm run test:realtime`.

## WhatsApp media

- Inbound image, video, audio and document messages create a
  `message_media` row (`pending`) in the same transaction as the message.
  The media worker (`python -m app.workers.whatsapp_media --loop`,
  `media_service.process_pending_media()`) downloads it later. No HTTP call
  happens inside a database transaction.
- **Download:** Graph `GET /{media-id}?phone_number_id=…` returns a
  short-lived URL plus MIME type, size and SHA-256. That URL is only
  fetched if it is `https` on a Meta media host (`fbsbx.com`, `fbcdn.net`,
  `facebook.com`, `whatsapp.net`); otherwise the token is never sent.
  Downloads have no redirects, a timeout and a streamed size cap.
- **Validation:** per-kind MIME allowlist and limits (image 5 MB, video and
  audio 16 MB, document 100 MB), a Content-Type match and a SHA-256 check.
  Permanent problems mark the row `failed`; timeouts, outages and storage
  errors retry up to `MEDIA_MAX_DOWNLOAD_ATTEMPTS`, using a 5-minute
  lease per attempt.
- **Storage:** `app/storage` (`MediaStorage` interface, `LocalFileStorage`
  for development at `backend/var/media`, which is git-ignored). Keys are
  generated by the app (`tenants/<tenant>/messages/<message>/<uuid>.<ext>`)
  and validated against traversal. Provider filenames are sanitized and
  used for display only. S3, R2 and MinIO plug in through `get_storage()`.
- **Serving:** `GET /messages/{id}/media` streams the file to an
  authorized member of the same tenant, with `nosniff`, a sandboxed CSP
  and `no-store` caching. `message.media_url` points at this endpoint and
  never at a provider URL.

## WhatsApp templates

- `POST /channels/{id}/templates/sync` fetches `/{waba}/message_templates`,
  following paging cursors only. Items are validated (name, language,
  status, components) and upserted on
  `(tenant, channel, name, language)`. Meta components are stored as
  JSONB. Templates no longer returned by Meta are set `is_active=false`.
  Sync is idempotent.
- **Sending:** `POST /conversations/{id}/messages` with
  `{"type": "template", "template_name": …, "language": …, "components": […]}`.
  The template must belong to the conversation's tenant and channel, be
  active and `approved`, and the parameters must match its definition:
  - header text or media
  - positional or named body parameters
  - dynamic URL buttons and quick-reply payloads

  Unsafe values (new lines, tabs, 5+ spaces, non-https links) are
  rejected. The stored message has `message_type=template`, a rendered
  preview text, and the template reference in its metadata.
- Meta remains the authority on the 24-hour window. Text messages keep
  their existing behavior; templates are chosen explicitly with
  `type=template`.

## Team management rules

- **Membership status:** `active`, `suspended` or `removed`. Only `active`
  members can access the tenant. `DELETE /users/{id}` sets `removed`; the
  global user account and other tenant memberships are never touched.
- **No privilege escalation:** a member can only assign, manage, invite
  to, or revoke invitations for a role whose permissions are a subset of
  their own. Only an OWNER can assign the OWNER role or manage an OWNER.
- **Owner protection:** a tenant always keeps at least one active OWNER.
  Removing, suspending or demoting the last active OWNER (including
  yourself) returns 409.
- `PATCH /users/{id}` accepts only `role_id` and `status`
  (`active` | `suspended`). Any other field returns 422.

## Invitation flow

1. `POST /users/invite` with `email` and `role_id` creates a
   `team_invitations` row. The raw token is 256 bits from `secrets`; only
   its SHA-256 hash is stored. Invitations expire after
   `INVITATION_EXPIRE_HOURS` (default 72).
2. One open invitation per email per tenant. Expired ones are revoked
   automatically when re-inviting.
3. **Email delivery is not implemented yet.** It plugs into
   `deliver_invitation()` in `app/services/user_service.py`. Until then,
   when `APP_ENV=development` the invite response includes
   `invitation_token`. It is never returned in other environments or by
   any other endpoint.
4. `POST /users/invitations/accept` with `token` and `password` (plus
   `first_name` and optional `last_name` for new accounts):
   - New email: creates the user (Argon2 password) and membership.
   - Existing account: the password must match the existing account. No
     duplicate user is created and the profile is not changed.
   - A previously `removed` membership is reactivated with the invited
     role. An existing `active` or `suspended` membership returns 409.
   - It runs in one transaction, marks the invitation accepted (single
     use), and returns an access token for the invited tenant.
5. Unknown, expired, revoked or already accepted tokens all return the
   same 400 response.
