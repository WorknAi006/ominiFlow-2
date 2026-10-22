#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mode=${1:-tls}
[[ $EUID == 0 ]] || { echo 'Run gateway setup as root.' >&2; exit 1; }
[[ $mode == tls || $mode == http || $mode == restore ]] || { echo 'Usage: setup-gateway.sh [http|tls|restore BACKUP_FILE]' >&2; exit 1; }
config=/var/www/lovenzea_v1/gateway.nginx.conf
exec 9>/run/lock/fmfilms-gateway.lock
flock -w 120 9
docker network inspect lovenzea_default >/dev/null
docker inspect lovenzea-gateway | python3 deploy/gateway.py preflight
docker exec lovenzea-gateway nginx -t
docker exec lovenzea-gateway nginx -T 2>/dev/null | python3 deploy/gateway.py check-dump
args=()
command=candidate
fingerprint=
if [[ $mode == tls ]]; then
  cert=$(python3 deploy/gateway.py certificate)
  fingerprint=$(sha256sum "$cert/fullchain.pem" | cut -d ' ' -f 1)
  args=(--certificate "$cert")
elif [[ $mode == restore ]]; then
  command=restore
  args=(--previous "${2:?A gateway backup file is required}")
elif python3 deploy/gateway.py certificate --allow-expired >/dev/null 2>&1; then
  echo 'An existing certificate is available; refusing to downgrade HTTPS to bootstrap HTTP.' >&2
  exit 1
fi
candidate=$(mktemp)
backup=
modified=0
cleanup() {
  status=$?
  trap - EXIT
  if (( status != 0 && modified )); then
    echo "Restoring gateway from $backup" >&2
    # Preserve the inode: the gateway bind-mounts this individual file.
    cat "$backup" > "$config"
    if docker exec lovenzea-gateway nginx -t; then
      docker exec lovenzea-gateway nginx -s reload || true
    fi
  fi
  rm -f "$candidate"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
python3 deploy/gateway.py "$command" --config "$config" --output "$candidate" "${args[@]}"
if cmp -s "$candidate" "$config"; then
  if [[ $mode == tls && $fingerprint != "$(cat .deployment/gateway-cert.sha256 2>/dev/null || true)" ]]; then
    docker exec lovenzea-gateway nginx -s reload
    mkdir -p .deployment
    printf '%s\n' "$fingerprint" > .deployment/gateway-cert.sha256
    echo 'Reloaded the renewed FM Films certificate after successful validation.'
  else
    echo 'FM Films gateway configuration is already current; no reload.'
  fi
  exit 0
fi
backup="${config}.backup.$(date -u +%Y%m%d-%H%M%S)-$$"
cp -p -- "$config" "$backup"
modified=1
cat "$candidate" > "$config"
test_output=$(docker exec lovenzea-gateway nginx -t 2>&1) || { echo "$test_output" >&2; exit 1; }
echo "$test_output"
if [[ $test_output == *'conflicting server name'* ]]; then
  echo 'Conflicting server names detected; restoring backup.' >&2
  exit 1
fi
docker exec lovenzea-gateway nginx -s reload
modified=0
if [[ $mode == tls ]]; then
  mkdir -p .deployment
  printf '%s\n' "$fingerprint" > .deployment/gateway-cert.sha256
fi
echo "Installed FM Films section. Backup: $backup"
