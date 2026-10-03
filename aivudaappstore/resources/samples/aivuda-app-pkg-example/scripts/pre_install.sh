#!/usr/bin/env bash
set -e

echo "[pre_install] checking system prerequisites"
command -v bash >/dev/null 2>&1 || { echo "bash not found"; exit 1; }
command -v systemctl >/dev/null 2>&1 || echo "systemctl not found, fallback runtime may be used"

## your install commands
for i in {1..3}; do
  echo "installing..."
  sleep 1
done

echo "[pre_install] done"
