# Omniflow — Platform Super Admin Panel

Enterprise control plane for Omniflow SaaS operators and platform administrators.

---

## 🏛️ Architecture & Separation

The Omniflow repository maintains three distinct, dedicated tiers:

```
Omniflow SaaS
│
├── admin/          ← ONE separate Super Admin application (Next.js / Port 3001)
│                     Target production domain: admin.omniflow.com
│
├── frontend/       ← Client / Tenant application (Next.js / Port 3000)
│                     Target production domain: app.omniflow.com
│
└── backend/        ← Shared FastAPI backend (Port 8000)
                      Target production domain: api.omniflow.com
```

- **Independent Application:** Built completely inside `/admin` with its own `package.json`, layout, routing, and styling.
- **Dedicated Authentication:** Completely isolated login portal at `/login`. Does not reuse client login or redirect through tenant routes.
- **Backend Authorization Authority:** All privileged requests require `is_platform_admin == true` enforced server-side by `get_current_platform_admin`. No client-side trust or hardcoded credentials.

---

## 🚀 Running Locally

```powershell
cd admin
npm install
npm run dev
```

The Super Admin application will be available at:
**`http://localhost:3001`**

---

## 🔐 Super Admin Credentials

You can log into the control plane with either configured platform administrator:

| Email | Password | Role |
|---|---|---|
| `admin@omniflow.io` | `OmniflowAdmin2026!` | Super Admin |
| `owner@businessai.com` | `Owner@BusinessAI2026` | Super Admin |

To seed or update credentials at any time, run from `backend/`:
```powershell
python -m app.db.seed_admin "admin@omniflow.io" "YourPasswordHere"
```

---

## 🗺️ Route Directory

| Route | Purpose | Access |
|---|---|---|
| `/login` | Dedicated Super Admin login portal | Public |
| `/unauthorized` | 403 Forbidden screen for non-super-admins | Authenticated |
| `/dashboard` | Platform metrics, tenants, users, subsystem health | Super Admin |
| `/tenants` | Tenant directory (search, filter, suspend, delete) | Super Admin |
| `/tenants/[id]` | Tenant detail view (members, channels, usage) | Super Admin |
| `/users` | Global users directory (search, filter, suspend) | Super Admin |
| `/users/[id]` | User detail view (workspaces, attributes) | Super Admin |
| `/channels` | Connected WhatsApp, Web Chat & Social channels | Super Admin |
| `/conversations` | Conversation traffic monitor across all tenants | Super Admin |
| `/api-usage` | Message throughput, webhook volumes & tenant quotas | Super Admin |
| `/plans` | Platform subscription tiers and active tenant counts | Super Admin |
| `/billing` | Gateway status and subscription overview | Super Admin |
| `/security` | Cryptographic guards, Argon2id & Fernet status | Super Admin |
| `/audit-logs` | Platform audit trail of organization & admin events | Super Admin |
| `/webhooks` | Meta Cloud API webhook delivery and verification | Super Admin |
| `/system-health` | Real-time FastAPI, PostgreSQL 16 & Redis probes | Super Admin |
| `/settings` | Verified platform parameters & CORS allowlists | Super Admin |
| `/maintenance` | Incident oversight and maintenance schedules | Super Admin |

---

## 🧪 Testing & Validation

```powershell
# Run Super Admin test suite:
npm test

# Type checking:
npx tsc --noEmit

# Production build check:
npm run build
```
