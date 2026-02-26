from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.core.settings import FILES_DIR
from app.services.auth import login, require_user
from app.services.db import create_audit_log, db_conn
from app.services.utils import file_sha256, now_ts

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/auth/login")
async def dev_login(username: str = Form(...), password: str = Form(...)) -> dict[str, object]:
    return login(username, password)


@router.get("/me")
async def dev_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = require_user(authorization)
    return {"user": user}




@router.post("/apps/upload-simple")
async def dev_upload_simple(
    name: str = Form(...),
    file: UploadFile = File(...),
    version: str = Form("0.1.0"),
    description: str = Form(""),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)

    name_text = name.strip()
    if not name_text:
        raise HTTPException(status_code=400, detail="name 不能为空")

    version_text = version.strip() or "0.1.0"
    ts = now_ts()

    with db_conn() as conn:
        app_id_text = f"app_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"
        while conn.execute("SELECT 1 FROM app WHERE app_id = ?", (app_id_text,)).fetchone():
            app_id_text = f"app_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"

        cur = conn.execute(
            """
            INSERT INTO app (app_id, owner_user_id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (app_id_text, user["user_id"], name_text, description, ts, ts),
        )
        app_pk = cur.lastrowid
        create_audit_log(
            conn,
            app_id=app_pk,
            actor_user_id=user["user_id"],
            action="upload_simple_create_app",
            detail={"app_id": app_id_text},
        )

        filename = file.filename or "artifact.bin"
        save_dir = FILES_DIR / "apps" / app_id_text / version_text
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / filename
        with save_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

        artifact_relpath = str(save_path.relative_to(FILES_DIR))
        artifact_sha = file_sha256(save_path)
        artifact_size = save_path.stat().st_size

        cur = conn.execute(
            """
            INSERT INTO app_version (
                app_id, version, status, published_at, created_at, updated_at
            ) VALUES (?, ?, 'published', ?, ?, ?)
            """,
            (
                app_pk,
                version_text,
                ts,
                ts,
                ts,
            ),
        )
        version_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO app_target (
                version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                artifact_relpath,
                artifact_sha,
                artifact_size,
                ts,
                ts,
            ),
        )
        create_audit_log(
            conn,
            app_id=app_pk,
            actor_user_id=user["user_id"],
            action="upload_simple_publish",
            detail={"version": version_text},
        )
        conn.commit()

    return {
        "ok": True,
        "app_id": app_id_text,
        "version": version_text,
        "status": "published",
        "download_url": f"/files/{artifact_relpath}",
    }
