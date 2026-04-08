#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WEB_HINT_SCRIPT="${SCRIPT_DIR}/_web_hint.sh"
source "${SCRIPT_DIR}/helpers/_aivudaappstore_systemd_common.sh"

ensure_systemctl_user_available
ensure_stack_unit_exists

if is_stack_active; then
  log "${STACK_SERVICE_NAME} is already running."
  exit 0
fi

log "Starting ${STACK_SERVICE_NAME}..."
systemctl --user start "${STACK_SERVICE_NAME}"
log "${STACK_SERVICE_NAME} started."
bash "${WEB_HINT_SCRIPT}" || true
