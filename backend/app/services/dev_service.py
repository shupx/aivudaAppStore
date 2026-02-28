from __future__ import annotations

import re
import secrets
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from app.core.settings import FILES_DIR
from app.services.db import create_audit_log, db_conn, get_app_owned, get_version_owned
from app.services.utils import file_sha256, now_ts


def _yaml_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _app_name_tag(name: str) -> str:
    tag = re.sub(r"\s+", "-", name.strip())
    tag = re.sub(r"[^\w-]+", "-", tag, flags=re.UNICODE)
    tag = re.sub(r"-{2,}", "-", tag).strip("-_")
    if not tag:
        return "app"
    return tag[:32]


def _normalize_zip_name(name: str) -> str:
    name = name.replace("\\", "/")
    name = name.lstrip("/")
    while name.startswith("./"):
        name = name[2:]
    return name


def _safe_extract_zip(zip_path: Path, dest_dir: Path, prefix: str = "") -> None:
    dest_real = dest_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            norm_name = _normalize_zip_name(member.filename)
            if prefix:
                if not norm_name.startswith(prefix):
                    continue
                norm_name = norm_name[len(prefix) :]
            if not norm_name:
                continue
            if norm_name == "app.yaml":
                continue
            member_path = (dest_dir / norm_name).resolve()
            if not str(member_path).startswith(str(dest_real)):
                raise HTTPException(status_code=400, detail="package.zip 路径非法")
            member_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, member_path.open("wb") as dst:
                dst.write(src.read())


def _detect_package_prefix(names: set[str]) -> str | None:
    required = {
        "scripts/install.sh",
        "scripts/uninstall.sh",
        "scripts/start.sh",
        "assets/icon.png",
    }
    if all(name in names for name in required):
        return ""
    if all(f"app/{name}" in names for name in required):
        return "app/"
    return None


async def _process_and_store_package(
    *,
    package_zip: UploadFile,
    package_root: Path,
    name: str,
    version: str,
    description: str,
) -> tuple[Path, str, int]:
    """Validate uploaded zip, extract, generate app.yaml, build final package.zip.

    Returns (package_path, artifact_sha256, artifact_size).
    Caller must handle cleanup of package_root on failure.
    """
    yaml_text = (
        f'name: "{_yaml_quote(name)}"\n'
        f'version: "{_yaml_quote(version)}"\n'
        f'description: "{_yaml_quote(description)}"\n'
    )

    work_dir = package_root / "_build"
    try:
        app_dir = work_dir / "app"
        scripts_dir = app_dir / "scripts"
        assets_dir = app_dir / "assets"
        app_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

        (app_dir / "app.yaml").write_text(yaml_text, encoding="utf-8")

        tmp_zip = work_dir / "package.zip"
        tmp_zip.write_bytes(await package_zip.read())
        try:
            with zipfile.ZipFile(tmp_zip) as zf:
                names = {_normalize_zip_name(n) for n in zf.namelist() if _normalize_zip_name(n)}
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="package.zip 不是有效的 zip 文件") from exc

        prefix = _detect_package_prefix(names)
        if prefix is None:
            raise HTTPException(
                status_code=400,
                detail="package.zip 缺少必须文件",
            )

        _safe_extract_zip(tmp_zip, app_dir, prefix=prefix)

        package_root.mkdir(parents=True, exist_ok=True)
        package_path = package_root / "package.zip"
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in app_dir.rglob("*"):
                if path.is_dir():
                    continue
                zf.write(path, path.relative_to(work_dir))

        artifact_sha = file_sha256(package_path)
        artifact_size = package_path.stat().st_size
        return package_path, artifact_sha, artifact_size
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


