#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -n "${AIVUDAAPPSTORE_PACKAGE_ROOT:-}" ]]; then
  PACKAGE_ROOT="$(cd "${AIVUDAAPPSTORE_PACKAGE_ROOT}" && pwd -P)"
else
  PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
fi
SOURCE_ROOT_CANDIDATE="$(cd "${PACKAGE_ROOT}/../.." && pwd -P)"
SOURCE_ROOT=""
if [[ -f "${SOURCE_ROOT_CANDIDATE}/setup.py" ]]; then
  SOURCE_ROOT="${SOURCE_ROOT_CANDIDATE}"
fi

RUNTIME_ROOT="${AIVUDAAPPSTORE_WS_ROOT:-${HOME}/aivudaAppStore_ws}"
PYTHONPATH_PREFIX="${PYTHONPATH:-}"
DEV_MODE=0

usage() {
  cat <<EOF
Usage: $0 [--dev]

Options:
  --dev    Run backend with uvicorn reload and frontend with vite build --watch
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev)
      DEV_MODE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

CADDY_BIN="${RUNTIME_ROOT}/.tools/caddy/caddy"
CADDY_TEMPLATE="${PACKAGE_ROOT}/caddy/Caddyfile_template"
CADDY_CONFIG="${RUNTIME_ROOT}/config/Caddyfile"
FRONTEND_DIR="${PACKAGE_ROOT}/ui"
FRONTEND_DIST="${FRONTEND_DIR}/dist"
FILES_ROOT="${RUNTIME_ROOT}/data/files"
FILES_APPS_ROOT="${FILES_ROOT}/apps"

if [[ ! -x "${CADDY_BIN}" ]]; then
  echo "Caddy binary not found or not executable: ${CADDY_BIN}" >&2
  exit 1
fi

mkdir -p "${RUNTIME_ROOT}/config" "${FILES_APPS_ROOT}" "${RUNTIME_ROOT}/samples"

if [[ ! -f "${CADDY_CONFIG}" ]]; then
  cp "${CADDY_TEMPLATE}" "${CADDY_CONFIG}"
fi

if [[ ! -f "${CADDY_CONFIG}" ]]; then
  echo "Caddy config not found: ${CADDY_CONFIG}" >&2
  exit 1
fi

if [[ "${DEV_MODE}" -eq 0 && ! -d "${FRONTEND_DIST}" ]]; then
  echo "Frontend dist not found: ${FRONTEND_DIST}" >&2
  echo "Run: cd ${FRONTEND_DIR} && npm run build" >&2
  exit 1
fi

if [[ "${DEV_MODE}" -eq 1 ]]; then
  if [[ -z "${SOURCE_ROOT}" ]]; then
    echo "Dev mode is only supported from a source checkout." >&2
    exit 1
  fi
  if [[ -n "${PYTHONPATH_PREFIX}" ]]; then
    PYTHONPATH_PREFIX="${SOURCE_ROOT}:${PYTHONPATH_PREFIX}"
  else
    PYTHONPATH_PREFIX="${SOURCE_ROOT}"
  fi
  mkdir -p "${FRONTEND_DIST}"
fi

export AIVUDAAPPSTORE_FILES_ROOT="${FILES_ROOT}"
export AIVUDAAPPSTORE_FILES_APPS_ROOT="${FILES_APPS_ROOT}"
export AIVUDAAPPSTORE_FRONTEND_DIST="${FRONTEND_DIST}"
export APPSTORE_PUBLIC_HTTPS_HOST="${APPSTORE_PUBLIC_HTTPS_HOST:-127.0.0.1}"
export APPSTORE_PRIVATE_HTTPS_HOST="${APPSTORE_PRIVATE_HTTPS_HOST:-127.0.0.1}"

cd "${RUNTIME_ROOT}"

if [[ "${DEV_MODE}" -eq 1 ]]; then
  env PYTHONPATH="${PYTHONPATH_PREFIX}" /usr/bin/env python3 -m uvicorn aivudaappstore.backend.main:app --host 127.0.0.1 --port 9001 --reload --reload-dir "${SOURCE_ROOT}/aivudaappstore/backend" &
else
  env PYTHONPATH="${PYTHONPATH_PREFIX}" /usr/bin/env python3 -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker aivudaappstore.backend.main:app -b 127.0.0.1:9001 &
fi
backend_pid=$!

vite_pid=""
if [[ "${DEV_MODE}" -eq 1 ]]; then
  (
    cd "${FRONTEND_DIR}"
    npm exec vite build -- --watch
  ) &
  vite_pid=$!
fi

(
  cd "${PACKAGE_ROOT}"
  "${CADDY_BIN}" run --config "${CADDY_CONFIG}"
) &
caddy_pid=$!

shutdown() {
  kill "${backend_pid}" >/dev/null 2>&1 || true
  kill "${caddy_pid}" >/dev/null 2>&1 || true
  if [[ -n "${vite_pid}" ]]; then
    kill "${vite_pid}" >/dev/null 2>&1 || true
  fi
  wait "${backend_pid}" >/dev/null 2>&1 || true
  wait "${caddy_pid}" >/dev/null 2>&1 || true
  if [[ -n "${vite_pid}" ]]; then
    wait "${vite_pid}" >/dev/null 2>&1 || true
  fi
}

trap shutdown TERM INT

sleep 2
echo "Aivuda AppStore web addresses:"
echo "  Admin:  https://${APPSTORE_PRIVATE_HTTPS_HOST}:8543"
echo "  Public: https://${APPSTORE_PUBLIC_HTTPS_HOST}:8580"

set +e
if [[ -n "${vite_pid}" ]]; then
  wait -n "${backend_pid}" "${caddy_pid}" "${vite_pid}"
else
  wait -n "${backend_pid}" "${caddy_pid}"
fi
exit_code=$?
set -e

shutdown
exit "${exit_code}"
