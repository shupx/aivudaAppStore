from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.services.store_service import (
    store_app_detail as service_store_app_detail,
    store_download_url as service_store_download_url,
    store_index as service_store_index,
    store_manifest as service_store_manifest,
    store_sample_package as service_store_sample_package,
)

router = APIRouter(prefix="/store", tags=["store"])

@router.get("/index")
async def store_index() -> dict[str, Any]:
    return service_store_index()


@router.get("/sample-package")
async def store_sample_package() -> FileResponse:
    return service_store_sample_package()


@router.get("/apps/{app_id}")
async def store_app_detail(app_id: str) -> dict[str, Any]:
    return service_store_app_detail(app_id)


@router.get("/apps/{app_id}/versions/{version}/manifest")
async def store_manifest(
    app_id: str,
    version: str,
) -> dict[str, Any]:
    return service_store_manifest(app_id, version)


@router.get("/apps/{app_id}/versions/{version}/download-url")
async def store_download_url(app_id: str, version: str) -> dict[str, Any]:
    return service_store_download_url(app_id, version)
