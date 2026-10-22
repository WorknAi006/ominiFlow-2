#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $EUID == 0 ]] || { echo 'Run SSL setup as root.' >&2; exit 1; }
email=${1:?Usage: setup-ssl.sh YOUR_LETSENCRYPT_EMAIL}
command -v certbot >/dev/null
docker inspect lovenzea-gateway | python3 deploy/gateway.py preflight
if ! python3 deploy/gateway.py certificate >/dev/null 2>&1; then
  if ! python3 deploy/gateway.py certificate --allow-expired >/dev/null 2>&1; then
    # Never expand or replace another site's existing certificate named fmfilms.
    if [[ -e /etc/letsencrypt/renewal/fmfilms.conf ]]; then
      echo 'An unexpected fmfilms certificate lineage exists; inspect it manually.' >&2
      exit 1
    fi
    bash deploy/setup-gateway.sh http
    certbot certonly --webroot -w /var/www/certbot \
      --cert-name fmfilms --keep-until-expiring --non-interactive --agree-tos \
      --email "$email" -d fmfilms.in -d www.fmfilms.in -d admin.fmfilms.in
  else
    cert=$(python3 deploy/gateway.py certificate --allow-expired)
    certbot renew --cert-name "${cert##*/}" --non-interactive
  fi
fi
bash deploy/setup-gateway.sh tls
echo 'Certificate detected and HTTPS installed. Enable the FM Films renewal timer per deploy/README.md.'
