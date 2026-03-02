from __future__ import annotations

import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
import yaml

from app.core.settings import APPSTORE_API_PREFIX, FILES_DIR
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


def _known_manifest_fields() -> set[str]:
    return {
        "app_id",
        "name",
        "description",
        "version",
        "run",
        "icon",
        "pre_install",
        "pre_uninstall",
        "update_this_version",
        "default_config",
        "config_schema",
        "extra_manifest",
    }


def _default_manifest_form() -> dict[str, Any]:
    return {
        "app_id": "",
        "name": "",
        "description": "",
        "version": "0.1.0",
        "run": {"entrypoint": "", "args": []},
        "icon": "",
        "pre_install": "",
        "pre_uninstall": "",
        "update_this_version": "",
        "default_config": {},
        "config_schema": None,
        "extra_manifest": {},
    }


def _find_manifest_member(names: set[str]) -> str | None:
    for name in ("manifest.yaml", "manifest.yml"):
        if name in names:
            return name

    for name in sorted(names):
        if name.endswith("/manifest.yaml") or name.endswith("/manifest.yml"):
            if name.count("/") == 1:
                return name
    return None


def _detect_package_prefix(names: set[str], manifest_member: str | None) -> str:
    if manifest_member:
        if "/" in manifest_member:
            return manifest_member.rsplit("/", 1)[0] + "/"
        return ""

    if any("/" not in name for name in names):
        return ""

    prefixes = {name.split("/", 1)[0] for name in names if "/" in name}
    if len(prefixes) == 1:
        return f"{next(iter(prefixes))}/"
    return ""


