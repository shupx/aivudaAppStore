#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}" && pwd)"

BUILD_SEQ="${AIVUDAAPPSTORE_BUILD_SEQ:-01}"
BUILD_DATE="${AIVUDAAPPSTORE_BUILD_DATE:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PUBLISH_VENV_DIR="${PUBLISH_VENV_DIR:-${REPO_DIR}/.publish-venv}"
PUBLISH_TOOLS_DIR="${PUBLISH_TOOLS_DIR:-${REPO_DIR}/.publish-tools}"
SKIP_UPLOAD=0
NO_ISOLATION=0
REPOSITORY=""
REPOSITORY_URL=""

usage() {
  cat <<EOF
Usage: $0 [options]

Build Aivuda AppStore wheel/sdist and upload them to PyPI with twine.

Options:
  --skip-upload            Build and run twine check, but do not upload.
  --no-isolation           Pass --no-isolation to python -m build.
  --repository NAME        Twine repository name, for example: pypi or testpypi.
  --repository-url URL     Explicit twine repository URL.
  --python BIN             Python executable to use. Default: ${PYTHON_BIN}
  --venv-dir PATH          Virtualenv path for isolated build/twine tools.
  --tools-dir PATH         Fallback target dir for isolated build/twine tools.
  --build-date YYYYMMDD    Override AIVUDAAPPSTORE_BUILD_DATE.
  --build-seq NN           Override AIVUDAAPPSTORE_BUILD_SEQ. Default: ${BUILD_SEQ}
  -h, --help               Show this help.
  -V, --version            Print the current package version metadata if available.
EOF
}

print_version() {
  REPO_DIR="${REPO_DIR}" PYTHONPATH="${REPO_DIR}" "${PYTHON_BIN}" - <<'PY' 2>/dev/null || true
import os
from pathlib import Path
ns = {"__file__": str(Path(os.environ["REPO_DIR"]) / "setup.py")}
setup_path = Path(os.environ["REPO_DIR"]) / "setup.py"
code = setup_path.read_text(encoding="utf-8")
prefix = code.split("\nsetup(", 1)[0]
exec(prefix, ns)
print(ns["build_version"]())
PY
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upload) SKIP_UPLOAD=1; shift ;;
    --no-isolation) NO_ISOLATION=1; shift ;;
    --repository) REPOSITORY="${2:-}"; shift 2 ;;
    --repository-url) REPOSITORY_URL="${2:-}"; shift 2 ;;
    --python) PYTHON_BIN="${2:-}"; shift 2 ;;
    --venv-dir) PUBLISH_VENV_DIR="${2:-}"; shift 2 ;;
    --tools-dir) PUBLISH_TOOLS_DIR="${2:-}"; shift 2 ;;
    --build-date) BUILD_DATE="${2:-}"; shift 2 ;;
    --build-seq) BUILD_SEQ="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -V|--version) print_version; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_command "${PYTHON_BIN}"
require_command npm

cd "${REPO_DIR}"
rm -rf dist build aivudaappstore.egg-info "${PUBLISH_VENV_DIR}" "${PUBLISH_TOOLS_DIR}"

RUN_PYTHON=()
if "${PYTHON_BIN}" -m venv "${PUBLISH_VENV_DIR}" >/dev/null 2>&1; then
  VENV_PYTHON="${PUBLISH_VENV_DIR}/bin/python"
  VENV_PIP="${PUBLISH_VENV_DIR}/bin/pip"
  "${VENV_PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${VENV_PIP}" install --upgrade build twine
  RUN_PYTHON=("${VENV_PYTHON}")
else
  mkdir -p "${PUBLISH_TOOLS_DIR}"
  "${PYTHON_BIN}" -m pip install --upgrade --target "${PUBLISH_TOOLS_DIR}" pip setuptools wheel build twine
  RUN_PYTHON=("${PYTHON_BIN}")
fi

(
  cd aivudaappstore/resources/ui
  npm install
  npm run build
)

BUILD_ARGS=()
if [[ "${NO_ISOLATION}" -eq 1 ]]; then
  BUILD_ARGS+=(--no-isolation)
fi

AIVUDAAPPSTORE_BUILD_SEQ="${BUILD_SEQ}" \
AIVUDAAPPSTORE_BUILD_DATE="${BUILD_DATE}" \
PYTHONPATH="${PUBLISH_TOOLS_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
  "${RUN_PYTHON[@]}" -m build "${BUILD_ARGS[@]}"

PYTHONPATH="${PUBLISH_TOOLS_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
  "${RUN_PYTHON[@]}" -m twine check dist/*

if [[ "${SKIP_UPLOAD}" -eq 1 ]]; then
  ls -1 dist
  exit 0
fi

TWINE_ARGS=()
if [[ -n "${REPOSITORY}" ]]; then
  TWINE_ARGS+=(--repository "${REPOSITORY}")
fi
if [[ -n "${REPOSITORY_URL}" ]]; then
  TWINE_ARGS+=(--repository-url "${REPOSITORY_URL}")
fi

PYTHONPATH="${PUBLISH_TOOLS_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
  "${RUN_PYTHON[@]}" -m twine upload "${TWINE_ARGS[@]}" dist/*
