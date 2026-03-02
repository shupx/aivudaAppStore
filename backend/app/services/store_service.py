from __future__ import annotations

from typing import Any
import zipfile
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.core.settings import APPSTORE_API_PREFIX, FILES_DIR, ROOT
from app.services.db import build_manifest, db_conn, get_targets, pick_largest_published_version
from app.services.utils import now_ts

SAMPLE_DIR = ROOT / "samples"
SAMPLE_APP_DIR = SAMPLE_DIR / "aivuda-app-pkg-example"
SAMPLE_PACKAGE_NAME = "aivuda-app-pkg-example.zip"
SAMPLE_PACKAGE = SAMPLE_DIR / SAMPLE_PACKAGE_NAME


def store_index() -> dict[str, Any]:
    with db_conn() as conn:
        apps = conn.execute("SELECT id, app_id, name, description FROM app ORDER BY app_id").fetchall()

        items = []
        for app_row in apps:
            version_row = pick_largest_published_version(conn, app_row["id"])
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


def store_sample_package() -> FileResponse:
    if not SAMPLE_APP_DIR.exists():
        raise HTTPException(status_code=404, detail="Sample package directory not found")

    # @TODO: 可以预先生成好示例包，避免每次请求都生成一次
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SAMPLE_PACKAGE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in SAMPLE_APP_DIR.rglob("*"):
            if path.is_dir():
                continue
            rel_path = path.relative_to(SAMPLE_APP_DIR)
            rel_text = rel_path.as_posix()
            if rel_text == ".git" or rel_text.startswith(".git/"):
                continue
            zf.write(path, rel_path)

    return FileResponse(SAMPLE_PACKAGE, media_type="application/zip", filename=SAMPLE_PACKAGE_NAME)


def store_app_detail(app_id: str) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute("SELECT * FROM app WHERE app_id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="App not found")

        all_versions = conn.execute(
            """
            SELECT * FROM app_version
            WHERE app_id = ?
            ORDER BY created_at DESC
            """,
            (app_row["id"],),
        ).fetchall()

        # Structured versions array (all versions including unpublished)
        versions = []
        for v_row in all_versions:
            targets = get_targets(conn, version_id=v_row["id"])
            artifact_size = targets[0]["artifact_size"] if targets else 0
            artifact_url = f"{APPSTORE_API_PREFIX}/files/{targets[0]['artifact_relpath']}" if targets and targets[0]["artifact_relpath"] else ""
            versions.append({
                "version": v_row["version"],
                "description": v_row["description"],
                "status": v_row["status"],
                "published_at": v_row["published_at"],
                "created_at": v_row["created_at"],
                "updated_at": v_row["updated_at"],
                "artifact_size": artifact_size,
                "artifact_url": artifact_url,
            })

        # Published items with manifests (backward compat)
        items = []
        for v_row in all_versions:
            if v_row["status"] != "published":
                continue
            targets = get_targets(conn, version_id=v_row["id"])
            items.append({
                "version": v_row["version"],
                "manifest": build_manifest(app_row=app_row, version_row=v_row, target_rows=targets),
                "updated_at": v_row["updated_at"],
            })

    return {
        "app_id": app_id,
        "app": {
            "name": app_row["name"],
            "description": app_row["description"],
            "owner_user_id": app_row["owner_user_id"],
            "created_at": app_row["created_at"],
            "updated_at": app_row["updated_at"],
        },
        "versions": versions,
        "items": items,
    }


def store_manifest(app_id: str, version: str) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute(
            "SELECT id, app_id, name, description FROM app WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="App not found")

        version_row = conn.execute(
            "SELECT * FROM app_version WHERE app_id = ? AND version = ?",
            (app_row["id"], version),
        ).fetchone()
        if not version_row or version_row["status"] != "published":
            raise HTTPException(status_code=404, detail="Version not found or not published")

        targets = get_targets(conn, version_id=version_row["id"])

    return build_manifest(app_row=app_row, version_row=version_row, target_rows=targets)


def store_download_url(app_id: str, version: str) -> dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute("SELECT id FROM app WHERE app_id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="App not found")

        version_row = conn.execute(
            "SELECT id, status FROM app_version WHERE app_id = ? AND version = ?",
            (app_row["id"], version),
        ).fetchone()
        if not version_row or version_row["status"] != "published":
            raise HTTPException(status_code=404, detail="Version not found or not published")

        target = conn.execute(
            "SELECT * FROM app_target WHERE version_id = ?",
            (version_row["id"],),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="No downloadable package for this version")

    return {
        "url": f"{APPSTORE_API_PREFIX}/store/apps/{app_id}/versions/{version}/download",
        "sha256": target["artifact_sha256"] or "",
        "size": target["artifact_size"] or 0,
    }


def store_download_file(app_id: str, version: str) -> FileResponse:
    with db_conn() as conn:
        app_row = conn.execute("SELECT id FROM app WHERE app_id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="App not found")

        version_row = conn.execute(
            "SELECT id, status FROM app_version WHERE app_id = ? AND version = ?",
            (app_row["id"], version),
        ).fetchone()
        if not version_row or version_row["status"] != "published":
            raise HTTPException(status_code=404, detail="Version not found or not published")

        target = conn.execute(
            "SELECT * FROM app_target WHERE version_id = ?",
            (version_row["id"],),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="No downloadable package for this version")

    relpath = Path(str(target["artifact_relpath"]))
    package_path = (FILES_DIR / relpath).resolve()
    files_root = FILES_DIR.resolve()
    try:
        package_path.relative_to(files_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package path")
    if not package_path.exists() or not package_path.is_file():
        raise HTTPException(status_code=404, detail="Package file not found")

    download_name = f"{app_id}-{version}.zip"
    return FileResponse(package_path, media_type="application/zip", filename=download_name)
