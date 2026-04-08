#!/usr/bin/env bash
set -euo pipefail

USER_SYSTEMD_UNIT="${HOME}/.config/systemd/user/aivudaappstore.service"

read_appstore_host_from_unit() {
  local key="$1"
  if [[ ! -f "${USER_SYSTEMD_UNIT}" ]]; then
    return 1
  fi
  grep -E "^Environment=${key}=" "${USER_SYSTEMD_UNIT}" | tail -n 1 | cut -d= -f3-
}
