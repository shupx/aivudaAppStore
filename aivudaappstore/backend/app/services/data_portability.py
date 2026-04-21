from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from aivudaappstore.backend.app.core.settings import DATA_DIR, FILES_DIR, TMP_DIR
from aivudaappstore.backend.app.services.db import create_audit_log, db_conn
from aivudaappstore.backend.app.services.utils import now_ts


IMPORT_DECISIONS = {"skip", "overwrite"}


def _cleanup_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def _safe_zip_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def _is_safe_zip_member(name: str) -> bool:
    safe_name = _safe_zip_name(name)
    return safe_name and not safe_name.startswith("../") and "/../" not in safe_name


def _is_safe_relpath(path_text: str) -> bool:
    path = Path(path_text)
    return bool(path_text) and not path.is_absolute() and ".." not in path.parts


def _find_repo_db_member(names: List[str]) -> str:
    candidates = [name for name in names if name.endswith("data/repo.db") or name == "repo.db"]
    if not candidates:
        raise HTTPException(status_code=400, detail="data/repo.db was not found in import zip")
    return sorted(candidates, key=len)[0]


def _data_prefix(repo_member: str) -> str:
    if repo_member == "repo.db":
        return ""
    return repo_member[: -len("repo.db")]


def _zip_data_member(data_prefix: str, relpath: str) -> str:
    relpath = f"files/{relpath}".replace("\\", "/")
    if data_prefix:
        return f"{data_prefix}{relpath}".replace("\\", "/")
    return relpath.replace("\\", "/")


def _extract_import_zip(package_zip: UploadFile) -> Tuple[Path, str, str]:
    if not package_zip.filename or not package_zip.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="import file must be a zip archive")

    tmp_root = TMP_DIR / f"import_{now_ts()}_{id(package_zip)}"
    tmp_root.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_root / "import.zip"
    try:
        with zip_path.open("wb") as fp:
            shutil.copyfileobj(package_zip.file, fp)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                raw_names = zf.namelist()
                if not raw_names:
                    raise HTTPException(status_code=400, detail="import zip is empty")
                names = [_safe_zip_name(name) for name in raw_names if _safe_zip_name(name)]
                if any(not _is_safe_zip_member(name) for name in names):
                    raise HTTPException(status_code=400, detail="import zip contains unsafe paths")
                repo_member = _find_repo_db_member(names)
                for member in zf.infolist():
                    safe_name = _safe_zip_name(member.filename)
                    if not safe_name:
                        continue
                    target = (tmp_root / safe_name).resolve()
                    if not _is_relative_to(target, tmp_root.resolve()):
                        raise HTTPException(status_code=400, detail="import zip contains unsafe paths")
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="import file is not a valid zip archive") from exc

        data_prefix = _data_prefix(repo_member)
        repo_path = tmp_root / repo_member
        if not repo_path.exists():
            raise HTTPException(status_code=400, detail="data/repo.db was not extracted")
        return tmp_root, repo_member, data_prefix
    except Exception:
        _cleanup_path(tmp_root)
        raise


