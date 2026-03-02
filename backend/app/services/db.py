from __future__ import annotations

import re
import json
import sqlite3
from typing import Any

import semver as _semver

from fastapi import HTTPException

from app.core.settings import DB_PATH
from app.services.utils import now_ts


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(*, admin_password_hash: str) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS developer_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'developer',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_session (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES developer_user(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL UNIQUE,
                owner_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(owner_user_id) REFERENCES developer_user(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                version TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                published_at INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(app_id, version),
                FOREIGN KEY(app_id) REFERENCES app(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_target (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                artifact_relpath TEXT,
                artifact_sha256 TEXT,
                artifact_size INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(version_id),
                FOREIGN KEY(version_id) REFERENCES app_version(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                version_id INTEGER,
                actor_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                detail_json TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(app_id) REFERENCES app(id) ON DELETE CASCADE,
                FOREIGN KEY(version_id) REFERENCES app_version(id) ON DELETE SET NULL,
                FOREIGN KEY(actor_user_id) REFERENCES developer_user(id)
            )
            """
        )

        # --- Migrations for existing databases ---
        # Add description column to app_version if missing
        cols = {row[1] for row in conn.execute("PRAGMA table_info(app_version)").fetchall()}
        if "description" not in cols:
            conn.execute("ALTER TABLE app_version ADD COLUMN description TEXT NOT NULL DEFAULT ''")

        user = conn.execute("SELECT id FROM developer_user WHERE username = 'admin'").fetchone()
        if not user:
            ts = now_ts()
            conn.execute(
                """
                INSERT INTO developer_user (username, password_hash, role, created_at, updated_at)
                VALUES (?, ?, 'admin', ?, ?)
                """,
                ("admin", admin_password_hash, ts, ts),
            )

        conn.commit()


def create_audit_log(
    conn: sqlite3.Connection,
    *,
    app_id: int,
    actor_user_id: int,
    action: str,
    version_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO app_audit_log (app_id, version_id, actor_user_id, action, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (app_id, version_id, actor_user_id, action, json.dumps(detail or {}), now_ts()),
    )


def get_app_owned(conn: sqlite3.Connection, *, app_id_text: str, user: dict[str, Any]) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, app_id, owner_user_id, name, description FROM app WHERE app_id = ?",
        (app_id_text,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="App not found")
    if user["role"] != "admin" and row["owner_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Permission denied for this app")
    return row


def get_version_owned(conn: sqlite3.Connection, *, app_row: sqlite3.Row, version: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM app_version WHERE app_id = ? AND version = ?",
        (app_row["id"], version),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")
    return row


def _semver_sort_key(version_str: str) -> tuple:
    """Return a sortable key following semver precedence rules.

    Valid semver versions (parsed by the ``semver`` package) get
    priority ``(1, VersionInfo)`` so they sort above non-semver
    strings which get ``(0, lowercase_string)``.
    """
    try:
        ver = _semver.Version.parse(version_str.strip())
        return (1, ver)
    except ValueError:
        return (0, version_str.lower())


def pick_largest_published_version(conn: sqlite3.Connection, app_pk: int) -> sqlite3.Row | None:
    """Pick the published version with the largest semver version number.

    Valid semver versions are preferred; non-semver versions are sorted
    last by string comparison.
    """
    rows = conn.execute(
        """
        SELECT *
        FROM app_version
        WHERE app_id = ? AND status = 'published'
        """,
        (app_pk,),
    ).fetchall()
    if not rows:
        return None
    return max(rows, key=lambda r: _semver_sort_key(r["version"]))


def pick_latest_published_version(conn: sqlite3.Connection, app_pk: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM app_version
        WHERE app_id = ? AND status = 'published'
        ORDER BY published_at DESC, created_at DESC
        LIMIT 1
        """,
        (app_pk,),
    ).fetchone()


def get_targets(
    conn: sqlite3.Connection,
    *,
    version_id: int,
) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM app_target WHERE version_id = ?", (version_id,)).fetchall()


def build_manifest(
    *,
    app_row: sqlite3.Row,
    version_row: sqlite3.Row,
    target_rows: list[sqlite3.Row],
) -> dict[str, Any]:
    install_obj = {"url": "", "sha256": "", "size": 0}
    if target_rows:
        target = target_rows[0]
        relpath = target["artifact_relpath"]
        install_obj = {
            "url": f"/files/{relpath}" if relpath else "",
            "sha256": target["artifact_sha256"] or "",
            "size": target["artifact_size"] or 0,
        }

    return {
        "app_id": app_row["app_id"],
        "name": app_row["name"],
        "description": version_row["description"] or app_row["description"],
        "version": version_row["version"],
        "status": version_row["status"],
        "run": {
            "entrypoint": "./run.sh",
            "args": [],
        },
        "runtime": "host",
        "install": install_obj,
        "published_at": version_row["published_at"],
        "updated_at": version_row["updated_at"],
    }
