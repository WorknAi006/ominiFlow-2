#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $EUID == 0 ]] || { echo 'Run rollback as root.' >&2; exit 1; }
exec 8>/run/lock/fmfilms-deploy.lock
flock -w 120 8
target=${1:-$(cat .deployment/previous)}
[[ $target =~ ^[a-f0-9]{12}-[0-9]{14}-[0-9]+$ ]] || exit 1
[[ -f .deployment/releases/$target/compose.yml ]] || exit 1
current=$(cat .deployment/current)
IMAGE_TAG=$target docker compose --project-name fmfilms --project-directory "$PWD" \
  --env-file "$PWD/.env" -f ".deployment/releases/$target/compose.yml" \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 240 \
  backend web admin whatsapp-events whatsapp-media automations campaigns flow-delivery knowledge-base
bash deploy/verify.sh
printf '%s\n' "$current" > .deployment/previous
printf '%s\n' "$target" > .deployment/current
echo "Restored $target. Database schema and persistent volumes were retained."
