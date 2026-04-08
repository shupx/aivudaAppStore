from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from aivudaappstore.backend.app.api.dev import router as dev_router
from aivudaappstore.backend.app.api.store import router as store_router
from aivudaappstore.backend.app.core.settings import APPSTORE_API_PREFIX, FRONTEND_UI_DIST_DIR, ensure_storage_dirs
from aivudaappstore.backend.app.services.auth import hash_password
from aivudaappstore.backend.app.services.db import init_db


def create_app() -> FastAPI:
    ensure_storage_dirs()
    api = FastAPI(title="Aivuda App Store", version="0.1.0")

    public_paths = (
        f"{APPSTORE_API_PREFIX}/store",
    )

    def is_public_path(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in public_paths)

    def apply_public_cors(response: Response) -> None:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Range"
        response.headers["Access-Control-Expose-Headers"] = "Content-Length, Content-Range, Content-Disposition"
        response.headers["Access-Control-Max-Age"] = "86400"

    @api.middleware("http")
    async def public_cors_middleware(request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS" and is_public_path(request.url.path):
            response = Response(status_code=204)
            apply_public_cors(response)
            return response

        response = await call_next(request)
        if is_public_path(request.url.path):
            apply_public_cors(response)
        return response

    @api.on_event("startup")
    async def startup() -> None:
        init_db(admin_password_hash=hash_password("admin123"))

    api.include_router(dev_router, prefix=APPSTORE_API_PREFIX)
    api.include_router(store_router, prefix=APPSTORE_API_PREFIX)

    if FRONTEND_UI_DIST_DIR.exists():
        api.mount("/", StaticFiles(directory=str(FRONTEND_UI_DIST_DIR), html=True), name="static")

    return api


app = create_app()