def _connect_import_db(repo_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{repo_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_import_apps(repo_path: Path) -> Dict[str, Dict[str, Any]]:
    try:
        with _connect_import_db(repo_path) as conn:
            apps = conn.execute(
                """
                SELECT id, app_id, name, description, created_at, updated_at
                FROM app
                ORDER BY app_id
                """
            ).fetchall()
            versions = conn.execute(
                """
                SELECT id, app_id, version, description, status, published_at, created_at, updated_at
                FROM app_version
                ORDER BY app_id, version
                """
            ).fetchall()
            targets = conn.execute(
                """
                SELECT id, version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                FROM app_target
                ORDER BY version_id
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail="import repo.db has an invalid schema") from exc

    app_by_pk: Dict[int, Dict[str, Any]] = {}
    app_by_text: Dict[str, Dict[str, Any]] = {}
    for row in apps:
        app_id_text = str(row["app_id"] or "").strip()
        if not app_id_text:
            continue
        app = {
            "source_id": row["id"],
            "app_id": app_id_text,
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "versions": [],
        }
        app_by_pk[row["id"]] = app
        app_by_text[app_id_text] = app

    version_by_pk: Dict[int, Dict[str, Any]] = {}
    for row in versions:
        app = app_by_pk.get(row["app_id"])
        if not app:
            continue
        version = {
            "source_id": row["id"],
            "version": row["version"],
            "description": row["description"],
            "status": row["status"],
            "published_at": row["published_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "targets": [],
        }
        app["versions"].append(version)
        version_by_pk[row["id"]] = version

    for row in targets:
        version = version_by_pk.get(row["version_id"])
        if not version:
            continue
        relpath = str(row["artifact_relpath"] or "").strip()
        if relpath and not _is_safe_relpath(relpath):
            raise HTTPException(status_code=400, detail=f"unsafe artifact path in import db: {relpath}")
        version["targets"].append(
            {
                "artifact_relpath": relpath,
                "artifact_sha256": row["artifact_sha256"],
                "artifact_size": row["artifact_size"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    return app_by_text


def _public_app(app: Dict[str, Any]) -> Dict[str, Any]:
    versions = []
    artifact_count = 0
    for version in app["versions"]:
        artifact_count += len([target for target in version["targets"] if target["artifact_relpath"]])
        versions.append(
            {
                "version": version["version"],
                "status": version["status"],
                "artifact_count": len(version["targets"]),
            }
        )
    return {
        "app_id": app["app_id"],
        "name": app["name"],
        "description": app["description"],
        "versions": versions,
        "version_count": len(versions),
        "artifact_count": artifact_count,
    }


def _parse_selected_app_ids(selected_app_ids_json: str) -> Optional[List[str]]:
    if not selected_app_ids_json:
        return None
    try:
        payload = json.loads(selected_app_ids_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="selected_app_ids must be valid JSON") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="selected_app_ids must be an array")
    result: List[str] = []
    seen = set()
    for item in payload:
        app_id_text = str(item or "").strip()
        if not app_id_text or app_id_text in seen:
            continue
        seen.add(app_id_text)
        result.append(app_id_text)
    return result


def list_exportable_apps() -> Dict[str, Any]:
    with db_conn() as conn:
        apps = conn.execute(
            """
            SELECT a.app_id, a.name, a.description, COUNT(v.id) AS version_count
            FROM app a
            LEFT JOIN app_version v ON v.app_id = a.id
            GROUP BY a.id
            ORDER BY a.app_id
            """
        ).fetchall()
    return {
        "ok": True,
        "apps": [
            {
                "app_id": row["app_id"],
                "name": row["name"],
                "description": row["description"],
                "version_count": row["version_count"],
            }
            for row in apps
        ],
    }


def _create_subset_repo_db(target_db_path: Path, selected_app_ids: Optional[List[str]]) -> None:
    source_db_path = DATA_DIR / "repo.db"
    if not source_db_path.exists():
        raise HTTPException(status_code=404, detail="repo.db was not found")

    with sqlite3.connect(str(source_db_path)) as source_conn, sqlite3.connect(str(target_db_path)) as target_conn:
        source_conn.row_factory = sqlite3.Row
        target_conn.execute("PRAGMA foreign_keys = OFF")

        schema_rows = source_conn.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
              AND type IN ('table', 'index')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name
            """
        ).fetchall()
        for row in schema_rows:
            if row["sql"]:
                target_conn.execute(row["sql"])

        if selected_app_ids is None:
            selected_app_rows = source_conn.execute(
                """
                SELECT id, app_id, owner_user_id, name, description, created_at, updated_at
                FROM app
                ORDER BY id
                """
            ).fetchall()
        elif selected_app_ids:
            placeholders = ",".join(["?"] * len(selected_app_ids))
            selected_app_rows = source_conn.execute(
                f"""
                SELECT id, app_id, owner_user_id, name, description, created_at, updated_at
                FROM app
                WHERE app_id IN ({placeholders})
                ORDER BY id
                """,
                selected_app_ids,
            ).fetchall()
        else:
            selected_app_rows = []

        selected_app_pks = [row["id"] for row in selected_app_rows]
        if selected_app_rows:
            target_conn.executemany(
                """
                INSERT INTO app (id, app_id, owner_user_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id"],
                        row["app_id"],
                        row["owner_user_id"],
                        row["name"],
                        row["description"],
                        row["created_at"],
                        row["updated_at"],
                    )
                    for row in selected_app_rows
                ],
            )

        version_rows = []
        target_rows = []
        audit_rows = []
        if selected_app_pks:
            placeholders = ",".join(["?"] * len(selected_app_pks))
            version_rows = source_conn.execute(
                f"""
                SELECT id, app_id, version, description, status, published_at, created_at, updated_at
                FROM app_version
                WHERE app_id IN ({placeholders})
                ORDER BY id
                """,
                selected_app_pks,
            ).fetchall()
            version_ids = [row["id"] for row in version_rows]

            if version_rows:
                target_conn.executemany(
                    """
                    INSERT INTO app_version (id, app_id, version, description, status, published_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            row["id"],
                            row["app_id"],
                            row["version"],
                            row["description"],
                            row["status"],
                            row["published_at"],
                            row["created_at"],
                            row["updated_at"],
                        )
                        for row in version_rows
                    ],
                )

            if version_ids:
                version_placeholders = ",".join(["?"] * len(version_ids))
                target_rows = source_conn.execute(
                    f"""
                    SELECT id, version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                    FROM app_target
                    WHERE version_id IN ({version_placeholders})
                    ORDER BY id
                    """,
                    version_ids,
                ).fetchall()
                if target_rows:
                    target_conn.executemany(
                        """
                        INSERT INTO app_target (
                            id, version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                row["id"],
                                row["version_id"],
                                row["artifact_relpath"],
                                row["artifact_sha256"],
                                row["artifact_size"],
                                row["created_at"],
                                row["updated_at"],
                            )
                            for row in target_rows
                        ],
                    )

            audit_rows = source_conn.execute(
                f"""
                SELECT id, app_id, version_id, actor_user_id, action, detail_json, created_at
                FROM app_audit_log
                WHERE app_id IN ({placeholders})
                ORDER BY id
                """,
                selected_app_pks,
            ).fetchall()
            if audit_rows:
                target_conn.executemany(
                    """
                    INSERT INTO app_audit_log (id, app_id, version_id, actor_user_id, action, detail_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            row["id"],
                            row["app_id"],
                            row["version_id"],
                            row["actor_user_id"],
                            row["action"],
                            row["detail_json"],
                            row["created_at"],
                        )
                        for row in audit_rows
                    ],
                )

        target_conn.commit()


