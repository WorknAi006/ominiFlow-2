# FM Films production deployment

This deploys the existing **Omniflow** application under the requested FM Films
domains. See [AUDIT.md](AUDIT.md) for the inspected stack and test limitations.
There is no UI redesign or additional backend. Nothing in this repository
starts another public Nginx or binds a host port.

## Architecture

```text
Internet
  |
  +-- lovenzea-gateway :80/:443 (existing container, retained)
        +-- fmfilms.in / www.fmfilms.in --> fmfilms-web:3000
        +-- admin.fmfilms.in -----------> fmfilms-admin:3000
        +-- all three /api/v1/* --------> fmfilms-backend:8000
        +-- all three /health ---------> backend /health
                                              |
                                     PostgreSQL + Redis
                                              |
                          six workers + persistent media volume
```

Only web, admin and backend join external `lovenzea_default`. PostgreSQL,
Redis and workers use the separate `fmfilms_fmfilms_internal` bridge. This
bridge permits outbound provider requests; it is not Docker's `internal: true`
mode, which would break workers calling Meta/OpenAI. No service publishes
database, application or development ports. Backend trusts forwarded headers
from Docker peers because it has no published ports; access to the shared
gateway network must remain limited to trusted server projects.

Main Next.js cookie proxy routes such as `/api/auth/login` and
`/api/realtime/inbox` stay on web. Backend routes retain their `/api/v1` prefix.
WebSockets get upgrade headers and SSE buffering is disabled. Docker DNS
re-resolves service names after container replacements, so normal code
deployments do not require gateway reloads.

## Required access and DNS

You need the VPS SSH username, SSH port, and a working SSH key or provider console.
An IP address alone does not provide authenticated access. Use the hosting
provider's server/access page to recover these details. Do not send passwords
or private key contents in chat.

Point these records at the VPS's public IPv4 address in your DNS provider:

| Type | Name | Value |
| --- | --- | --- |
| A | `@` | `VPS_PUBLIC_IP` |
| A | `www` | `VPS_PUBLIC_IP` |
| A | `admin` | `VPS_PUBLIC_IP` |

Remove AAAA records unless FM Films IPv6 listeners have also been configured on
the gateway. These generated blocks use IPv4 listeners. Port 80 must reach the existing gateway for HTTP-01; port 443 must
reach it for HTTPS. Do not change other domains, firewall rules or containers.

## First-time VPS setup

The current production deployment is already live. For this server, configure
the Actions secrets below and use normal pushes to `main`; do not rerun clone,
bootstrap, environment generation or initial certificate issuance.

Commit and push these repository changes to `main` before cloning. Run the
following on Ubuntu, through SSH or the provider console. The repository and
deployment scripts are administered as root. CI supports either root SSH or a
deployment user with passwordless `sudo`; the root process needs repository
read access for future `git fetch` operations.

```bash
sudo -i
apt-get update
apt-get install -y git python3 openssl curl certbot

# Docker Engine and Compose already run on this shared VPS. Verify them.
# Do not reinstall/restart the daemon or recreate the public gateway.
docker version
docker compose version
docker inspect lovenzea-gateway >/dev/null
docker network inspect lovenzea_default >/dev/null
docker exec lovenzea-gateway nginx -t

# The live server already pulls this HTTPS remote successfully; preserve it.
# A new private checkout needs its own GitHub read authentication.
# If /var/www/fmfilms already exists, inspect it first; never overwrite blindly.
git clone --branch main https://github.com/WorknAi006/ominiFlow-2.git /var/www/fmfilms
cd /var/www/fmfilms
python3 deploy/init-env.py
chmod 600 .env

# Optional integrations: edit credentials here, never in GitHub source files.
nano .env

# Builds and migrations run before any application replacement.
bash deploy/deploy.sh --bootstrap
```

Use Docker Compose 2.27.1 or newer with `up --wait`, `--wait-timeout` and `--pull`.
The backend build uses `build.network: host` because Docker bridge networking
was unreliable for PyPI on this VPS. Its wheel download has a 300-second
timeout and ten retries. Dependency pins, including SQLAlchemy and Alembic,
are unchanged. `build.entitlements: [network.host]` explicitly grants the
requested build network privilege to Compose/Bake; without it, CI rejects the
build before downloading dependencies. This does not set runtime `network_mode: host`; all six workers
continue sharing the single backend image. If a transient failure needs a
fresh build, run `docker compose build --no-cache backend`, then retry the
normal deployment. Do not change package versions to work around networking.

The helper checks the gateway's network, running state and the exact mounts
documented in the request. If the real server uses different mount source
paths, it stops without making changes; inspect the mounts before adapting it.
It never recreates the gateway to change mounts.