def _parse_manifest_yaml(text: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"manifest.yaml is not valid YAML: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="manifest.yaml top-level value must be an object")
    return payload


def _normalize_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    extra_manifest = merged.pop("extra_manifest", None)
    if extra_manifest is not None and not isinstance(extra_manifest, dict):
        raise HTTPException(status_code=400, detail="manifest.extra_manifest must be an object")

    run_raw = merged.get("run")
    if run_raw is None:
        run_raw = {}
    if not isinstance(run_raw, dict):
        raise HTTPException(status_code=400, detail="manifest.run must be an object")

    args_raw = run_raw.get("args")
    if args_raw is None:
        args = []
    elif isinstance(args_raw, list):
        args = [str(item) for item in args_raw]
    else:
        args = [str(args_raw)]

    result: dict[str, Any] = {
        "app_id": str(merged.get("app_id") or "").strip(),
        "name": str(merged.get("name") or "").strip(),
        "description": str(merged.get("description") or "").strip(),
        "version": str(merged.get("version") or "").strip(),
        "run": {
            "entrypoint": str(run_raw.get("entrypoint") or "").strip(),
            "args": args,
        },
    }

    optional_paths = ("icon", "pre_install", "pre_uninstall", "update_this_version")
    for key in optional_paths:
        value = merged.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result[key] = text

    default_config = merged.get("default_config", {})
    if default_config is None:
        default_config = {}
    if not isinstance(default_config, dict):
        raise HTTPException(status_code=400, detail="manifest.default_config must be an object")
    result["default_config"] = default_config

    config_schema = merged.get("config_schema")
    if config_schema is not None and not isinstance(config_schema, dict):
        raise HTTPException(status_code=400, detail="manifest.config_schema must be an object or null")
    if config_schema is not None:
        result["config_schema"] = config_schema

    known = _known_manifest_fields()
    for key, value in merged.items():
        if key in known:
            continue
        result[key] = value
    if isinstance(extra_manifest, dict):
        for key, value in extra_manifest.items():
            if key not in result:
                result[key] = value

    if not result["name"] and result["app_id"]:
        result["name"] = result["app_id"]
    if not result["version"]:
        result["version"] = "0.0.0"

    return result


def _manifest_for_form(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_manifest_payload(payload)
    form = _default_manifest_form()
    form["app_id"] = normalized.get("app_id", "")
    form["name"] = normalized.get("name", "")
    form["description"] = normalized.get("description", "")
    form["version"] = normalized.get("version", "0.1.0")
    form["run"] = normalized.get("run", {"entrypoint": "", "args": []})
    form["icon"] = normalized.get("icon", "")
    form["pre_install"] = normalized.get("pre_install", "")
    form["pre_uninstall"] = normalized.get("pre_uninstall", "")
    form["update_this_version"] = normalized.get("update_this_version", "")
    form["default_config"] = normalized.get("default_config", {})
    form["config_schema"] = normalized.get("config_schema")

    known = _known_manifest_fields()
    extra: dict[str, Any] = {}
    for key, value in normalized.items():
        if key in known:
            continue
        extra[key] = value
    form["extra_manifest"] = extra
    return form


def _build_package_entries(
    names: set[str],
    *,
    prefix: str = "",
    max_depth: int = 3,
) -> list[dict[str, Any]]:
    entries_map: dict[str, dict[str, Any]] = {}

    for raw_name in sorted(names):
        norm_name = _normalize_zip_name(raw_name)
        if not norm_name:
            continue
        if prefix:
            if not norm_name.startswith(prefix):
                continue
            norm_name = norm_name[len(prefix) :]
        norm_name = norm_name.strip("/")
        if not norm_name:
            continue

        parts = [part for part in norm_name.split("/") if part]
        if not parts:
            continue

        limit = min(len(parts), max_depth)
        for depth in range(1, limit + 1):
            partial = parts[:depth]
            is_last_visible = depth == limit
            is_original_last = depth == len(parts)

            if is_last_visible and is_original_last:
                node_type = "file"
                path = "/".join(partial)
            else:
                node_type = "dir"
                path = "/".join(partial) + "/"

            node = entries_map.get(path)
            if node is None:
                entries_map[path] = {
                    "path": path,
                    "depth": depth,
                    "type": node_type,
                    "truncated": False,
                }
                node = entries_map[path]
            elif node_type == "dir":
                node["type"] = "dir"

            if depth == max_depth and len(parts) > max_depth:
                node["type"] = "dir"
                node["truncated"] = True

    return sorted(entries_map.values(), key=lambda item: (item["depth"], item["path"]))


def _resolve_inside_package(root: Path, rel_path: str, *, field: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail=f"manifest.{field} cannot be an absolute path")
    resolved = (root / candidate).resolve()
    root_real = root.resolve()
    if not str(resolved).startswith(str(root_real)):
        raise HTTPException(status_code=400, detail=f"manifest.{field} path escapes package root")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=400, detail=f"manifest.{field} points to a missing file: {rel_path}")
    return resolved


def _validate_manifest_for_package(
    manifest: dict[str, Any],
    *,
    expected_app_id: str | None = None,
    expected_version: str | None = None,
) -> None:
    app_id = str(manifest.get("app_id") or "").strip()
    if not app_id:
        raise HTTPException(status_code=400, detail="manifest.app_id is required")
    if expected_app_id and app_id != expected_app_id:
        raise HTTPException(status_code=400, detail=f"manifest.app_id must be {expected_app_id}")

    version = str(manifest.get("version") or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="manifest.version is required")
    if expected_version and version != expected_version:
        raise HTTPException(status_code=400, detail=f"manifest.version must be {expected_version}")

    name = str(manifest.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="manifest.name is required")

    description = str(manifest.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="manifest.description is required")


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
            if norm_name in {"app.yaml", "manifest.yaml", "manifest.yml"}:
                continue
            member_path = (dest_dir / norm_name).resolve()
            if not str(member_path).startswith(str(dest_real)):
                raise HTTPException(status_code=400, detail="Invalid path in package.zip")
            member_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, member_path.open("wb") as dst:
                dst.write(src.read())


async def _process_and_store_package(
    *,
    package_zip: UploadFile,
    package_root: Path,
    manifest_payload: dict[str, Any],
    expected_app_id: str | None = None,
    expected_version: str | None = None,
) -> tuple[Path, str, int]:
    """Validate uploaded zip, extract, generate manifest.yaml, build final package.zip.

    Returns (package_path, artifact_sha256, artifact_size).
    Caller must handle cleanup of package_root on failure.
    """
    work_dir = package_root / "_build"
    try:
        app_dir = work_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        tmp_zip = work_dir / "package.zip"
        tmp_zip.write_bytes(await package_zip.read())
        try:
            with zipfile.ZipFile(tmp_zip) as zf:
                names = {_normalize_zip_name(n) for n in zf.namelist() if _normalize_zip_name(n)}
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="package.zip is not a valid zip file") from exc

        if not names:
            raise HTTPException(status_code=400, detail="package.zip is empty")

        manifest_member = _find_manifest_member(names)
        prefix = _detect_package_prefix(names, manifest_member)

        _safe_extract_zip(tmp_zip, app_dir, prefix=prefix)

        manifest = _normalize_manifest_payload(manifest_payload)
        _validate_manifest_for_package(
            manifest,
            expected_app_id=expected_app_id,
            expected_version=expected_version,
        )

        (app_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        legacy_manifest = app_dir / "manifest.yml"
        if legacy_manifest.exists():
            legacy_manifest.unlink()

        package_root.mkdir(parents=True, exist_ok=True)
        package_path = package_root / "package.zip"
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in app_dir.rglob("*"):
                if path.is_dir():
                    continue
                zf.write(path, path.relative_to(app_dir))

        artifact_sha = file_sha256(package_path)
        artifact_size = package_path.stat().st_size
        return package_path, artifact_sha, artifact_size
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def _parse_manifest_json(manifest_json: str) -> dict[str, Any]:
    text = manifest_json.strip()
    if not text:
        raise HTTPException(status_code=400, detail="manifest_json is required")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"manifest_json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="manifest_json top-level value must be an object")
    return payload


async def parse_package_manifest(*, package_zip: UploadFile) -> dict[str, Any]:
    tmp_dir = FILES_DIR / "_manifest_parse"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_zip = tmp_dir / f"{now_ts()}_{_app_name_tag(package_zip.filename or 'package')}.zip"
    try:
        tmp_zip.write_bytes(await package_zip.read())
        try:
            with zipfile.ZipFile(tmp_zip) as zf:
                names = {_normalize_zip_name(n) for n in zf.namelist() if _normalize_zip_name(n)}
                if not names:
                    raise HTTPException(status_code=400, detail="package.zip is empty")
                manifest_member = _find_manifest_member(names)
                prefix = _detect_package_prefix(names, manifest_member)
                package_entries = _build_package_entries(names, prefix=prefix, max_depth=3)
                if not manifest_member:
                    raise HTTPException(status_code=400, detail="manifest.yaml was not found in package.zip")
                with zf.open(manifest_member) as fp:
                    raw_manifest = _parse_manifest_yaml(fp.read().decode("utf-8"))
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="package.zip is not a valid zip file") from exc

        return {
            "ok": True,
            "has_manifest": True,
            "found_path": manifest_member,
            "manifest": raw_manifest,
            "normalized_manifest": _manifest_for_form(raw_manifest),
            "package_entries": package_entries,
            "warnings": [],
        }
    finally:
        if tmp_zip.exists():
            tmp_zip.unlink(missing_ok=True)
        if tmp_dir.exists():
            tmp_dir.rmdir()


