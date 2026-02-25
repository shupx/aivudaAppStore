from __future__ import annotations

import json
import sqlite3
from typing import Any

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
                category TEXT NOT NULL DEFAULT 'general',
                icon TEXT NOT NULL DEFAULT 'box',
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
                status TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'stable',
                changelog TEXT NOT NULL DEFAULT '',
                run_entrypoint TEXT NOT NULL DEFAULT './run.sh',
                run_args_json TEXT NOT NULL DEFAULT '[]',
                install_script TEXT NOT NULL DEFAULT '',
                uninstall_script TEXT NOT NULL DEFAULT '',
                start_script TEXT NOT NULL DEFAULT '',
                stop_script TEXT NOT NULL DEFAULT '',
                healthcheck_script TEXT NOT NULL DEFAULT '',
                config_schema_json TEXT NOT NULL DEFAULT '{"type":"object","properties":{}}',
                default_config_json TEXT NOT NULL DEFAULT '{}',
                extra_json TEXT NOT NULL DEFAULT '{}',
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
                os TEXT NOT NULL,
                arch TEXT NOT NULL,
                runtime TEXT NOT NULL,
                image_ref TEXT,
                image_digest TEXT,
                artifact_relpath TEXT,
                artifact_sha256 TEXT,
                artifact_size INTEGER,
                min_os_version TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(version_id, os, arch),
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
        "SELECT id, app_id, owner_user_id, name, description, category, icon FROM app WHERE app_id = ?",
        (app_id_text,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="app 不存在")
    if user["role"] != "admin" and row["owner_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="无权限操作该 app")
    return row


def get_version_owned(conn: sqlite3.Connection, *, app_row: sqlite3.Row, version: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM app_version WHERE app_id = ? AND version = ?",
        (app_row["id"], version),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="版本不存在")
    return row


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
    os_name: str | None = None,
    arch: str | None = None,
    normalized_platform_getter,
) -> list[sqlite3.Row]:
    if os_name and arch:
        os_text, arch_text = normalized_platform_getter(os_name, arch)
        return conn.execute(
            "SELECT * FROM app_target WHERE version_id = ? AND os = ? AND arch = ?",
            (version_id, os_text, arch_text),
        ).fetchall()

    return conn.execute("SELECT * FROM app_target WHERE version_id = ?", (version_id,)).fetchall()


def build_manifest(
    *,
    app_row: sqlite3.Row,
    version_row: sqlite3.Row,
    target_rows: list[sqlite3.Row],
) -> dict[str, Any]:
    targets = []
    for target in target_rows:
        if target["runtime"] in {"docker", "podman"}:
            install_obj = {
                "image": target["image_ref"],
                "image_digest": target["image_digest"],
                "sha256": target["artifact_sha256"] or "",
            }
        else:
            relpath = target["artifact_relpath"]
            install_obj = {
                "url": f"/files/{relpath}" if relpath else "",
                "sha256": target["artifact_sha256"] or "",
                "size": target["artifact_size"] or 0,
            }

        targets.append(
            {
                "os": target["os"],
                "arch": target["arch"],
                "runtime": target["runtime"],
                "min_os_version": target["min_os_version"] or "",
                "install": install_obj,
            }
        )

    return {
        "app_id": app_row["app_id"],
        "name": app_row["name"],
        "description": app_row["description"],
        "category": app_row["category"],
        "icon": app_row["icon"],
        "version": version_row["version"],
        "status": version_row["status"],
        "channel": version_row["channel"],
        "changelog": version_row["changelog"],
        "run": {
            "entrypoint": version_row["run_entrypoint"],
            "args": json.loads(version_row["run_args_json"]),
        },
        "scripts": {
            "install": version_row["install_script"],
            "uninstall": version_row["uninstall_script"],
            "start": version_row["start_script"],
            "stop": version_row["stop_script"],
            "healthcheck": version_row["healthcheck_script"],
        },
        "config_schema": json.loads(version_row["config_schema_json"]),
        "default_config": json.loads(version_row["default_config_json"]),
        "extra": json.loads(version_row["extra_json"]),
        "published_at": version_row["published_at"],
        "updated_at": version_row["updated_at"],
        "targets": targets,
    }
