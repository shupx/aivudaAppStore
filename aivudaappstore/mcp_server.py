"""Small stdlib MCP server for Aivuda AppStore.

Transport: line-delimited JSON-RPC 2.0 over stdin/stdout.  Calls stay inside
the AppStore public HTTP API.  Developer access is limited to the read-only
manageable-apps endpoint and requires an explicit bearer token.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen


class APIClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None,
                 opener: Optional[Callable[..., Any]] = None) -> None:
        self.base_url = (base_url or os.environ.get("AIVUDAAPPSTORE_MCP_BASE_URL", "http://127.0.0.1:8000/aivuda_app_store")).rstrip("/")
        self.token = token if token is not None else os.environ.get("AIVUDAAPPSTORE_MCP_TOKEN", "")
        self.opener = opener or urlopen

    def request(self, path: str, method: str = "GET") -> Any:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = Request(self.base_url + path, method=method, headers=headers)
        with self.opener(req, timeout=30) as response:
            raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


TOOLS = [
    {"name": "store_index", "description": "List public apps in the store.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "store_app_detail", "description": "Read public details for a store app.", "inputSchema": {"type": "object", "properties": {"app_id": {"type": "string"}}, "required": ["app_id"]}},
    {"name": "store_download_metadata", "description": "Read a version's download metadata (not the package bytes).", "inputSchema": {"type": "object", "properties": {"app_id": {"type": "string"}, "version": {"type": "string"}}, "required": ["app_id", "version"]}},
    {"name": "developer_manageable_apps", "description": "List apps manageable by the authenticated developer; requires AIVUDAAPPSTORE_MCP_TOKEN.", "inputSchema": {"type": "object", "properties": {}}},
]


class MCPServer:
    def __init__(self, client: Optional[APIClient] = None) -> None:
        self.client = client or APIClient()

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name == "store_index":
            return self.client.request("/store/index")
        if name == "store_app_detail":
            return self.client.request("/store/apps/{0}".format(quote(str(arguments["app_id"]), safe="")))
        if name == "store_download_metadata":
            return self.client.request("/store/apps/{0}/versions/{1}/download-url".format(quote(str(arguments["app_id"]), safe=""), quote(str(arguments["version"]), safe="")))
        if name == "developer_manageable_apps":
            if not self.client.token:
                raise ValueError("AIVUDAAPPSTORE_MCP_TOKEN is required for developer operations")
            return self.client.request("/dev/apps/manageable")
        raise ValueError("Unknown tool: {0}".format(name))

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        request_id = message.get("id")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "aivudaappstore-mcp", "version": "1.0"}}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
        if method == "tools/call":
            params = message.get("params") or {}
            try:
                result = self.call_tool(str(params.get("name")), params.get("arguments") or {})
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}
            except Exception as exc:
                return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": str(exc)}]}}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}


def main() -> None:
    server = MCPServer()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = server.handle(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
