#!/usr/bin/env bash
set -e

echo "[pre_uninstall] start"

## your uninstall commands
for i in {1..3}; do
  echo "uninstalling"
  sleep 1
done

echo "[pre_uninstall] done"
