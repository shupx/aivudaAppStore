#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

STACK_UNIT="${USER_SYSTEMD_DIR}/aivuda-appstore.service"
LEGACY_BACKEND_UNIT="${USER_SYSTEMD_DIR}/aivuda-appstore-backend.service"
LEGACY_CADDY_UNIT="${USER_SYSTEMD_DIR}/aivuda-appstore-caddy.service"
LEGACY_TARGET_UNIT="${USER_SYSTEMD_DIR}/aivuda-appstore.target"

CADDY_BIN="${REPO_DIR}/.tools/caddy/caddy"
CADDY_CONFIG="${REPO_DIR}/Caddyfile.nosudo"
FRONTEND_DIST="${REPO_DIR}/frontend_dev/dist"
STACK_RUN_SCRIPT="${REPO_DIR}/scripts/run_appstore_stack.sh"

mkdir -p "${USER_SYSTEMD_DIR}"

cat > "${STACK_UNIT}" <<EOF
[Unit]
Description=Aivuda AppStore Stack (backend + caddy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_DIR}
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

rm -f "${LEGACY_BACKEND_UNIT}" "${LEGACY_CADDY_UNIT}" "${LEGACY_TARGET_UNIT}"

echo "User service generated:"
echo "  - ${STACK_UNIT}"

if pgrep -af "python3 -m uvicorn main:app.*--port 9001|gunicorn.*main:app.*127.0.0.1:9001" >/dev/null; then
  echo ""
  echo "Warning: detected manually started backend process on port 9001."
  echo "Please stop it first, otherwise user service may fail to bind 127.0.0.1:9001."
fi

systemctl --user daemon-reload
systemctl --user disable --now aivuda-appstore-backend.service aivuda-appstore-caddy.service aivuda-appstore.target >/dev/null 2>&1 || true
systemctl --user enable --now aivuda-appstore.service

echo ""
echo "Done. Current status:"
systemctl --user --no-pager --full status aivuda-appstore.service || true

echo ""
echo "Manage commands:"
echo "  systemctl --user restart aivuda-appstore.service"
echo "  systemctl --user stop aivuda-appstore.service"
echo "  systemctl --user status aivuda-appstore.service"
echo "  journalctl --user -u aivuda-appstore.service -f"
echo ""
echo "If you need auto-start before login, run (requires admin):"
echo "  sudo loginctl enable-linger ${USER}"