async def upload_package(
    *,
    user: dict[str, Any],
    name: str,
    version: str,
    description: str,
    package_zip: UploadFile,
) -> dict[str, Any]:
    ts = now_ts()
    name_text = name.strip()
    version_text = version.strip()
    description_text = description.strip()

    if not name_text or not version_text:
        raise HTTPException(status_code=400, detail="必须提供 name 与 version")

    if "\n" in name_text or "\r" in name_text or "\n" in version_text or "\r" in version_text:
        raise HTTPException(status_code=400, detail="name 与 version 不能包含换行符")

    package_root: Path | None = None
    persisted = False

    try:
        with db_conn() as conn:
            name_tag = _app_name_tag(name_text)
            app_id_text = f"app_{name_tag}_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"
            while conn.execute("SELECT 1 FROM app WHERE app_id = ?", (app_id_text,)).fetchone():
                app_id_text = (
                    f"app_{name_tag}_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"
                )

            package_root = FILES_DIR / "apps" / app_id_text / version_text

            package_path, artifact_sha, artifact_size = await _process_and_store_package(
                package_zip=package_zip,
                package_root=package_root,
                name=name_text,
                version=version_text,
                description=description_text,
            )

            cur = conn.execute(
                """
                INSERT INTO app (app_id, owner_user_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (app_id_text, user["user_id"], name_text, description_text, ts, ts),
            )
            app_pk = cur.lastrowid
            create_audit_log(
                conn,
                app_id=app_pk,
                actor_user_id=user["user_id"],
                action="upload_package_create_app",
                detail={"app_id": app_id_text},
            )

            artifact_relpath = str(package_path.relative_to(FILES_DIR))

            cur = conn.execute(
                """
                INSERT INTO app_version (
                    app_id, version, description, status, published_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'published', ?, ?, ?)
                """,
                (app_pk, version_text, description_text, ts, ts, ts),
            )
            version_id = cur.lastrowid

            conn.execute(
                """
                INSERT INTO app_target (
                    version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (version_id, artifact_relpath, artifact_sha, artifact_size, ts, ts),
            )
            create_audit_log(
                conn,
                app_id=app_pk,
                actor_user_id=user["user_id"],
                action="upload_package_publish",
                detail={"version": version_text},
            )
            conn.commit()
            persisted = True
    finally:
        if not persisted and package_root and package_root.exists():
            shutil.rmtree(package_root, ignore_errors=True)

    return {
        "ok": True,
        "app_id": app_id_text,
        "version": version_text,
        "status": "published",
        "download_url": f"/files/{artifact_relpath}",
    }


# ---------------------------------------------------------------------------
# Version management functions
# ---------------------------------------------------------------------------


async def upload_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
    description: str,
    package_zip: UploadFile,
) -> dict[str, Any]:
    """Upload a new version to an existing app."""
    ts = now_ts()
    version_text = version.strip()
    description_text = description.strip()

    if not version_text:
        raise HTTPException(status_code=400, detail="必须提供 version")
    if "\n" in version_text or "\r" in version_text:
        raise HTTPException(status_code=400, detail="version 不能包含换行符")

    package_root: Path | None = None
    persisted = False

    try:
        with db_conn() as conn:
            app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
            app_pk = app_row["id"]

            existing = conn.execute(
                "SELECT 1 FROM app_version WHERE app_id = ? AND version = ?",
                (app_pk, version_text),
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail=f"版本 {version_text} 已存在")

            package_root = FILES_DIR / "apps" / app_id_text / version_text

            package_path, artifact_sha, artifact_size = await _process_and_store_package(
                package_zip=package_zip,
                package_root=package_root,
                name=app_row["name"],
                version=version_text,
                description=description_text or app_row["description"],
            )

            artifact_relpath = str(package_path.relative_to(FILES_DIR))

            ver_desc = description_text or app_row["description"]
            cur = conn.execute(
                """
                INSERT INTO app_version (
                    app_id, version, description, status, published_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'published', ?, ?, ?)
                """,
                (app_pk, version_text, ver_desc, ts, ts, ts),
            )
            version_id = cur.lastrowid

            conn.execute(
                """
                INSERT INTO app_target (
                    version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (version_id, artifact_relpath, artifact_sha, artifact_size, ts, ts),
            )

            if description_text:
                conn.execute(
                    "UPDATE app SET description = ?, updated_at = ? WHERE id = ?",
                    (description_text, ts, app_pk),
                )
            else:
                conn.execute(
                    "UPDATE app SET updated_at = ? WHERE id = ?",
                    (ts, app_pk),
                )

            create_audit_log(
                conn,
                app_id=app_pk,
                version_id=version_id,
                actor_user_id=user["user_id"],
                action="upload_version",
                detail={"version": version_text},
            )
            conn.commit()
            persisted = True
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"版本 {version_text} 已存在") from exc
    finally:
        if not persisted and package_root and package_root.exists():
            shutil.rmtree(package_root, ignore_errors=True)

    return {
        "ok": True,
        "app_id": app_id_text,
        "version": version_text,
        "status": "published",
        "download_url": f"/files/{artifact_relpath}",
    }


async def modify_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
    description: str | None = None,
    package_zip: UploadFile | None = None,
) -> dict[str, Any]:
    """Modify an existing version (update description and/or replace package)."""
    ts = now_ts()
    description_text = description.strip() if description else None

    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        app_pk = app_row["id"]
        version_row = get_version_owned(conn, app_row=app_row, version=version)
        version_id = version_row["id"]

        if description_text is not None:
            conn.execute(
                "UPDATE app SET description = ?, updated_at = ? WHERE id = ?",
                (description_text, ts, app_pk),
            )
            conn.execute(
                "UPDATE app_version SET description = ?, updated_at = ? WHERE id = ?",
                (description_text, ts, version_id),
            )

        if package_zip is not None and package_zip.filename:
            package_root = FILES_DIR / "apps" / app_id_text / version

            # Remove old package file (keep directory)
            old_pkg = package_root / "package.zip"
            if old_pkg.exists():
                old_pkg.unlink()

            package_path, artifact_sha, artifact_size = await _process_and_store_package(
                package_zip=package_zip,
                package_root=package_root,
                name=app_row["name"],
                version=version,
                description=description_text or app_row["description"],
            )

            artifact_relpath = str(package_path.relative_to(FILES_DIR))

            conn.execute(
                """
                UPDATE app_target
                SET artifact_relpath = ?, artifact_sha256 = ?, artifact_size = ?, updated_at = ?
                WHERE version_id = ?
                """,
                (artifact_relpath, artifact_sha, artifact_size, ts, version_id),
            )

        conn.execute(
            "UPDATE app_version SET updated_at = ? WHERE id = ?",
            (ts, version_id),
        )

        create_audit_log(
            conn,
            app_id=app_pk,
            version_id=version_id,
            actor_user_id=user["user_id"],
            action="modify_version",
            detail={"version": version, "description_changed": description_text is not None, "package_replaced": package_zip is not None and bool(package_zip.filename)},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id_text, "version": version}


def unpublish_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
) -> dict[str, Any]:
    """Soft delist: set version status to 'unpublished'."""
    ts = now_ts()
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)

        if version_row["status"] == "unpublished":
            raise HTTPException(status_code=400, detail="该版本已处于下架状态")

        published_count = conn.execute(
            "SELECT COUNT(*) FROM app_version WHERE app_id = ? AND status = 'published'",
            (app_row["id"],),
        ).fetchone()[0]
        if published_count <= 1:
            raise HTTPException(status_code=400, detail="无法下架：应用至少需要保留一个已发布版本")

        conn.execute(
            "UPDATE app_version SET status = 'unpublished', updated_at = ? WHERE id = ?",
            (ts, version_row["id"]),
        )
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=version_row["id"],
            actor_user_id=user["user_id"],
            action="unpublish_version",
            detail={"version": version},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id_text, "version": version, "status": "unpublished"}


def publish_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
) -> dict[str, Any]:
    """Re-publish a previously unpublished version."""
    ts = now_ts()
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)

        if version_row["status"] == "published":
            raise HTTPException(status_code=400, detail="该版本已处于发布状态")

        if version_row["published_at"]:
            # Re-publish: preserve original published_at
            conn.execute(
                "UPDATE app_version SET status = 'published', updated_at = ? WHERE id = ?",
                (ts, version_row["id"]),
            )
        else:
            # First publish
            conn.execute(
                "UPDATE app_version SET status = 'published', published_at = ?, updated_at = ? WHERE id = ?",
                (ts, ts, version_row["id"]),
            )
        create_audit_log(
            conn,
            app_id=app_row["id"],
            version_id=version_row["id"],
            actor_user_id=user["user_id"],
            action="publish_version",
            detail={"version": version},
        )
        conn.commit()

    return {"ok": True, "app_id": app_id_text, "version": version, "status": "published"}


def delete_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
) -> dict[str, Any]:
    """Hard delete: remove DB records and files for a version."""
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        version_row = get_version_owned(conn, app_row=app_row, version=version)
        version_id = version_row["id"]
        app_pk = app_row["id"]

        total_count = conn.execute(
            "SELECT COUNT(*) FROM app_version WHERE app_id = ?",
            (app_pk,),
        ).fetchone()[0]
        if total_count <= 1:
            raise HTTPException(status_code=400, detail="无法删除：应用至少需要保留一个版本")

        # Audit log before delete (FK ON DELETE SET NULL will null out version_id)
        create_audit_log(
            conn,
            app_id=app_pk,
            version_id=version_id,
            actor_user_id=user["user_id"],
            action="delete_version",
            detail={"version": version},
        )

        conn.execute("DELETE FROM app_target WHERE version_id = ?", (version_id,))
        conn.execute("DELETE FROM app_version WHERE id = ?", (version_id,))
        conn.commit()

    # Remove files on disk
    version_dir = FILES_DIR / "apps" / app_id_text / version
    if version_dir.exists():
        shutil.rmtree(version_dir, ignore_errors=True)

    return {"ok": True, "app_id": app_id_text, "version": version}


def delete_app(
    *,
    user: dict[str, Any],
    app_id_text: str,
) -> dict[str, Any]:
    """Hard delete: remove an entire app including all versions, targets, and files."""
    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        app_pk = app_row["id"]

        create_audit_log(
            conn,
            app_id=app_pk,
            actor_user_id=user["user_id"],
            action="delete_app",
            detail={"app_id": app_id_text},
        )

        # CASCADE will remove app_version, app_target, and audit logs
        conn.execute("DELETE FROM app WHERE id = ?", (app_pk,))
        conn.commit()

    # Remove all files on disk
    app_dir = FILES_DIR / "apps" / app_id_text
    if app_dir.exists() and app_dir.is_dir():
        shutil.rmtree(app_dir, ignore_errors=True)

    return {"ok": True, "app_id": app_id_text}
