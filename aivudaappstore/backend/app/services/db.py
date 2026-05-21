from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

import semver as _semver
from fastapi import HTTPException

from aivudaappstore.backend.app.core.settings import APPSTORE_API_PREFIX, DB_PATH
from aivudaappstore.backend.app.services.utils import now_ts

APP_ROLE_ADMIN = "admin"
APP_ROLE_DEVELOPER = "developer"
APP_WRITE_ROLES = {APP_ROLE_ADMIN, APP_ROLE_DEVELOPER}
APP_MANAGE_MEMBER_ROLES = {APP_ROLE_ADMIN}


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
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
            CREATE TABLE IF NOT EXISTS app_member (
                app_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (app_id, user_id),
                FOREIGN KEY(app_id) REFERENCES app(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES developer_user(id) ON DELETE CASCADE
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

        version_cols = {row[1] for row in conn.execute("PRAGMA table_info(app_version)").fetchall()}
        if "description" not in version_cols:
            conn.execute("ALTER TABLE app_version ADD COLUMN description TEXT NOT NULL DEFAULT ''")

        member_cols = {row[1] for row in conn.execute("PRAGMA table_info(app_member)").fetchall()}
        if member_cols and "role" in member_cols:
            conn.execute(
                """
                UPDATE app_member
                SET role = CASE
                    WHEN role NOT IN ('admin', 'developer') THEN 'developer'
                    ELSE role
                END
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

        _backfill_app_members(conn)
        conn.commit()


def _backfill_app_members(conn: sqlite3.Connection) -> None:
    apps = conn.execute(
        "SELECT id, owner_user_id, created_at, updated_at FROM app ORDER BY id"
    ).fetchall()
    for app_row in apps:
        ts_created = app_row["created_at"] or now_ts()
        ts_updated = app_row["updated_at"] or ts_created
        existing_rows = conn.execute(
            "SELECT user_id, role FROM app_member WHERE app_id = ?",
            (app_row["id"],),
        ).fetchall()
        existing = {row["user_id"]: row["role"] for row in existing_rows}
        owner_user_id = app_row["owner_user_id"]

        if owner_user_id not in existing:
            conn.execute(
                """
                INSERT INTO app_member (app_id, user_id, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (app_row["id"], owner_user_id, APP_ROLE_ADMIN, ts_created, ts_updated),
            )
        else:
            conn.execute(
                """
                UPDATE app_member
                SET role = ?, updated_at = ?
                WHERE app_id = ? AND user_id = ?
                """,
                (APP_ROLE_ADMIN, ts_updated, app_row["id"], owner_user_id),
            )

        conn.execute(
            """
            DELETE FROM app_member
            WHERE app_id = ? AND role = ? AND user_id != ?
            """,
            (app_row["id"], APP_ROLE_ADMIN, owner_user_id),
        )


def create_audit_log(
    conn: sqlite3.Connection,
    *,
    app_id: int,
    actor_user_id: int,
    action: str,
    version_id: Optional[int] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO app_audit_log (app_id, version_id, actor_user_id, action, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (app_id, version_id, actor_user_id, action, json.dumps(detail or {}), now_ts()),
    )


def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT id, username, role, password_hash, created_at, updated_at FROM developer_user WHERE username = ?",
        (username,),
    ).fetchone()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT id, username, role, password_hash, created_at, updated_at FROM developer_user WHERE id = ?",
        (user_id,),
    ).fetchone()


def list_users(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT id, username, role, created_at, updated_at FROM developer_user ORDER BY username"
    ).fetchall()


def get_app_row(conn: sqlite3.Connection, *, app_id_text: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, app_id, owner_user_id, name, description, created_at, updated_at FROM app WHERE app_id = ?",
        (app_id_text,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="App not found")
    return row


def get_app_member_role(conn: sqlite3.Connection, *, app_pk: int, user_id: int) -> Optional[str]:
    row = conn.execute(
        "SELECT role FROM app_member WHERE app_id = ? AND user_id = ?",
        (app_pk, user_id),
    ).fetchone()
    return str(row["role"]) if row else None


def compute_app_permissions(*, user: Optional[Dict[str, Any]], app_member_role: Optional[str]) -> Dict[str, bool]:
    is_global_admin = bool(user and user.get("role") == "admin")
    is_app_admin = is_global_admin or app_member_role == APP_ROLE_ADMIN
    can_edit_versions = is_global_admin or app_member_role in APP_WRITE_ROLES
    return {
        "is_global_admin": is_global_admin,
        "is_app_admin": is_app_admin,
        "app_role": app_member_role or "",
        "can_edit_versions": can_edit_versions,
        "can_manage_members": is_app_admin,
        "can_delete_app": is_app_admin,
        "can_upload_new_version": can_edit_versions,
        "can_change_admin": is_app_admin,
    }


def require_app_role(
    conn: sqlite3.Connection,
    *,
    app_id_text: str,
    user: Dict[str, Any],
    allowed_roles: Sequence[str],
) -> sqlite3.Row:
    app_row = get_app_row(conn, app_id_text=app_id_text)
    if user["role"] == "admin":
        return app_row
    member_role = get_app_member_role(conn, app_pk=app_row["id"], user_id=int(user["user_id"]))
    if member_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Permission denied for this app")
    return app_row


def get_app_members(conn: sqlite3.Connection, *, app_pk: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT m.app_id, m.user_id, m.role, m.created_at, m.updated_at, u.username, u.role AS global_role
        FROM app_member m
        JOIN developer_user u ON u.id = m.user_id
        WHERE m.app_id = ?
        ORDER BY CASE m.role WHEN 'admin' THEN 0 ELSE 1 END, u.username
        """,
        (app_pk,),
    ).fetchall()


def ensure_app_admin_member(conn: sqlite3.Connection, *, app_pk: int, user_id: int, ts: Optional[int] = None) -> None:
    ts_value = ts or now_ts()
    conn.execute(
        """
        INSERT INTO app_member (app_id, user_id, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(app_id, user_id) DO UPDATE SET
            role = excluded.role,
            updated_at = excluded.updated_at
        """,
        (app_pk, user_id, APP_ROLE_ADMIN, ts_value, ts_value),
    )
    conn.execute(
        """
        DELETE FROM app_member
        WHERE app_id = ? AND role = ? AND user_id != ?
        """,
        (app_pk, APP_ROLE_ADMIN, user_id),
    )
    conn.execute(
        "UPDATE app SET owner_user_id = ?, updated_at = ? WHERE id = ?",
        (user_id, ts_value, app_pk),
    )


def upsert_app_member(
    conn: sqlite3.Connection,
    *,
    app_pk: int,
    user_id: int,
    role: str,
    ts: Optional[int] = None,
) -> None:
    ts_value = ts or now_ts()
    conn.execute(
        """
        INSERT INTO app_member (app_id, user_id, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(app_id, user_id) DO UPDATE SET
            role = excluded.role,
            updated_at = excluded.updated_at
        """,
        (app_pk, user_id, role, ts_value, ts_value),
    )


def delete_app_member(conn: sqlite3.Connection, *, app_pk: int, user_id: int) -> None:
    conn.execute(
        "DELETE FROM app_member WHERE app_id = ? AND user_id = ?",
        (app_pk, user_id),
    )


def get_version_owned(conn: sqlite3.Connection, *, app_row: sqlite3.Row, version: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM app_version WHERE app_id = ? AND version = ?",
        (app_row["id"], version),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")
    return row


def serialize_member(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "app_role": row["role"],
        "global_role": row["global_role"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_user(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _semver_sort_key(version_str: str) -> Tuple[int, Any]:
    try:
        ver = _semver.Version.parse(version_str.strip())
        return (1, ver)
    except ValueError:
        return (0, version_str.lower())


def pick_largest_published_version(conn: sqlite3.Connection, app_pk: int) -> Optional[sqlite3.Row]:
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


def pick_latest_published_version(conn: sqlite3.Connection, app_pk: int) -> Optional[sqlite3.Row]:
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
) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM app_target WHERE version_id = ?", (version_id,)).fetchall()


def build_manifest(
    *,
    app_row: sqlite3.Row,
    version_row: sqlite3.Row,
    target_rows: List[sqlite3.Row],
) -> Dict[str, Any]:
    install_obj = {"url": "", "sha256": "", "size": 0}
    if target_rows:
        target = target_rows[0]
        app_id_text = str(app_row["app_id"])
        version_text = str(version_row["version"])
        install_obj = {
            "url": f"{APPSTORE_API_PREFIX}/store/apps/{app_id_text}/versions/{version_text}/download",
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
