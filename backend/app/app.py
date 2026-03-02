from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.dev import router as dev_router
from app.api.store import router as store_router
from app.core.settings import FILES_DIR, FRONTEND_DEV_UI_DIST_DIR, ensure_storage_dirs
from app.services.auth import hash_password
from app.services.db import init_db


def create_app() -> FastAPI:
    ensure_storage_dirs()

    api = FastAPI(title="Aivuda App Store", version="0.3.0")
    api.add_middleware(
        CORSMiddleware, # 允许跨域浏览器前端访问，危险
        # allow_origins=["*"], # dangerous in production, should be restricted to specific origins
        allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+", # 前端的地址， Only for npm run dev frontend development. 生产环境应去掉，要么用nginx代理使得前后端同域，要么nginx为后端设置合适的 CORS 头（前后端不在一个主机时，后端必须允许CORS了）
        allow_credentials=False, # if true, also need to specify allowed origins and cannot be "*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.on_event("startup")
    async def startup() -> None:
        init_db(admin_password_hash=hash_password("admin123"))

    api.include_router(dev_router)
    api.include_router(store_router)

    api.mount("/files", StaticFiles(directory=FILES_DIR), name="files") # for sample package file access, in production should use a proper static file server with better performance and security

    if FRONTEND_DEV_UI_DIST_DIR.exists():
        # 开发环境提供静态文件(使得访问后端ip:port也能打开前端网页)，生产环境建议使用专门的静态文件服务器（如 nginx）来提供 UI 文件
        api.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DEV_UI_DIST_DIR), html=True),
            name="static",
        )

    return api


app = create_app()
