#!/usr/bin/env bash
set -e

echo "[update_this_version] running steps of updating this version"

## your updating commands
for i in {1..3}; do
  echo "updating..."
  sleep 1
done

echo "[update_this_version] done"
