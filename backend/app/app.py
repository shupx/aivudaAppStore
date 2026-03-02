from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.dev import router as dev_router
from app.api.store import router as store_router
from app.core.settings import FILES_DIR, ensure_storage_dirs
from app.services.auth import hash_password
from app.services.db import init_db


def create_app() -> FastAPI:
    ensure_storage_dirs()

    api = FastAPI(title="Aivuda App Store", version="0.3.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.on_event("startup")
    async def startup() -> None:
        init_db(admin_password_hash=hash_password("admin123"))

    api.include_router(dev_router)
    api.include_router(store_router)
    api.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

    return api


app = create_app()
