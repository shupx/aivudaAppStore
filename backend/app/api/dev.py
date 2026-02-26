from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, Header, UploadFile

from app.services.auth import login, require_user
from app.services.dev_service import upload_package

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/auth/login")
async def dev_login(username: str = Form(...), password: str = Form(...)) -> dict[str, object]:
    return login(username, password)


@router.get("/me")
async def dev_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = require_user(authorization)
    return {"user": user}


@router.post("/apps/upload-package")
async def dev_upload_package(
    name: str = Form(""),
    version: str = Form(""),
    description: str = Form(""),
    package_zip: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = require_user(authorization)
    return await upload_package(
        user=user,
        name=name,
        version=version,
        description=description,
        package_zip=package_zip,
    )
