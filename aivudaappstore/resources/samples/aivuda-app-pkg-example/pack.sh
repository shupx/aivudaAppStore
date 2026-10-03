#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_NAME="$(basename "${SCRIPT_DIR}")"
OUTPUT_DIR="${1:-$(dirname "${SCRIPT_DIR}")}"
OUTPUT_DIR="$(mkdir -p "${OUTPUT_DIR}" && cd "${OUTPUT_DIR}" && pwd)"
OUTPUT_PATH="${OUTPUT_DIR}/${PKG_NAME}.tar.gz"

if ! command -v tar >/dev/null 2>&1; then
  echo "tar is required" >&2
  exit 1
fi

tar \
  --exclude='.git' \
  --exclude="$(basename "${OUTPUT_PATH}")" \
  -czf "${OUTPUT_PATH}" \
  -C "${SCRIPT_DIR}" \
  .

echo "Created: ${OUTPUT_PATH}"
