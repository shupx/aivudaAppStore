from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.core.settings import FILES_DIR
from app.services.auth import login, require_user
from app.services.db import create_audit_log, db_conn, get_app_owned, get_version_owned
from app.services.utils import file_sha256, normalize_platform, now_ts, parse_json_field, validate_runtime

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/auth/login")
async def dev_login(username: str = Form(...), password: str = Form(...)) -> dict[str, object]:
    return login(username, password)


@router.get("/me")
async def dev_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = require_user(authorization)
    return {"user": user}


@router.post("/apps")
async def dev_create_app(
    app_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    icon: str = Form("box"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    app_id_text = app_id.strip()
    if not app_id_text:
        raise HTTPException(status_code=400, detail="app_id 不能为空")

    ts = now_ts()
    with db_conn() as conn:
        existing = conn.execute("SELECT id FROM app WHERE app_id = ?", (app_id_text,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="app_id 已存在")

        cur = conn.execute(
            """
            INSERT INTO app (app_id, owner_user_id, name, description, category, icon, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (app_id_text, user["user_id"], name.strip(), description, category, icon, ts, ts),
        )
        create_audit_log(
            conn,
            app_id=cur.lastrowid,
            actor_user_id=user["user_id"],
            action="create_app",
            detail={"app_id": app_id_text},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id_text}


@router.get("/apps")
async def dev_list_apps(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = require_user(authorization)

    with db_conn() as conn:
        if user["role"] == "admin":
            rows = conn.execute(
                """
                SELECT app_id, name, description, category, icon, created_at, updated_at
                FROM app
                ORDER BY updated_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT app_id, name, description, category, icon, created_at, updated_at
                FROM app
                WHERE owner_user_id = ?
                ORDER BY updated_at DESC
                """,
                (user["user_id"],),
            ).fetchall()

    return {"items": [dict(x) for x in rows]}


@router.get("/apps/{app_id}")
async def dev_get_app(app_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = require_user(authorization)
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        versions = conn.execute(
            """
            SELECT id, version, status, channel, published_at, updated_at
            FROM app_version
            WHERE app_id = ?
            ORDER BY created_at DESC
            """,
            (app_row["id"],),
        ).fetchall()

    app_info = dict(app_row)
    app_info.pop("owner_user_id", None)
    return {"app": app_info, "versions": [dict(v) for v in versions]}


@router.post("/apps/{app_id}/versions")
async def dev_create_version(
    app_id: str,
    version: str = Form(...),
    channel: str = Form("stable"),
    changelog: str = Form(""),
    run_entrypoint: str = Form("./run.sh"),
    run_args_json: str = Form("[]"),
    install_script: str = Form(""),
    uninstall_script: str = Form(""),
    start_script: str = Form(""),
    stop_script: str = Form(""),
    healthcheck_script: str = Form(""),
    config_schema_json: str = Form('{"type":"object","properties":{}}'),
    default_config_json: str = Form("{}"),
    extra_json: str = Form("{}"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    run_args = parse_json_field(run_args_json, field_name="run_args_json", default=[])
    if not isinstance(run_args, list):
        raise HTTPException(status_code=400, detail="run_args_json 必须是数组")

    config_schema = parse_json_field(config_schema_json, field_name="config_schema_json", default={})
    default_config = parse_json_field(default_config_json, field_name="default_config_json", default={})
    extra = parse_json_field(extra_json, field_name="extra_json", default={})

    version_text = version.strip()
    if not version_text:
        raise HTTPException(status_code=400, detail="version 不能为空")

    ts = now_ts()
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)

        try:
            cur = conn.execute(
                """
                INSERT INTO app_version (
                    app_id, version, status, channel, changelog, run_entrypoint, run_args_json,
                    install_script, uninstall_script, start_script, stop_script, healthcheck_script,
                    config_schema_json, default_config_json, extra_json, created_at, updated_at
                ) VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    app_row["id"],
                    version_text,
                    channel,
                    changelog,
                    run_entrypoint,
                    json.dumps([str(x) for x in run_args]),
                    install_script,
                    uninstall_script,
                    start_script,
                    stop_script,
                    healthcheck_script,
                    json.dumps(config_schema),
                    json.dumps(default_config),
                    json.dumps(extra),
                    ts,
                    ts,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="版本已存在") from exc

        conn.execute("UPDATE app SET updated_at = ? WHERE id = ?", (ts, app_row["id"]))
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=cur.lastrowid,
            actor_user_id=user["user_id"],
            action="create_version",
            detail={"version": version_text},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id, "version": version_text, "status": "draft"}


@router.post("/apps/{app_id}/versions/{version}/targets")
async def dev_upsert_target(
    app_id: str,
    version: str,
    os: str = Form(...),
    arch: str = Form(...),
    runtime: str = Form(...),
    image_ref: str = Form(""),
    image_digest: str = Form(""),
    min_os_version: str = Form(""),
    file: UploadFile | None = File(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    normalized_os, normalized_arch = normalize_platform(os, arch)
    runtime_text = validate_runtime(runtime)

    artifact_relpath: str | None = None
    artifact_sha: str | None = None
    artifact_size: int | None = None

    if runtime_text == "host":
        if file is None:
            raise HTTPException(status_code=400, detail="host 运行时必须上传 artifact")
    else:
        if not image_ref.strip() or not image_digest.strip():
            raise HTTPException(status_code=400, detail="容器运行时必须提供 image_ref 与 image_digest")

    ts = now_ts()
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)
        if version_row["status"] not in {"draft", "unpublished"}:
            raise HTTPException(status_code=400, detail="仅 draft/unpublished 版本允许更新平台构建")

        if file is not None:
            save_dir = FILES_DIR / "apps" / app_id / version / normalized_os / normalized_arch
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = file.filename or "artifact.bin"
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

        conn.execute(
            """
            INSERT INTO app_target (
                version_id, os, arch, runtime, image_ref, image_digest, artifact_relpath,
                artifact_sha256, artifact_size, min_os_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(version_id, os, arch) DO UPDATE SET
                runtime = excluded.runtime,
                image_ref = excluded.image_ref,
                image_digest = excluded.image_digest,
                artifact_relpath = excluded.artifact_relpath,
                artifact_sha256 = excluded.artifact_sha256,
                artifact_size = excluded.artifact_size,
                min_os_version = excluded.min_os_version,
                updated_at = excluded.updated_at
            """,
            (
                version_row["id"],
                normalized_os,
                normalized_arch,
                runtime_text,
                image_ref.strip() or None,
                image_digest.strip() or None,
                artifact_relpath,
                artifact_sha,
                artifact_size,
                min_os_version.strip() or None,
                ts,
                ts,
            ),
        )
        conn.execute("UPDATE app_version SET updated_at = ? WHERE id = ?", (ts, version_row["id"]))
        conn.execute("UPDATE app SET updated_at = ? WHERE id = ?", (ts, app_row["id"]))
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=version_row["id"],
            actor_user_id=user["user_id"],
            action="upsert_target",
            detail={"os": normalized_os, "arch": normalized_arch, "runtime": runtime_text},
        )
        conn.commit()

    return {
        "ok": True,
        "app_id": app_id,
        "version": version,
        "target": {"os": normalized_os, "arch": normalized_arch, "runtime": runtime_text},
    }


@router.post("/apps/{app_id}/versions/{version}/publish")
async def dev_publish_version(
    app_id: str,
    version: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    ts = now_ts()

    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)

        target_cnt = conn.execute(
            "SELECT COUNT(1) AS cnt FROM app_target WHERE version_id = ?",
            (version_row["id"],),
        ).fetchone()["cnt"]
        if target_cnt <= 0:
            raise HTTPException(status_code=400, detail="至少上传一个平台构建后才能发布")

        conn.execute(
            "UPDATE app_version SET status = 'published', published_at = ?, updated_at = ? WHERE id = ?",
            (ts, ts, version_row["id"]),
        )
        conn.execute("UPDATE app SET updated_at = ? WHERE id = ?", (ts, app_row["id"]))
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=version_row["id"],
            actor_user_id=user["user_id"],
            action="publish_version",
            detail={"version": version},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id, "version": version, "status": "published"}


@router.post("/apps/{app_id}/versions/{version}/unpublish")
async def dev_unpublish_version(
    app_id: str,
    version: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    ts = now_ts()

    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)

        conn.execute("UPDATE app_version SET status = 'unpublished', updated_at = ? WHERE id = ?", (ts, version_row["id"]))
        conn.execute("UPDATE app SET updated_at = ? WHERE id = ?", (ts, app_row["id"]))
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=version_row["id"],
            actor_user_id=user["user_id"],
            action="unpublish_version",
            detail={"version": version},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id, "version": version, "status": "unpublished"}


