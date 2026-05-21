from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
from typing import Any, Dict, Optional

from fastapi import HTTPException

from aivudaappstore.backend.app.core.settings import SESSION_TTL_SECONDS
from aivudaappstore.backend.app.services.db import db_conn, get_user_by_id, get_user_by_username, list_users, serialize_user
from aivudaappstore.backend.app.services.utils import now_ts

PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 240000
LEGACY_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")


def hash_password(password: str) -> str:
    salt = base64.b64encode(os.urandom(16)).decode("ascii")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    digest = base64.b64encode(derived).decode("ascii")
    return f"{PBKDF2_PREFIX}${PBKDF2_ITERATIONS}${salt}${digest}"


def hash_password_legacy(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    stored = str(password_hash or "")
    if stored.startswith(f"{PBKDF2_PREFIX}$"):
        try:
            _prefix, iterations_text, salt, digest = stored.split("$", 3)
            expected = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations_text),
            )
            actual = base64.b64decode(digest.encode("ascii"))
            return hmac.compare_digest(expected, actual)
        except Exception:
            return False
    if LEGACY_SHA256_RE.fullmatch(stored):
        return hmac.compare_digest(hash_password_legacy(password), stored)
    return False


def _validate_username(username: str) -> str:
    normalized = str(username or "").strip()
    if not USERNAME_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-64 chars and contain only letters, digits, underscore, dot, or hyphen",
        )
    return normalized


def _validate_password_strength(password: str) -> str:
    normalized = str(password or "")
    if len(normalized) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    return normalized


def require_user(authorization: Optional[str]) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")

    now = now_ts()
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT u.id AS user_id, u.username, u.role, u.created_at, u.updated_at, s.expires_at
            FROM dev_session s
            JOIN developer_user u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid token")
        if row["expires_at"] < now:
            conn.execute("DELETE FROM dev_session WHERE token = ?", (token,))
            conn.commit()
            raise HTTPException(status_code=401, detail="Token has expired")

    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _create_session(conn, *, user_id: int) -> Dict[str, Any]:
    row = get_user_by_id(conn, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    token = secrets.token_urlsafe(32)
    created_at = now_ts()
    expires_at = created_at + SESSION_TTL_SECONDS
    conn.execute(
        "INSERT INTO dev_session (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, created_at, expires_at),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "user": serialize_user(row),
    }


def register(username: str, password: str) -> Dict[str, Any]:
    username_value = _validate_username(username)
    password_value = _validate_password_strength(password)
    with db_conn() as conn:
        if get_user_by_username(conn, username_value):
            raise HTTPException(status_code=409, detail="Username already exists")
        ts = now_ts()
        cur = conn.execute(
            """
            INSERT INTO developer_user (username, password_hash, role, created_at, updated_at)
            VALUES (?, ?, 'developer', ?, ?)
            """,
            (username_value, hash_password(password_value), ts, ts),
        )
        payload = _create_session(conn, user_id=cur.lastrowid)
        conn.commit()
    return payload


def login(username: str, password: str) -> Dict[str, Any]:
    username_value = str(username or "").strip()
    password_value = str(password or "")
    with db_conn() as conn:
        row = get_user_by_username(conn, username_value)
        if not row or not verify_password(password_value, str(row["password_hash"] or "")):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not str(row["password_hash"]).startswith(f"{PBKDF2_PREFIX}$"):
            conn.execute(
                "UPDATE developer_user SET password_hash = ?, updated_at = ? WHERE id = ?",
                (hash_password(password_value), now_ts(), row["id"]),
            )

        payload = _create_session(conn, user_id=row["id"])
        conn.commit()
        return payload


def change_password(*, user: Dict[str, Any], current_password: str, new_password: str) -> Dict[str, Any]:
    new_password_value = _validate_password_strength(new_password)
    with db_conn() as conn:
        row = get_user_by_id(conn, int(user["user_id"]))
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(current_password or "", str(row["password_hash"] or "")):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        conn.execute(
            "UPDATE developer_user SET password_hash = ?, updated_at = ? WHERE id = ?",
            (hash_password(new_password_value), now_ts(), row["id"]),
        )
        conn.commit()
    return {"ok": True}


def reset_password(*, actor: Dict[str, Any], target_user_id: int, new_password: str) -> Dict[str, Any]:
    if actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can reset other users' passwords")
    new_password_value = _validate_password_strength(new_password)
    with db_conn() as conn:
        row = get_user_by_id(conn, int(target_user_id))
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute(
            "UPDATE developer_user SET password_hash = ?, updated_at = ? WHERE id = ?",
            (hash_password(new_password_value), now_ts(), target_user_id),
        )
        conn.execute("DELETE FROM dev_session WHERE user_id = ?", (target_user_id,))
        conn.commit()
    return {"ok": True}


def list_all_users(*, actor: Dict[str, Any]) -> Dict[str, Any]:
    with db_conn() as conn:
        return {"users": [serialize_user(row) for row in list_users(conn)]}