def export_data_archive(selected_app_ids_json: str = "") -> FileResponse:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_name = f"aivudaAppStore-data-{stamp}.zip"
    archive_path = TMP_DIR / archive_name
    selected_app_ids = _parse_selected_app_ids(selected_app_ids_json)
    allowed_relpaths = None
    subset_db_path = TMP_DIR / f"repo_export_{stamp}_{now_ts()}.db"

    if selected_app_ids is not None:
        allowed_relpaths = {"repo.db"}
        if selected_app_ids:
            with db_conn() as conn:
                placeholders = ",".join(["?"] * len(selected_app_ids))
                rows = conn.execute(
                    f"""
                    SELECT t.artifact_relpath
                    FROM app_target t
                    JOIN app_version v ON v.id = t.version_id
                    JOIN app a ON a.id = v.app_id
                    WHERE a.app_id IN ({placeholders})
                    """,
                    selected_app_ids,
                ).fetchall()
            for row in rows:
                relpath = str(row["artifact_relpath"] or "").strip()
                if relpath:
                    allowed_relpaths.add(Path(relpath).as_posix())
    try:
        _create_subset_repo_db(subset_db_path, selected_app_ids)

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(subset_db_path, (Path("data") / "repo.db").as_posix())
            for path in sorted(DATA_DIR.rglob("*")):
                rel = path.relative_to(DATA_DIR)
                if not rel.parts or rel.parts[0] in {"tmp"}:
                    continue
                rel_posix = rel.as_posix()
                if rel_posix == "repo.db":
                    continue
                if allowed_relpaths is not None:
                    if rel.parts[0] == "files":
                        if rel_posix[len("files/") :] not in allowed_relpaths:
                            continue
                    elif rel_posix not in allowed_relpaths:
                        continue
                arcname = Path("data") / rel
                if path.is_dir():
                    continue
                zf.write(path, arcname.as_posix())
    finally:
        _cleanup_path(subset_db_path)

    return FileResponse(
        path=str(archive_path),
        media_type="application/zip",
        filename=archive_name,
        background=BackgroundTask(_cleanup_path, archive_path),
    )


