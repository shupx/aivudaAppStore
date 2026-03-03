#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_CADDYFILE="${REPO_DIR}/Caddyfile"

FRONTEND_DIST="${1:-${REPO_DIR}/frontend_dev/dist}"

if [[ ! -f "${SOURCE_CADDYFILE}" ]]; then
  echo "Caddyfile not found: ${SOURCE_CADDYFILE}" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIST}" ]]; then
  echo "Frontend dist directory not found: ${FRONTEND_DIST}" >&2
  echo "Run 'cd frontend_dev && npm run build' first, or pass dist path as arg1." >&2
  exit 1
fi

TMP_CADDYFILE="$(mktemp)"
trap 'rm -f "${TMP_CADDYFILE}"' EXIT

awk -v dist="${FRONTEND_DIST}" '
  {
    if ($1 == "root" && $2 == "*" && !done) {
      print "  root * " dist
      done=1
    } else {
      print $0
    }
  }
  END {
    if (!done) {
      exit 2
    }
  }
' "${SOURCE_CADDYFILE}" > "${TMP_CADDYFILE}"

echo "Installing /etc/caddy/Caddyfile with frontend root: ${FRONTEND_DIST}"
sudo install -m 644 "${TMP_CADDYFILE}" /etc/caddy/Caddyfile

sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy || sudo systemctl restart caddy
sudo systemctl status caddy --no-pager -l

echo "Done. Caddy is running with systemd and absolute frontend root."
