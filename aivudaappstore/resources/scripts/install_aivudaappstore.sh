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

USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
RUNTIME_ROOT="${AIVUDAAPPSTORE_WS_ROOT:-${HOME}/aivudaAppStore_ws}"
STACK_UNIT="${USER_SYSTEMD_DIR}/aivudaappstore.service"
CADDY_BIN="${RUNTIME_ROOT}/.tools/caddy/caddy"
CADDY_TEMPLATE="${PACKAGE_ROOT}/caddy/Caddyfile_template"
CADDY_CONFIG="${RUNTIME_ROOT}/config/Caddyfile"
FRONTEND_DIST="${PACKAGE_ROOT}/ui/dist"
STACK_RUN_SCRIPT="${SCRIPT_DIR}/_run_aivudaappstore_stack.sh"
DOWNLOAD_CADDY_HELPER="${SCRIPT_DIR}/_download_caddy.sh"
APPSTORE_PUBLIC_HTTPS_HOST="${APPSTORE_PUBLIC_HTTPS_HOST:-}"
APPSTORE_PRIVATE_HTTPS_HOST="${APPSTORE_PRIVATE_HTTPS_HOST:-}"
WORKING_DIRECTORY="${RUNTIME_ROOT}"

if [[ -n "${SOURCE_ROOT}" ]]; then
  WORKING_DIRECTORY="${SOURCE_ROOT}"
fi

list_local_ipv4_candidates() {
  local ip_list=()
  local token=""

  if command -v hostname >/dev/null 2>&1; then
    for token in $(hostname -I 2>/dev/null || true); do
      if [[ "${token}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && [[ "${token}" != "127.0.0.1" ]]; then
        ip_list+=("${token}")
      fi
    done
  fi

  if command -v ip >/dev/null 2>&1; then
    while IFS= read -r token; do
      if [[ "${token}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && [[ "${token}" != "127.0.0.1" ]]; then
        ip_list+=("${token}")
      fi
    done < <(ip -o -4 addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
  fi

  if [[ ${#ip_list[@]} -gt 0 ]]; then
    printf "%s\n" "${ip_list[@]}" | awk '!seen[$0]++'
  fi
}

prompt_private_https_host() {
  local candidates=()
  local idx=0
  local pick=""

  while IFS= read -r line; do
    [[ -n "${line}" ]] && candidates+=("${line}")
  done < <(list_local_ipv4_candidates)

  if [[ ${#candidates[@]} -eq 0 ]]; then
    read -r -p "Input HTTPS private IP/domain for Caddy (APPSTORE_PRIVATE_HTTPS_HOST, press Enter to skip): " APPSTORE_PRIVATE_HTTPS_HOST
    return
  fi

  echo "Detected local IPv4 addresses:"
  for idx in "${!candidates[@]}"; do
    printf "  [%d] %s\n" "$((idx + 1))" "${candidates[idx]}"
  done
  echo "  [m] Manual input"
  echo "  [s] Skip"

  read -r -p "Select private IP [1-${#candidates[@]}], m, or s to skip: " pick
  if [[ "${pick}" =~ ^[0-9]+$ ]] && (( pick >= 1 && pick <= ${#candidates[@]} )); then
    APPSTORE_PRIVATE_HTTPS_HOST="${candidates[pick-1]}"
  elif [[ "${pick}" == "s" || "${pick}" == "S" ]]; then
    APPSTORE_PRIVATE_HTTPS_HOST=""
  else
    read -r -p "Input HTTPS private IP/domain for Caddy (APPSTORE_PRIVATE_HTTPS_HOST, press Enter to skip): " APPSTORE_PRIVATE_HTTPS_HOST
  fi
}

ensure_https_hosts() {
  if [[ -z "${APPSTORE_PUBLIC_HTTPS_HOST}" ]]; then
    read -r -p "Input HTTPS public IP/domain for Caddy (APPSTORE_PUBLIC_HTTPS_HOST, press Enter to skip): " APPSTORE_PUBLIC_HTTPS_HOST
  fi
  if [[ -z "${APPSTORE_PRIVATE_HTTPS_HOST}" ]]; then
    prompt_private_https_host
  fi
}

ensure_user_linger_enabled() {
  local linger_state=""
  linger_state="$(loginctl show-user "${USER}" -p Linger --value 2>/dev/null || true)"

  if [[ "${linger_state}" == "yes" ]]; then
    return
  fi

  echo ""
  echo "Enable user linger for boot auto-start before login."
  echo "Running: sudo loginctl enable-linger ${USER}"
  sudo loginctl enable-linger "${USER}"
}

mkdir -p "${USER_SYSTEMD_DIR}" "${RUNTIME_ROOT}/config" "${RUNTIME_ROOT}/data/files/apps" "${RUNTIME_ROOT}/samples"

ensure_https_hosts
ensure_user_linger_enabled

if [[ ! -x "${CADDY_BIN}" ]]; then
  "${DOWNLOAD_CADDY_HELPER}" --output "${CADDY_BIN}"
fi

if [[ ! -d "${FRONTEND_DIST}" ]]; then
  echo "Frontend dist not found: ${FRONTEND_DIST}" >&2
  echo "Run: cd ${PACKAGE_ROOT}/ui && npm run build" >&2
  exit 1
fi

cp "${CADDY_TEMPLATE}" "${CADDY_CONFIG}"

cat > "${STACK_UNIT}" <<EOF
[Unit]
Description=Aivuda AppStore Stack (backend + caddy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${WORKING_DIRECTORY}
Environment=AIVUDAAPPSTORE_WS_ROOT=${RUNTIME_ROOT}
Environment=AIVUDAAPPSTORE_PACKAGE_ROOT=${PACKAGE_ROOT}
Environment=APPSTORE_PUBLIC_HTTPS_HOST=${APPSTORE_PUBLIC_HTTPS_HOST}
Environment=APPSTORE_PRIVATE_HTTPS_HOST=${APPSTORE_PRIVATE_HTTPS_HOST}
Environment=AIVUDAAPPSTORE_FRONTEND_DIST=${FRONTEND_DIST}
Environment=AIVUDAAPPSTORE_FILES_ROOT=${RUNTIME_ROOT}/data/files
Environment=AIVUDAAPPSTORE_FILES_APPS_ROOT=${RUNTIME_ROOT}/data/files/apps
ExecStartPre=/usr/bin/test -x ${CADDY_BIN}
ExecStartPre=/usr/bin/test -f ${CADDY_CONFIG}
ExecStartPre=/usr/bin/test -d ${FRONTEND_DIST}
ExecStartPre=/usr/bin/test -f ${STACK_RUN_SCRIPT}
ExecStart=/usr/bin/env bash ${STACK_RUN_SCRIPT}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

rm -f "${USER_SYSTEMD_DIR}/aivuda-appstore.service" \
  "${USER_SYSTEMD_DIR}/aivuda-appstore-backend.service" \
  "${USER_SYSTEMD_DIR}/aivuda-appstore-caddy.service" \
  "${USER_SYSTEMD_DIR}/aivuda-appstore.target"

systemctl --user stop aivudaappstore.service >/dev/null 2>&1 || true
systemctl --user disable aivudaappstore.service >/dev/null 2>&1 || true
systemctl --user daemon-reload
systemctl --user enable --now aivudaappstore.service

echo ""
echo "aivudaappstore.service is started and enabled."
echo "  Admin UI:  https://${APPSTORE_PRIVATE_HTTPS_HOST:-127.0.0.1}:8543"
echo "  Public UI: https://${APPSTORE_PUBLIC_HTTPS_HOST:-127.0.0.1}:8580"