def inspect_import_archive(package_zip: UploadFile) -> Dict[str, Any]:
    tmp_root, repo_member, _data_prefix_text = _extract_import_zip(package_zip)
    try:
        apps = _load_import_apps(tmp_root / repo_member)
        app_ids = sorted(apps)
        with db_conn() as conn:
            existing = {
                row["app_id"]
                for row in conn.execute(
                    f"SELECT app_id FROM app WHERE app_id IN ({','.join(['?'] * len(app_ids))})",
                    app_ids,
                ).fetchall()
            } if app_ids else set()

        public_apps = [_public_app(apps[app_id]) for app_id in app_ids]
        conflicts = [app for app in public_apps if app["app_id"] in existing]
        artifact_count = sum(app["artifact_count"] for app in public_apps)
        version_count = sum(app["version_count"] for app in public_apps)
        return {
            "ok": True,
            "summary": {
                "app_count": len(public_apps),
                "version_count": version_count,
                "artifact_count": artifact_count,
            },
            "apps": public_apps,
            "conflicts": conflicts,
            "importable_apps": [app for app in public_apps if app["app_id"] not in existing],
        }
    finally:
        _cleanup_path(tmp_root)


def _validate_artifacts(tmp_root: Path, data_prefix: str, app: Dict[str, Any]) -> None:
    for version in app["versions"]:
        for target in version["targets"]:
            relpath = target["artifact_relpath"]
            if not relpath:
                continue
            source_path = tmp_root / _zip_data_member(data_prefix, relpath)
            if not source_path.exists() or not source_path.is_file():
                raise FileNotFoundError(relpath)


def _copy_artifacts(tmp_root: Path, data_prefix: str, app: Dict[str, Any]) -> None:
    for version in app["versions"]:
        for target in version["targets"]:
            relpath = target["artifact_relpath"]
            if not relpath:
                continue
            source_path = tmp_root / _zip_data_member(data_prefix, relpath)
            target_path = FILES_DIR / relpath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)