`init-env.py` uses exclusive file creation: an existing `.env` is left intact.
It creates random database/JWT/Fernet secrets and production defaults without
printing them. The root `.env.example` contains variable names only. If you
provide an existing `.env`, `DATABASE_URL` must use the `postgres` Docker hostname,
database/user `fmfilms`, and the same password as `POSTGRES_PASSWORD`. URL-encode
special password characters in the URL; generated hexadecimal passwords need
no encoding. Never regenerate JWT/Fernet keys on routine deployment.

Optional SMTP settings enable existing invitations/password-reset delivery;
Meta app/webhook credentials enable channel integrations; AI and Razorpay
credentials enable their existing integrations. Register the production
OAuth callback `https://fmfilms.in/api/v1/channels/oauth/callback` with Meta.
The setup does not invent credentials or create a default administrator.

After signing up through the main application, grant the existing account's
platform role when appropriate:

```bash
cd /var/www/fmfilms
docker compose exec backend python -m app.cli.platform_admin --grant --email YOUR_ACCOUNT_EMAIL
```

The new project uses `fmfilms_postgres_data`, `fmfilms_redis_data`, and
`fmfilms_media` named volumes. It does **not** import the development database,
SQLite file, older `omniflow` volumes or other applications' data. If live data
must be transferred, take a backup and plan that import before directing users
to the new instance. Merely pointing a new image at an old volume is not a data
migration strategy.

## SSL and safe shared-gateway installation

After all three DNS records resolve to this VPS, replace the email placeholder
with your certificate contact address:

```bash
cd /var/www/fmfilms
bash deploy/setup-ssl.sh YOUR_LETSENCRYPT_EMAIL
bash deploy/deploy.sh

install -m 644 deploy/fmfilms-cert-renew.service /etc/systemd/system/fmfilms-cert-renew.service
install -m 644 deploy/fmfilms-cert-renew.timer /etc/systemd/system/fmfilms-cert-renew.timer
systemctl daemon-reload
systemctl enable --now fmfilms-cert-renew.timer

# Test ACME renewal without replacing production certificates.
bash deploy/renew-ssl.sh --dry-run
```

The SSL helper bootstraps only an FM Films HTTP block with the existing
`/var/www/certbot` challenge root. Ordinary requests return 503 until TLS is
ready. It uses host Certbot `certonly --webroot`, never standalone mode, so it
does not compete for ports 80/443. The certificate request is equivalent to:

```bash
certbot certonly --webroot -w /var/www/certbot \
  --cert-name fmfilms --keep-until-expiring --non-interactive --agree-tos \
  --email YOUR_LETSENCRYPT_EMAIL \
  -d fmfilms.in -d www.fmfilms.in -d admin.fmfilms.in
```

Use `setup-ssl.sh` for the initial setup, because it first installs/validates
HTTP challenge routing. It detects actual `fullchain.pem`/`privkey.pem` paths
from a valid, non-staging certificate whose SANs are exactly the three requested
names, including suffixed directories such as `fmfilms-0001`. It refuses to
expand or overwrite an unrelated lineage named `fmfilms`. It never deletes the
Let's Encrypt tree or changes another site's certificate. HTTP then redirects
normal traffic to HTTPS, with the challenge location still available.

The dedicated timer renews **only** this detected lineage. Existing server
renewal jobs remain intact. Certificate fingerprints also detect renewal by
another job; only a changed certificate or config causes a tested gateway
reload. Renewal errors are visible in:

```bash
journalctl -u fmfilms-cert-renew.service
systemctl list-timers fmfilms-cert-renew.timer
```

`setup-gateway.sh` reads `/var/www/lovenzea_v1/gateway.nginx.conf`, then inserts
or replaces only `# BEGIN FMFILMS` through `# END FMFILMS` directly inside the
existing `http` context. A parser handles quoted braces/comments and refuses
missing/duplicate/nested markers or existing unmanaged FM Films server names,
including names in included configurations. It preserves unrelated content.

Before every change it creates
`gateway.nginx.conf.backup.UTC_TIMESTAMP-PID`. It writes in place to preserve
the single-file Docker bind mount. It runs `docker exec lovenzea-gateway nginx -t`
before any reload and restores the backup if testing/reload fails. Gateway
changes and deployments use separate locks. Do not edit the shared file
concurrently while an installer is running.

## GitHub Actions secrets and deployment

Set these repository or `production` environment secrets in GitHub:

| Secret | Meaning |
| --- | --- |
| `VPS_HOST` | VPS hostname or public IP, without a URL scheme |
| `VPS_USER` | SSH account authorized for the deployment |
| `VPS_PORT` | SSH port; defaults to 22 if omitted |
| `VPS_SSH_KEY` | Dedicated private SSH key; matching public key belongs in VPS `authorized_keys` |
| `VPS_KNOWN_HOSTS` | Verified OpenSSH host-key entries for this host and port |

