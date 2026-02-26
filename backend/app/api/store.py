from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.db import build_manifest, db_conn, get_targets, pick_latest_published_version
from app.services.utils import now_ts

router = APIRouter(prefix="/store", tags=["store"])


@router.get("/index")
async def store_index() -> dict[str, Any]:
    with db_conn() as conn:
        apps = conn.execute("SELECT id, app_id, name, description FROM app ORDER BY app_id").fetchall()

        items = []
        for app_row in apps:
            version_row = pick_latest_published_version(conn, app_row["id"])
            if not version_row:
                continue

            targets = get_targets(conn, version_id=version_row["id"])

            manifest = build_manifest(app_row=app_row, version_row=version_row, target_rows=targets)
            items.append(
                {
                    "app_id": app_row["app_id"],
                    "version": version_row["version"],
                    "manifest": manifest,
                    "updated_at": version_row["updated_at"],
                }
            )

    return {"generated_at": now_ts(), "items": items}


@router.get("/apps/{app_id}")
async def store_app_detail(app_id: str) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute(
            "SELECT id, app_id, name, description FROM app WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="app 不存在")

        versions = conn.execute(
            """
            SELECT * FROM app_version
            WHERE app_id = ? AND status = 'published'
            ORDER BY published_at DESC, created_at DESC
            """,
            (app_row["id"],),
        ).fetchall()

        items = []
        for version_row in versions:
            targets = get_targets(conn, version_id=version_row["id"])

            items.append(
                {
                    "version": version_row["version"],
                    "manifest": build_manifest(app_row=app_row, version_row=version_row, target_rows=targets),
                    "updated_at": version_row["updated_at"],
                }
            )

    return {"app_id": app_id, "items": items}


@router.get("/apps/{app_id}/versions/{version}/manifest")
async def store_manifest(
    app_id: str,
    version: str,
) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute(
            "SELECT id, app_id, name, description FROM app WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="app 不存在")

        version_row = conn.execute(
            "SELECT * FROM app_version WHERE app_id = ? AND version = ?",
            (app_row["id"], version),
        ).fetchone()
        if not version_row or version_row["status"] != "published":
            raise HTTPException(status_code=404, detail="版本不存在或未发布")

        targets = get_targets(conn, version_id=version_row["id"])

    return build_manifest(app_row=app_row, version_row=version_row, target_rows=targets)


@router.get("/apps/{app_id}/versions/{version}/download-url")
async def store_download_url(app_id: str, version: str) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute("SELECT id FROM app WHERE app_id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="app 不存在")

        version_row = conn.execute(
            "SELECT id, status FROM app_version WHERE app_id = ? AND version = ?",
            (app_row["id"], version),
        ).fetchone()
        if not version_row or version_row["status"] != "published":
            raise HTTPException(status_code=404, detail="版本不存在或未发布")

        target = conn.execute(
            "SELECT * FROM app_target WHERE version_id = ?",
            (version_row["id"],),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="该版本没有可用安装包")

    return {
        "url": f"/files/{target['artifact_relpath']}",
        "sha256": target["artifact_sha256"] or "",
        "size": target["artifact_size"] or 0,
    }
