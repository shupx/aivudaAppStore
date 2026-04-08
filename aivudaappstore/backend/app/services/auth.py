from __future__ import annotations

import hashlib
import secrets
from typing import Dict, Optional, Union

from fastapi import HTTPException

from aivudaappstore.backend.app.core.settings import SESSION_TTL_SECONDS
from aivudaappstore.backend.app.services.db import db_conn
from aivudaappstore.backend.app.services.utils import now_ts


def hash_password(password: str) -> str:
    # MVP: simple hash; production should use bcrypt/argon2.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def require_user(authorization: Optional[str]) -> Dict[str, Union[int, str]]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")

    now = now_ts()
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT u.id AS user_id, u.username, u.role, s.expires_at
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
    }


def login(username: str, password: str) -> Dict[str, object]:
    pwd_hash = hash_password(password)
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM developer_user WHERE username = ? AND password_hash = ?",
            (username, pwd_hash),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = secrets.token_urlsafe(32)
        created_at = now_ts()
        expires_at = created_at + SESSION_TTL_SECONDS
        conn.execute(
            "INSERT INTO dev_session (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], created_at, expires_at),
        )
        conn.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "user": {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
        },
    }