The live VPS uses its existing HTTPS GitHub remote and successful read
authentication. Do not change that remote to SSH. The Actions-to-VPS login
key authenticates a different connection and does not replace GitHub read access.
Generate/provision keys privately, never commit them. Obtain the SSH host-key
fingerprint from the VPS/provider console and verify it before saving
`VPS_KNOWN_HOSTS`. For a nonstandard port, the known-host entry uses
`[hostname]:PORT`. The workflow uses strict host-key checking and never accepts
a host key merely because an unauthenticated network scan returned it.

For this deployment, set `VPS_HOST` to the VPS IP, `VPS_USER` to `root` and
`VPS_PORT` to `22`. Set `VPS_SSH_KEY` and `VPS_KNOWN_HOSTS` manually using the
following steps. The workflow cannot configure these secrets for you.

In Windows PowerShell, create a dedicated key outside the repository. At both
passphrase prompts press Enter; the current noninteractive workflow does not
support passphrase-protected private keys. Keep the private file private.

```powershell
$deployKey = Join-Path $env:USERPROFILE '.ssh/fmfilms-actions'
if ((Test-Path -LiteralPath $deployKey) -or (Test-Path -LiteralPath "$deployKey.pub")) { throw 'Key path already exists; choose a new filename.' }
New-Item -ItemType Directory -Force (Split-Path -Parent $deployKey) | Out-Null
ssh-keygen -t ed25519 -C 'github-actions-fmfilms' -f $deployKey
Get-Content -LiteralPath "$deployKey.pub"
```

Through your trusted VPS/provider console as root, append **only the public
key** shown above. Replace the placeholder with that entire `ssh-ed25519 ...`
line. Existing authorized keys are retained:

```bash
install -d -m 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
public_key='PASTE_THE_SSH_ED25519_PUBLIC_KEY_LINE_HERE'
[[ $public_key == ssh-ed25519\ * ]] || { echo 'Expected a public key' >&2; exit 1; }
grep -qxF -- "$public_key" /root/.ssh/authorized_keys || printf '%s\n' "$public_key" >> /root/.ssh/authorized_keys
```

For `VPS_SSH_KEY`, copy the private file to your clipboard without printing it
to a terminal, paste it into the GitHub Actions secret, then clear the clipboard:

```powershell
Get-Content -Raw -LiteralPath $deployKey | Set-Clipboard
# Paste into GitHub secret VPS_SSH_KEY, then:
Set-Clipboard -Value ''
```

For the safest known-host entry, obtain the server's ED25519 public host key
through the trusted provider console, using the server's actual IPv4 address
in place of `VPS_PUBLIC_IP`. This outputs the exact format for `VPS_KNOWN_HOSTS`:

```bash
awk '{print "VPS_PUBLIC_IP " $1 " " $2}' /etc/ssh/ssh_host_ed25519_key.pub
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
```

Alternatively scan from PowerShell, with the IP entered at the prompt:

```powershell
$vpsAddress = Read-Host 'VPS IPv4 address'
$hostKeyFile = Join-Path $env:TEMP 'fmfilms-known-hosts'
ssh-keyscan -T 10 -p 22 -t ed25519 $vpsAddress 2>$null | Set-Content -Encoding ascii -LiteralPath $hostKeyFile
ssh-keygen -lf $hostKeyFile -E sha256
```

Compare that fingerprint with the trusted console fingerprint above before
copying the scanned entry into GitHub. A network scan alone does not establish
authenticity. After they match, use `Get-Content -LiteralPath $hostKeyFile`.

After the initial setup:

```bash
git push origin main
```

GitHub Actions serializes deployments, checks gateway regression tests and
shell syntax, runs relevant existing frontend tests, validates Compose, builds
all three production images, migrates/seeds an ephemeral CI database, starts
and checks every service, and validates generated HTTP/HTTPS blocks with Nginx.
Only then does it SSH into the VPS with the verified host key. It checks that
`origin/main` still matches the exact validated commit; an outdated run fails
instead of deploying unvalidated newer code.

The root-owned `/var/www/fmfilms` checkout is reset to that commit. Its ignored
`.env` and `.deployment` state are preserved; no `git clean` is used. The update
rejects incoming commits that track either private path before reset. The VPS
builds commit/time-tagged images while the current app remains available, backs
up the gateway and database, runs migrations/seed, and replaces only FM Films
services. Readiness failure fails the job and attempts to restart the previous
images. The deployment never runs global pruning, `compose down`, volume
deletion, or `--remove-orphans` against any project.

The initial server setup and Actions secrets must be in place before automatic
deployment can run. Repository changes alone do not configure GitHub secrets
or prove Actions-to-VPS access. Normal deployment does not request certificates;
the existing renewal scripts and timer remain responsible for renewal.

