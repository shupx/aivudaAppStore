#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPTS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
RUNTIME_ROOT="${AIVUDAAPPSTORE_WS_ROOT:-${HOME}/aivudaAppStore_ws}"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
STACK_SERVICE_NAME="aivudaappstore.service"
STACK_UNIT="${USER_SYSTEMD_DIR}/${STACK_SERVICE_NAME}"
INSTALL_SCRIPT="${SCRIPTS_DIR}/install_aivudaappstore.sh"

log() {
  echo "[aivudaappstore-systemd] $*"
}

ensure_systemctl_user_available() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl is not available in PATH." >&2
    exit 1
  fi

  if ! systemctl --user --version >/dev/null 2>&1; then
    echo "systemctl --user is not available in the current environment." >&2
    exit 1
  fi
}

ensure_stack_unit_exists() {
  if [[ -f "${STACK_UNIT}" ]]; then
    return
  fi

  echo "Aivuda AppStore user service is not installed: ${STACK_UNIT}" >&2
  echo "Run: bash ${INSTALL_SCRIPT}" >&2
  exit 1
}

is_stack_active() {
  systemctl --user is-active --quiet "${STACK_SERVICE_NAME}"
}

is_stack_enabled() {
  systemctl --user is-enabled --quiet "${STACK_SERVICE_NAME}"
}
