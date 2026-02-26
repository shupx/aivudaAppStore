from __future__ import annotations

import re
import secrets
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from app.core.settings import FILES_DIR
from app.services.db import create_audit_log, db_conn
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

    yaml_text = (
        f'name: "{_yaml_quote(name_text)}"\n'
        f'version: "{_yaml_quote(version_text)}"\n'
        f'description: "{_yaml_quote(description_text)}"\n'
    )

    with db_conn() as conn:
        name_tag = _app_name_tag(name_text)
        app_id_text = f"app_{name_tag}_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"
        while conn.execute("SELECT 1 FROM app WHERE app_id = ?", (app_id_text,)).fetchone():
            app_id_text = (
                f"app_{name_tag}_{time.strftime('%Y%m%d_%H%M%S', time.localtime(ts))}_{secrets.token_hex(3)}"
            )

        package_root = FILES_DIR / "apps" / app_id_text / version_text
        work_dir = package_root / "_build"
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
                names = {_normalize_zip_name(name) for name in zf.namelist() if _normalize_zip_name(name)}
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="package.zip 不是有效的 zip 文件") from exc

        prefix = _detect_package_prefix(names)
        if prefix is None:
            raise HTTPException(
                status_code=400,
                detail="package.zip 缺少必须文件：scripts/install.sh、scripts/uninstall.sh、scripts/start.sh、assets/icon.png",
            )

        _safe_extract_zip(tmp_zip, app_dir, prefix=prefix)

        package_root.mkdir(parents=True, exist_ok=True)
        package_path = package_root / "package.zip"
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in app_dir.rglob("*"):
                if path.is_dir():
                    continue
                zf.write(path, path.relative_to(work_dir))

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
        artifact_sha = file_sha256(package_path)
        artifact_size = package_path.stat().st_size

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
            action="upload_package_publish",
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
