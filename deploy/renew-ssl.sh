#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $EUID == 0 ]] || { echo 'Run certificate renewal as root.' >&2; exit 1; }
[[ ${1:-} == '' || ${1:-} == --dry-run ]] || exit 1
docker inspect lovenzea-gateway | python3 deploy/gateway.py preflight
cert=$(python3 deploy/gateway.py certificate --allow-expired)
exec 9>/run/lock/fmfilms-gateway.lock
flock -w 120 9
args=()
if [[ ${1:-} == --dry-run ]]; then args=(--dry-run); fi
# cert-name restricts this job to FM Films. Existing server-wide renewal jobs
# may have renewed it first; setup-gateway compares the certificate fingerprint.
certbot renew --cert-name "${cert##*/}" --non-interactive "${args[@]}"
flock -u 9
if [[ ${1:-} != --dry-run ]]; then bash deploy/setup-gateway.sh tls; fi
