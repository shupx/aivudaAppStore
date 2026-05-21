from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from aivudaappstore.backend.app.services.auth import (
    change_password,
    list_all_users,
    login,
    register,
    require_user,
    reset_password,
)
from aivudaappstore.backend.app.services.data_portability import (
    apply_import_archive,
    export_data_archive,
    inspect_import_archive,
    list_exportable_apps,
)
from aivudaappstore.backend.app.services.dev_service import (
    add_app_developer,
    batch_update_app_memberships,
    delete_app,
    delete_version,
    list_app_members,
    list_manageable_apps,
    modify_version,
    parse_package_manifest,
    publish_version,
    remove_app_developer,
    transfer_app_admin,
    unpublish_version,
    upload_package,
    upload_version,
)

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/auth/login")
async def dev_login(username: str = Form(...), password: str = Form(...)) -> Dict[str, object]:
    return login(username, password)


@router.post("/auth/register")
async def dev_register(username: str = Form(...), password: str = Form(...)) -> Dict[str, object]:
    return register(username, password)


@router.post("/auth/change-password")
async def dev_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return change_password(user=user, current_password=current_password, new_password=new_password)


@router.post("/auth/users/{user_id}/reset-password")
async def dev_reset_password(
    user_id: int,
    new_password: str = Form(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = require_user(authorization)
    return reset_password(actor=actor, target_user_id=user_id, new_password=new_password)


@router.get("/users")
async def dev_list_users(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = require_user(authorization)
    return list_all_users(actor=actor)


@router.get("/me")
async def dev_me(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = require_user(authorization)
    return {"user": user}


@router.get("/data/export/apps")
async def dev_exportable_apps(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_user(authorization)
    return list_exportable_apps()


@router.get("/data/export")
async def dev_export_data(
    selected_app_ids: str = "",
    authorization: Optional[str] = Header(default=None),
):
    require_user(authorization)
    return export_data_archive(selected_app_ids)


@router.post("/data/import/inspect")
async def dev_inspect_data_import(
    data_zip: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    require_user(authorization)
    return inspect_import_archive(data_zip)


@router.post("/data/import/apply")
async def dev_apply_data_import(
    resolutions: str = Form("{}"),
    selected_app_ids: str = Form(""),
    data_zip: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return apply_import_archive(
        package_zip=data_zip,
        resolutions_json=resolutions,
        selected_app_ids_json=selected_app_ids,
        user=user,
    )


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


@router.get("/apps/{app_id}/members")
async def dev_list_app_members(
    app_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = require_user(authorization)
    return list_app_members(user=user, app_id_text=app_id)


@router.get("/apps/manageable")
async def dev_list_manageable_apps(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = require_user(authorization)
    return list_manageable_apps(actor=actor)


@router.post("/apps/{app_id}/members")
async def dev_add_app_member(
    app_id: str,
    username: str = Form(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = require_user(authorization)
    return add_app_developer(actor=actor, app_id_text=app_id, username=username)


@router.delete("/apps/{app_id}/members/{user_id}")
async def dev_remove_app_member(
    app_id: str,
    user_id: int,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = require_user(authorization)
    return remove_app_developer(actor=actor, app_id_text=app_id, target_user_id=user_id)


@router.post("/apps/{app_id}/transfer-admin")
async def dev_transfer_app_admin(
    app_id: str,
    user_id: int = Form(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = require_user(authorization)
    return transfer_app_admin(actor=actor, app_id_text=app_id, target_user_id=user_id)


@router.post("/apps/memberships/batch")
async def dev_batch_update_app_memberships(
    action: str = Form(...),
    target_user_ids: str = Form(...),
    app_ids: str = Form(...),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    import json

    actor = require_user(authorization)
    try:
        target_user_id_list = json.loads(target_user_ids)
        app_id_list = json.loads(app_ids)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="target_user_ids and app_ids must be valid JSON arrays") from exc
    if not isinstance(target_user_id_list, list) or not isinstance(app_id_list, list):
        raise HTTPException(status_code=400, detail="target_user_ids and app_ids must be arrays")
    return batch_update_app_memberships(
        actor=actor,
        action=action,
        target_user_ids=[int(item) for item in target_user_id_list],
        app_ids=[str(item) for item in app_id_list],
    )
