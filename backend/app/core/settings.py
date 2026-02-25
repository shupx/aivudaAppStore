from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
FILES_DIR = DATA_DIR / "files"
DB_PATH = DATA_DIR / "repo.db"

SESSION_TTL_SECONDS = 12 * 60 * 60


def ensure_storage_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