async def upload_package(
    *,
    user: dict[str, Any],
    name: str,
    version: str,
    description: str,
    manifest_json: str,
    package_zip: UploadFile,
) -> dict[str, Any]:
    ts = now_ts()
    manifest_payload = _parse_manifest_json(manifest_json)
    manifest = _normalize_manifest_payload(manifest_payload)

    app_id_text = str(manifest.get("app_id") or "").strip()
    name_text = str(manifest.get("name") or app_id_text).strip()
    version_text = str(manifest.get("version") or "").strip()
    description_text = str(manifest.get("description") or "").strip()

    if not app_id_text:
        raise HTTPException(status_code=400, detail="manifest.app_id is required")
    if not name_text:
        raise HTTPException(status_code=400, detail="manifest.name is required")
    if not description_text:
        raise HTTPException(status_code=400, detail="manifest.description is required")
    if not version_text:
        raise HTTPException(status_code=400, detail="manifest.version is required")

    package_root: Path | None = None
    persisted = False

    try:
        with db_conn() as conn:
            exists = conn.execute("SELECT 1 FROM app WHERE app_id = ?", (app_id_text,)).fetchone()
            if exists:
                raise HTTPException(status_code=409, detail=f"app_id {app_id_text} already exists")

            package_root = FILES_DIR / "apps" / app_id_text / version_text

            package_path, artifact_sha, artifact_size = await _process_and_store_package(
                package_zip=package_zip,
                package_root=package_root,
                manifest_payload=manifest,
                expected_app_id=app_id_text,
                expected_version=version_text,
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
        "download_url": f"{APPSTORE_API_PREFIX}/files/{artifact_relpath}",
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
    manifest_json: str,
    package_zip: UploadFile,
) -> dict[str, Any]:
    """Upload a new version to an existing app."""
    ts = now_ts()
    manifest_payload = _parse_manifest_json(manifest_json)
    manifest = _normalize_manifest_payload(manifest_payload)
    manifest_version = str(manifest.get("version") or "").strip()
    if not manifest_version:
        raise HTTPException(status_code=400, detail="manifest.version is required")

    version_text = version.strip() or manifest_version
    if version.strip() and version.strip() != manifest_version:
        raise HTTPException(status_code=400, detail="version does not match manifest.version")

    description_text = description.strip() or str(manifest.get("description") or "").strip()

    package_root: Path | None = None
    persisted = False

    try:
        with db_conn() as conn:
            app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
            app_pk = app_row["id"]

            expected_name = str(app_row["name"] or "").strip()
            manifest_name = str(manifest.get("name") or "").strip()
            if manifest_name != expected_name:
                raise HTTPException(status_code=400, detail="manifest.name must match the existing app name")

            existing = conn.execute(
                "SELECT 1 FROM app_version WHERE app_id = ? AND version = ?",
                (app_pk, version_text),
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail=f"Version {version_text} already exists")

            package_root = FILES_DIR / "apps" / app_id_text / version_text

            package_path, artifact_sha, artifact_size = await _process_and_store_package(
                package_zip=package_zip,
                package_root=package_root,
                manifest_payload=manifest,
                expected_app_id=app_id_text,
                expected_version=version_text,
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
        raise HTTPException(status_code=409, detail=f"Version {version_text} already exists") from exc
    finally:
        if not persisted and package_root and package_root.exists():
            shutil.rmtree(package_root, ignore_errors=True)

    return {
        "ok": True,
        "app_id": app_id_text,
        "version": version_text,
        "status": "published",
        "download_url": f"{APPSTORE_API_PREFIX}/files/{artifact_relpath}",
    }


async def modify_version(
    *,
    user: dict[str, Any],
    app_id_text: str,
    version: str,
    description: str | None = None,
    manifest_json: str | None = None,
    package_zip: UploadFile | None = None,
) -> dict[str, Any]:
    """Modify an existing version (update description and/or replace package)."""
    ts = now_ts()
    description_text = description.strip() if description else None
    manifest: dict[str, Any] | None = None

    if package_zip is not None and package_zip.filename:
        manifest = _normalize_manifest_payload(_parse_manifest_json(manifest_json or ""))
        manifest_version = str(manifest.get("version") or "").strip()
        if manifest_version != version:
            raise HTTPException(status_code=400, detail="manifest.version must match the version being edited")
        manifest_desc = str(manifest.get("description") or "").strip()
        if description_text is None and manifest_desc:
            description_text = manifest_desc

    with db_conn() as conn:
        app_row = get_app_owned(conn, app_id_text=app_id_text, user=user)
        app_pk = app_row["id"]
        version_row = get_version_owned(conn, app_row=app_row, version=version)
        version_id = version_row["id"]

        if manifest is not None:
            expected_name = str(app_row["name"] or "").strip()
            manifest_name = str(manifest.get("name") or "").strip()
            if manifest_name != expected_name:
                raise HTTPException(status_code=400, detail="manifest.name must match the existing app name")

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
                manifest_payload=manifest or {},
                expected_app_id=app_id_text,
                expected_version=version,
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
            raise HTTPException(status_code=400, detail="This version is already unpublished")

        published_count = conn.execute(
            "SELECT COUNT(*) FROM app_version WHERE app_id = ? AND status = 'published'",
            (app_row["id"],),
        ).fetchone()[0]
        if published_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot unpublish: at least one published version must remain")

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
            raise HTTPException(status_code=400, detail="This version is already published")

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
            raise HTTPException(status_code=400, detail="Cannot delete: the app must keep at least one version")

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