## Verification and logs

Run as root on the VPS:

```bash
cd /var/www/fmfilms
bash deploy/verify.sh
curl -I https://fmfilms.in
curl -I https://www.fmfilms.in
curl -I https://admin.fmfilms.in
curl --fail https://fmfilms.in/health
curl --fail https://admin.fmfilms.in/health
docker exec fmfilms-backend python /app/healthcheck.py api
docker ps
docker compose ps
docker exec lovenzea-gateway nginx -t
docker compose logs --tail=100 backend web admin
docker compose logs --tail=100 whatsapp-events whatsapp-media automations campaigns flow-delivery knowledge-base
```

Website 200/301/302/307/308 responses are accepted; 000 and 5xx fail. Public
health must return JSON status `ok` over verified TLS on all three hostnames.
Unauthenticated API requests must return 401, and the main site's cookie proxy
must also return 401, confirming both routing paths remain present.
The container check also probes the existing database health endpoint and
Redis. Verify real browser login, uploads and realtime events with authorized
test accounts after first setup. Other hosted sites should be spot-checked
using their known URLs; no unrelated container is restarted by these scripts.

## Rollback and persistent data

Each deployment retains the last good image tag, original commit, raw Compose
manifest, gateway snapshot and pre-migration PostgreSQL custom-format dump
under private `.deployment/`. No secrets are interpolated into saved manifests.
Updates also save `.deployment/previous-git-commit` before resetting Git.
Old images/volumes/backups are retained; provision disk space and a separate
off-server backup/retention policy.

```bash
cd /var/www/fmfilms
cat .deployment/current
cat .deployment/previous
bash deploy/rollback.sh

# Or select a retained release explicitly (substitute its actual tag):
bash deploy/rollback.sh RELEASE_TAG

# Inspect the commit associated with a retained release:
cat .deployment/releases/RELEASE_TAG/commit
```

Rollback uses the retained manifest/images without rebuilding or updating
PostgreSQL/Redis. It verifies production responses before changing the recorded
current release. It does not reverse database migrations, restore old secrets,
or delete uploads. An incompatible schema migration may require an explicitly
planned database restore from `.deployment/backups/RELEASE_TAG.dump`; automatic
restoration would discard newly written data, so the scripts do not do it.
Single-instance app updates can have a short replacement window; this is not a
zero-downtime deployment system.

If an earlier FM Films gateway section must also be restored, use the retained
gateway snapshot. This extracts **only** its FM Films section into the current
live file, preserving unrelated changes made since that snapshot:

```bash
bash deploy/setup-gateway.sh restore .deployment/releases/RELEASE_TAG/gateway.before.conf
```

The helper backs up and tests that restore before reload. Never copy a whole
historic gateway snapshot over newer unrelated site changes.

## Repository files

- `.github/workflows/deploy.yml`: validation and exact-commit SSH deployment.
- `Dockerfile`, `Dockerfile.admin`, `Dockerfile.backend`: production images.
- `docker-compose.yml`: isolated services, healthchecks, networks and volumes.
- `.dockerignore`, `.gitattributes`, `.gitignore`: private build context/state and LF shell scripts.
- `.env.example`, `deploy/init-env.py`: variable inventory and private first-time configuration.
- `deploy/gateway.py`, `deploy/setup-gateway.sh`: isolated gateway rendering, installation and restore.
- `deploy/setup-ssl.sh`, `deploy/renew-ssl.sh`: scoped certificate issuance/renewal.
- `deploy/fmfilms-cert-renew.service`, `deploy/fmfilms-cert-renew.timer`: renewal scheduling.
- `deploy/deploy.sh`, `deploy/rollback.sh`, `deploy/verify.sh`, `deploy/healthcheck.py`: deployment and checks.
- `deploy/tests/test_gateway.py`, `deploy/tests/test_init_env.py`: shared-gateway preservation and secret persistence tests.
- `deploy/AUDIT.md`, `deploy/README.md`, root `README.md`: audit and operating instructions.
- `frontend/next.config.ts`, `AdminSide/admin/next.config.ts`: standalone output.
- `frontend/src/lib/api/client.ts`: browser uses its own origin.
- `AdminSide/admin/app/unauthorized/page.tsx`, `frontend/public/webchat-demo.html`: production-safe links.
- `backend/requirements.txt`: upload/WebSocket runtime dependencies and removal of redundant unpinned entry.
- `AdminSide/docker-compose.yml`, `AdminSide/.env.example`: remove the duplicated legacy database password and require local configuration.

Implementation references: [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output),
[Nginx proxy directives](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[Certbot webroot and certificate management](https://eff-certbot.readthedocs.io/en/stable/using.html).
