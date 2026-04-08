#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="${AIVUDAAPPSTORE_WS_ROOT:-${HOME}/aivudaAppStore_ws}"
RUNTIME_CADDY_CONFIG="${RUNTIME_ROOT}/config/Caddyfile"
USER_SYSTEMD_UNIT="${HOME}/.config/systemd/user/aivudaappstore.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

source "${SCRIPT_DIR}/_read_appstore_hosts.sh"

print_install_hint() {
  echo -e "\033[0;33maivudaappstore is not ready yet. Please run \033[1maivudaappstore install\033[0;33m first.\033[0m" >&2
}

main() {
  local public_host=""
  local private_host=""

  if [[ ! -f "${RUNTIME_CADDY_CONFIG}" || ! -f "${USER_SYSTEMD_UNIT}" ]]; then
    print_install_hint
    return 1
  fi

  public_host="${APPSTORE_PUBLIC_HTTPS_HOST:-}"
  private_host="${APPSTORE_PRIVATE_HTTPS_HOST:-}"
  if [[ -z "${public_host}" ]]; then
    public_host="$(read_appstore_host_from_unit APPSTORE_PUBLIC_HTTPS_HOST 2>/dev/null || true)"
  fi
  if [[ -z "${private_host}" ]]; then
    private_host="$(read_appstore_host_from_unit APPSTORE_PRIVATE_HTTPS_HOST 2>/dev/null || true)"
  fi

  public_host="${public_host:-127.0.0.1}"
  private_host="${private_host:-127.0.0.1}"

  echo "Aivuda AppStore web addresses:"
  echo "  Admin:  https://${private_host}:8543"
  echo "  Public: https://${public_host}:8580"
}

main "$@"
