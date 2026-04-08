from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, Header, UploadFile

from aivudaappstore.backend.app.services.auth import login, require_user
from aivudaappstore.backend.app.services.dev_service import (
    delete_app,
    delete_version,
    modify_version,
    parse_package_manifest,
    publish_version,
    unpublish_version,
    upload_package,
    upload_version,
)

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/auth/login")
async def dev_login(username: str = Form(...), password: str = Form(...)) -> Dict[str, object]:
    return login(username, password)


@router.get("/me")
async def dev_me(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = require_user(authorization)
    return {"user": user}


@router.post("/apps/upload-package")
async def dev_upload_package(
    name: str = Form(""),
    version: str = Form(""),
    description: str = Form(""),
    manifest_json: str = Form(""),
    package_zip: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return await upload_package(
        user=user,
        name=name,
        version=version,
        description=description,
        manifest_json=manifest_json,
        package_zip=package_zip,
    )


@router.post("/apps/manifest/parse-package")
async def dev_parse_package_manifest(
    package_zip: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    require_user(authorization)
    return await parse_package_manifest(package_zip=package_zip)


@router.post("/apps/{app_id}/versions")
async def dev_upload_version(
    app_id: str,
    version: str = Form(""),
    description: str = Form(""),
    manifest_json: str = Form(""),
    package_zip: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return await upload_version(
        user=user,
        app_id_text=app_id,
        version=version,
        description=description,
        manifest_json=manifest_json,
        package_zip=package_zip,
    )


@router.patch("/apps/{app_id}/versions/{version}")
async def dev_modify_version(
    app_id: str,
    version: str,
    description: str = Form(None),
    manifest_json: Optional[str] = Form(None),
    package_zip: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return await modify_version(
        user=user,
        app_id_text=app_id,
        version=version,
        description=description,
        manifest_json=manifest_json,
        package_zip=package_zip,
    )


@router.post("/apps/{app_id}/versions/{version}/unpublish")
async def dev_unpublish_version(
    app_id: str,
    version: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return unpublish_version(user=user, app_id_text=app_id, version=version)


@router.post("/apps/{app_id}/versions/{version}/publish")
async def dev_publish_version(
    app_id: str,
    version: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return publish_version(user=user, app_id_text=app_id, version=version)


@router.delete("/apps/{app_id}")
async def dev_delete_app(
    app_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return delete_app(user=user, app_id_text=app_id)


@router.delete("/apps/{app_id}/versions/{version}")
async def dev_delete_version(
    app_id: str,
    version: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return delete_version(user=user, app_id_text=app_id, version=version)