@router.delete("/apps/{app_id}/versions/{version}")
async def dev_delete_version(
    app_id: str,
    version: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)

    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)

        if version_row["status"] == "published":
            raise HTTPException(status_code=400, detail="已发布版本请先下架再删除")

        targets = conn.execute(
            "SELECT artifact_relpath FROM app_target WHERE version_id = ?",
            (version_row["id"],),
        ).fetchall()
        conn.execute("DELETE FROM app_version WHERE id = ?", (version_row["id"],))
        conn.execute("UPDATE app SET updated_at = ? WHERE id = ?", (now_ts(), app_row["id"]))
        create_audit_log(
            conn,
            app_id=app_row["id"],
            actor_user_id=user["user_id"],
            action="delete_version",
            detail={"version": version},
        )
        conn.commit()

    for target in targets:
        file_rel = target["artifact_relpath"]
        if not file_rel:
            continue
        p = FILES_DIR / file_rel
        if p.exists():
            p.unlink()

    return {"ok": True, "app_id": app_id, "version": version}


@router.get("/apps/{app_id}/audit-logs")
async def dev_get_audit_logs(
    app_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id, user=user)
        rows = conn.execute(
            """
            SELECT l.id, l.action, l.detail_json, l.created_at, l.version_id, u.username AS actor
            FROM app_audit_log l
            JOIN developer_user u ON u.id = l.actor_user_id
            WHERE l.app_id = ?
            ORDER BY l.created_at DESC, l.id DESC
            """,
            (app_row["id"],),
        ).fetchall()

    return {
        "items": [
            {
                "id": row["id"],
                "action": row["action"],
                "detail": json.loads(row["detail_json"]),
                "created_at": row["created_at"],
                "version_id": row["version_id"],
                "actor": row["actor"],
            }
            for row in rows
        ]
    }
