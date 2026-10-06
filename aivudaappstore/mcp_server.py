"""Standalone Streamable HTTP MCP facade over every AppStore API route."""
from __future__ import annotations

from aivudaappstore.mcp_runtime import APIClient as BaseAPIClient, OpenAPIServer, serve


class APIClient(BaseAPIClient):
    def __init__(self, base_url=None, token=None, opener=None):
        super().__init__("AIVUDAAPPSTORE", "http://127.0.0.1:8540/aivuda_app_store", "bearer", base_url, token, opener)


def api_schema():
    from fastapi import FastAPI
    from aivudaappstore.backend.app.api import dev, store

    app = FastAPI()
    for router in (dev.router, store.router):
        app.include_router(router)
    return app


class MCPServer(OpenAPIServer):
    def __init__(self, client=None):
        super().__init__("aivudaappstore-mcp", client or APIClient(), api_schema(), {
            ("GET", "/store/index"): "store_index",
            ("GET", "/store/apps/{app_id}"): "store_app_detail",
            ("GET", "/store/apps/{app_id}/versions/{version}/download-url"): "store_download_metadata",
            ("GET", "/dev/apps/manageable"): "developer_manageable_apps",
        })


def main():
    serve(MCPServer(), "AIVUDAAPPSTORE", 28795)


if __name__ == "__main__":
    main()
