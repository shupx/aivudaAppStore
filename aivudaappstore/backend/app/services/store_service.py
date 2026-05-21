from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote
import tarfile

from fastapi import HTTPException
from fastapi.responses import FileResponse
from starlette.responses import RedirectResponse

from aivudaappstore.backend.app.core.settings import (
    APPSTORE_API_PREFIX,
    FILES_DIR,
    SAMPLES_DIR,
    SAMPLES_SOURCE_DIR,
    ensure_storage_dirs,
)
from aivudaappstore.backend.app.services.db import (
    build_manifest,
    compute_app_permissions,
    db_conn,
    get_app_member_role,
    get_app_members,
    get_targets,
    pick_largest_published_version,
    serialize_member,
)
from aivudaappstore.backend.app.services.utils import now_ts

SAMPLE_DIR = SAMPLES_DIR
SAMPLE_APP_DIR = SAMPLE_DIR / "aivuda-app-pkg-example"
SAMPLE_SOURCE_APP_DIR = SAMPLES_SOURCE_DIR / "aivuda-app-pkg-example"
SAMPLE_PACKAGE_NAME = "aivuda-app-pkg-example.tar.gz"
SAMPLE_PACKAGE = SAMPLE_DIR / SAMPLE_PACKAGE_NAME
_CADDY_LOCAL_CA_ROOT_PATH = Path.home() / ".local/share/caddy/pki/authorities/local/root.crt"


def _artifact_download_filename(app_id: str, version: str, artifact_relpath: str) -> str:
    rel_name = Path(str(artifact_relpath or "")).name
    suffixes = Path(rel_name).suffixes
    suffix = "".join(suffixes) if suffixes else ".zip"
    return f"{app_id}-{version}{suffix}"


def store_index() -> Dict[str, Any]:
    with db_conn() as conn:
        apps = conn.execute(
            """
            SELECT a.id, a.app_id, a.name, a.description, a.owner_user_id, u.username AS owner_username
            FROM app a
            JOIN developer_user u ON u.id = a.owner_user_id
            ORDER BY a.app_id
            """
        ).fetchall()

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
                    "owner_user_id": app_row["owner_user_id"],
                    "owner_username": app_row["owner_username"],
                    "created_at": version_row["created_at"],
                    "published_at": version_row["published_at"],
                    "updated_at": version_row["updated_at"],
                }
            )

    return {"generated_at": now_ts(), "items": items}


def store_sample_package() -> FileResponse:
    if not SAMPLE_SOURCE_APP_DIR.exists():
        raise HTTPException(status_code=404, detail="Sample package directory not found")

    ensure_storage_dirs()
    with tarfile.open(SAMPLE_PACKAGE, "w:gz") as tf:
        for path in sorted(SAMPLE_SOURCE_APP_DIR.rglob("*")):
            if path.is_dir():
                continue
            rel_path = path.relative_to(SAMPLE_SOURCE_APP_DIR)
            rel_text = rel_path.as_posix()
            if rel_text == ".git" or rel_text.startswith(".git/"):
                continue
            tf.add(path, arcname=rel_text, recursive=False)

    return FileResponse(SAMPLE_PACKAGE, media_type="application/gzip", filename=SAMPLE_PACKAGE_NAME)


def store_caddy_local_ca_root() -> FileResponse:
    cert_path = _CADDY_LOCAL_CA_ROOT_PATH
    if not cert_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Caddy local CA root certificate not found or not accessible: ~/.local/share/caddy/pki/authorities/local/root.crt",
        )

    return FileResponse(
        str(cert_path),
        media_type="application/x-x509-ca-cert",
        filename=_build_caddy_local_ca_filename(),
    )


def store_app_detail(app_id: str, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with db_conn() as conn:
        app_row = conn.execute("SELECT * FROM app WHERE app_id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="App not found")
        member_role = None
        if current_user:
            member_role = get_app_member_role(conn, app_pk=app_row["id"], user_id=int(current_user["user_id"]))
        permissions = compute_app_permissions(user=current_user, app_member_role=member_role)
        members = [serialize_member(row) for row in get_app_members(conn, app_pk=app_row["id"])]

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
            artifact_url = (
                f"{APPSTORE_API_PREFIX}/store/apps/{app_id}/versions/{v_row['version']}/download"
                if targets and targets[0]["artifact_relpath"]
                else ""
            )
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
        "permissions": permissions,
        "members": members,
        "versions": versions,
        "items": items,
    }


def store_manifest(app_id: str, version: str) -> Dict[str, Any]:
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


def store_download_url(app_id: str, version: str) -> Dict[str, Any]:
    target = _get_download_target(app_id, version)
    static_url = _build_caddy_file_url(str(target["artifact_relpath"] or ""))

    return {
        "url": static_url,
        "sha256": target["artifact_sha256"] or "",
        "size": target["artifact_size"] or 0,
        "filename": _artifact_download_filename(app_id, version, str(target["artifact_relpath"] or "")),
    }


def store_download_file(app_id: str, version: str) -> RedirectResponse:
    target = _get_download_target(app_id, version)
    static_url = _build_caddy_file_url(str(target["artifact_relpath"] or ""))
    return RedirectResponse(url=static_url, status_code=307)
    # Here, we use caddy to handle static file （避免后端FileResponse在高并发、大文件情况下对后端程序压力比较大）
    #TODO: 大规模文件托管应该用对象存储服务OBS，minIO之类的分布式存储文件服务


def _get_download_target(app_id: str, version: str) -> Any:
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

    relpath = Path(str(target["artifact_relpath"] or ""))
    if relpath.is_absolute() or any(part == ".." for part in relpath.parts):
        raise HTTPException(status_code=400, detail="Invalid package path")

    package_path = (FILES_DIR / relpath).resolve()
    files_root = FILES_DIR.resolve()
    try:
        package_path.relative_to(files_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid package path") from exc

    if not package_path.exists() or not package_path.is_file():
        raise HTTPException(status_code=404, detail="Package file not found")

    return target


def _build_caddy_file_url(artifact_relpath: str) -> str:
    relpath = Path(str(artifact_relpath or ""))
    encoded = quote(relpath.as_posix().lstrip("/"), safe="/")
    if not encoded:
        raise HTTPException(status_code=400, detail="Invalid package path")
    return f"{APPSTORE_API_PREFIX}/files/{encoded}"


def store_download_response_meta(app_id: str, version: str) -> Dict[str, str]:
    target = _get_download_target(app_id, version)
    artifact_relpath = str(target["artifact_relpath"] or "")
    filename = _artifact_download_filename(app_id, version, artifact_relpath)
    media_type, _ = mimetypes.guess_type(filename)
    return {
        "filename": filename,
        "media_type": media_type or "application/octet-stream",
    }


def _build_caddy_local_ca_filename() -> str:
    parts = []

    for env_name in ("APPSTORE_PUBLIC_HTTPS_HOST", "APPSTORE_PRIVATE_HTTPS_HOST"):
        raw_value = str(os.environ.get(env_name, "") or "").strip().lower()
        if not raw_value:
            continue
        normalized = raw_value.replace(".", "_")
        safe_value = "".join(ch for ch in normalized if ch.isalnum() or ch in {"-", "_"}).strip("-_")
        if safe_value:
            parts.append(safe_value)

    if not parts:
        parts.append("local")

    return f"aivudaappstore-{'-'.join(parts)}-caddy-local-root.crt"
