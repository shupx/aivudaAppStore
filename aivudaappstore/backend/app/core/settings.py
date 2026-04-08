from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
RESOURCES_ROOT = PACKAGE_ROOT / "resources"
WORKSPACE_ROOT = Path(
    os.environ.get("AIVUDAAPPSTORE_WS_ROOT", str(Path.home() / "aivudaAppStore_ws"))
).expanduser().resolve()

DATA_DIR = WORKSPACE_ROOT / "data"
FILES_DIR = DATA_DIR / "files"
FILES_APPS_DIR = FILES_DIR / "apps"
TMP_DIR = DATA_DIR / "tmp"
DB_PATH = DATA_DIR / "repo.db"
CONFIG_DIR = WORKSPACE_ROOT / "config"
TOOLS_DIR = WORKSPACE_ROOT / ".tools"
CADDY_BIN = TOOLS_DIR / "caddy" / "caddy"
RUNTIME_CADDY_CONFIG = CONFIG_DIR / "Caddyfile"
SAMPLES_DIR = WORKSPACE_ROOT / "samples"
SAMPLES_SOURCE_DIR = RESOURCES_ROOT / "samples"
FRONTEND_UI_DIR = RESOURCES_ROOT / "ui"
FRONTEND_UI_DIST_DIR = FRONTEND_UI_DIR / "dist"
APPSTORE_API_PREFIX = "/aivuda_app_store"
SESSION_TTL_SECONDS = 12 * 60 * 60


def ensure_storage_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    FILES_APPS_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