def _import_single_app(
    conn: sqlite3.Connection,
    *,
    tmp_root: Path,
    data_prefix: str,
    app: Dict[str, Any],
    decision: str,
    user: Dict[str, Any],
) -> str:
    app_id_text = app["app_id"]
    existing = conn.execute("SELECT id FROM app WHERE app_id = ?", (app_id_text,)).fetchone()
    if existing and decision == "skip":
        return "skipped"
    if existing and decision != "overwrite":
        raise HTTPException(status_code=400, detail=f"resolution for {app_id_text} must be skip or overwrite")

    _validate_artifacts(tmp_root, data_prefix, app)

    app_dir = FILES_DIR / "apps" / app_id_text
    backup_dir: Optional[Path] = None
    copied = False
    savepoint = f"import_app_{abs(hash(app_id_text))}"

    try:
        conn.execute(f"SAVEPOINT {savepoint}")
        if existing:
            backup_dir = TMP_DIR / f"import_backup_{now_ts()}_{app_id_text}"
            if app_dir.exists():
                if backup_dir.exists():
                    _cleanup_path(backup_dir)
                shutil.move(str(app_dir), str(backup_dir))
            conn.execute("DELETE FROM app WHERE app_id = ?", (app_id_text,))

        cur = conn.execute(
            """
            INSERT INTO app (app_id, owner_user_id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                app_id_text,
                user["user_id"],
                app["name"] or app_id_text,
                app["description"] or "",
                app["created_at"] or now_ts(),
                app["updated_at"] or now_ts(),
            ),
        )
        app_pk = cur.lastrowid

        for version in app["versions"]:
            cur = conn.execute(
                """
                INSERT INTO app_version (
                    app_id, version, description, status, published_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    app_pk,
                    version["version"],
                    version["description"] or "",
                    version["status"] or "published",
                    version["published_at"],
                    version["created_at"] or now_ts(),
                    version["updated_at"] or now_ts(),
                ),
            )
            version_id = cur.lastrowid
            for target in version["targets"]:
                conn.execute(
                    """
                    INSERT INTO app_target (
                        version_id, artifact_relpath, artifact_sha256, artifact_size, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        target["artifact_relpath"],
                        target["artifact_sha256"],
                        target["artifact_size"],
                        target["created_at"] or now_ts(),
                        target["updated_at"] or now_ts(),
                    ),
                )

        _copy_artifacts(tmp_root, data_prefix, app)
        copied = True
        create_audit_log(
            conn,
            app_id=app_pk,
            actor_user_id=user["user_id"],
            action="import_app_overwrite" if existing else "import_app_create",
            detail={"app_id": app_id_text},
        )
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        if backup_dir:
            _cleanup_path(backup_dir)
        return "overwritten" if existing else "imported"
    except Exception:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        if copied and app_dir.exists():
            _cleanup_path(app_dir)
        if backup_dir and backup_dir.exists():
            if app_dir.exists():
                _cleanup_path(app_dir)
            shutil.move(str(backup_dir), str(app_dir))
        raise


def apply_import_archive(
    *,
    package_zip: UploadFile,
    resolutions_json: str,
    selected_app_ids_json: str,
    user: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        resolutions = json.loads(resolutions_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="resolutions must be valid JSON") from exc
    if not isinstance(resolutions, dict):
        raise HTTPException(status_code=400, detail="resolutions must be an object")
    for app_id_text, decision in resolutions.items():
        if decision not in IMPORT_DECISIONS:
            raise HTTPException(status_code=400, detail=f"invalid resolution for {app_id_text}")
    selected_app_ids = _parse_selected_app_ids(selected_app_ids_json)
    selected_set = set(selected_app_ids or [])

    tmp_root, repo_member, data_prefix = _extract_import_zip(package_zip)
    result: Dict[str, Any] = {
        "ok": True,
        "imported_apps": [],
        "overwritten_apps": [],
        "skipped_apps": [],
        "failed_apps": [],
        "messages": [],
    }
    try:
        apps = _load_import_apps(tmp_root / repo_member)
        if selected_app_ids is not None:
            apps = {app_id_text: app for app_id_text, app in apps.items() if app_id_text in selected_set}
        with db_conn() as conn:
            for app_id_text in sorted(apps):
                app = apps[app_id_text]
                existing = conn.execute("SELECT 1 FROM app WHERE app_id = ?", (app_id_text,)).fetchone()
                decision = str(resolutions.get(app_id_text) or ("overwrite" if not existing else "")).strip()
                if existing and not decision:
                    raise HTTPException(status_code=400, detail=f"missing resolution for {app_id_text}")

                try:
                    status = _import_single_app(
                        conn,
                        tmp_root=tmp_root,
                        data_prefix=data_prefix,
                        app=app,
                        decision=decision,
                        user=user,
                    )
                    if status == "imported":
                        result["imported_apps"].append(app_id_text)
                    elif status == "overwritten":
                        result["overwritten_apps"].append(app_id_text)
                    elif status == "skipped":
                        result["skipped_apps"].append(app_id_text)
                except FileNotFoundError as exc:
                    result["failed_apps"].append(app_id_text)
                    result["messages"].append(f"{app_id_text}: missing artifact {exc}")
                except sqlite3.Error as exc:
                    result["failed_apps"].append(app_id_text)
                    result["messages"].append(f"{app_id_text}: database import failed: {exc}")
                except OSError as exc:
                    result["failed_apps"].append(app_id_text)
                    result["messages"].append(f"{app_id_text}: file import failed: {exc}")

            conn.commit()
        return result
    finally:
        _cleanup_path(tmp_root)
