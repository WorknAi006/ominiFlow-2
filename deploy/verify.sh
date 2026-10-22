#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker exec lovenzea-gateway nginx -t
for host in fmfilms.in www.fmfilms.in admin.fmfilms.in; do
  code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 10 --max-time 30 --retry 3 --retry-all-errors "https://$host/")
  case "$code" in
    200|301|302|307|308) echo "$host: $code" ;;
    *) echo "$host: unexpected status $code" >&2; exit 1 ;;
  esac
  # Redirects do not count as API success. TLS validation remains enabled.
  body=$(curl --fail --silent --show-error --connect-timeout 10 --max-time 30 \
    --retry 3 --retry-all-errors "https://$host/health")
  printf '%s' "$body" | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'
  api_code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 10 --max-time 30 "https://$host/api/v1/tenants/current")
  [[ $api_code == 401 ]] || { echo "$host API routing failed: $api_code" >&2; exit 1; }
done
bridge_code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --connect-timeout 10 --max-time 30 https://fmfilms.in/api/contacts)
[[ $bridge_code == 401 ]] || { echo "Next.js cookie proxy routing failed: $bridge_code" >&2; exit 1; }
docker exec fmfilms-backend python /app/healthcheck.py api
docker exec fmfilms-web node -e "fetch('http://127.0.0.1:3000/api/contacts').then(r=>{if(r.status!==401)process.exit(1)}).catch(()=>process.exit(1))"
