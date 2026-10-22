#!/usr/bin/env bash
# Build before replacing services; retain versioned images and last good manifest.
set -Eeuo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $EUID == 0 ]] || { echo 'Run deployment as root.' >&2; exit 1; }
mode=${1:-production}
[[ $mode == production || $mode == --bootstrap ]] || exit 1
exec 8>/run/lock/fmfilms-deploy.lock
flock -w 1800 8
[[ -f .env && ! -L .env ]] || { echo 'Create the VPS-only .env first.' >&2; exit 1; }
[[ -z $(git ls-files -- .env) ]] || { echo '.env must never be tracked.' >&2; exit 1; }
chmod 600 .env
mkdir -p .deployment/releases .deployment/backups
if [[ $mode == --bootstrap && -f .deployment/current ]]; then
  echo 'A production release already exists; run deploy.sh without --bootstrap.' >&2
  exit 1
fi
docker network inspect lovenzea_default >/dev/null
docker inspect lovenzea-gateway | python3 deploy/gateway.py preflight
docker exec lovenzea-gateway nginx -t
# No gateway or service mutations until the production certificate exists.
if [[ $mode == production ]]; then python3 deploy/gateway.py certificate >/dev/null; fi
previous=
if [[ -f .deployment/current ]]; then previous=$(cat .deployment/current); fi
if [[ -z $previous && -f .deployment/bootstrap ]]; then previous=$(cat .deployment/bootstrap); fi
[[ -z $previous || $previous =~ ^[a-f0-9]{12}-[0-9]{14}-[0-9]+$ ]] || exit 1
export IMAGE_TAG="$(git rev-parse --short=12 HEAD)-$(date -u +%Y%m%d%H%M%S)-$$"
release=".deployment/releases/$IMAGE_TAG"
mkdir -p "$release"
git rev-parse HEAD > "$release/commit"
cp docker-compose.yml "$release/compose.yml"
cp -p /var/www/lovenzea_v1/gateway.nginx.conf "$release/gateway.before.conf"
compose() { docker compose --project-name fmfilms --env-file .env "$@"; }
compose config --quiet
# Explicitly scope every build and update to this Compose project.
compose build web admin backend
# Dependency startup leaves current application containers serving during builds.
compose up -d --wait --wait-timeout 120 postgres redis
compose exec -T postgres pg_dump -U fmfilms -d fmfilms -Fc > ".deployment/backups/$IMAGE_TAG.dump"
compose run --rm --no-deps backend alembic upgrade head
compose run --rm --no-deps backend python -m app.db.run_seed
changed=0
rollback_on_error() {
  status=$?
  trap - EXIT
  if (( status != 0 && changed )); then
    echo 'Deployment failed. Attempting to restore the previous application images.' >&2
    if [[ -n $previous ]]; then
      IMAGE_TAG=$previous docker compose --project-name fmfilms --project-directory "$PWD" \
        --env-file "$PWD/.env" -f ".deployment/releases/$previous/compose.yml" \
        up -d --no-deps --no-build --pull never --wait --wait-timeout 180 \
        backend web admin whatsapp-events whatsapp-media automations campaigns flow-delivery knowledge-base || true
    else
      echo 'No previous release exists. Inspect FM Films container logs.' >&2
    fi
    bash deploy/setup-gateway.sh restore "$release/gateway.before.conf" || true
    echo 'Database migrations are not automatically reversed; the pre-migration dump is retained.' >&2
  fi
  exit "$status"
}
trap rollback_on_error EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
changed=1
compose up -d --no-build --pull never --wait --wait-timeout 240 \
  backend web admin whatsapp-events whatsapp-media automations campaigns flow-delivery knowledge-base
if [[ $mode == production ]]; then
  bash deploy/setup-gateway.sh tls
  bash deploy/verify.sh
else
  docker exec fmfilms-backend python /app/healthcheck.py api
  echo 'Bootstrap containers are healthy. Run SSL setup, then a production deployment.'
fi
if [[ $mode == production ]]; then
  if [[ -n $previous ]]; then printf '%s\n' "$previous" > .deployment/previous; fi
  printf '%s\n' "$IMAGE_TAG" > .deployment/current
else
  printf '%s\n' "$IMAGE_TAG" > .deployment/bootstrap
fi
changed=0
echo "FM Films release: $IMAGE_TAG"
compose ps
