import json
import unittest

from aivudaappstore.mcp_server import MCPServer


class FakeClient:
    token = "developer-token"

    def __init__(self):
        self.calls = []

    def request(self, path, method="GET"):
        self.calls.append((path, method))
        return {"ok": True, "path": path}


class MCPServerTests(unittest.TestCase):
    def test_tools_list_is_protocol_response(self):
        response = MCPServer().handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(response["jsonrpc"], "2.0")
        names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertEqual(names, ["store_index", "store_app_detail", "store_download_metadata", "developer_manageable_apps"])

    def test_store_index_calls_public_api(self):
        client = FakeClient()
        result = MCPServer(client).handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "store_index", "arguments": {}}})
        self.assertFalse(result["result"].get("isError", False))
        self.assertEqual(client.calls, [("/store/index", "GET")])
        self.assertTrue(json.loads(result["result"]["content"][0]["text"])["ok"])

    def test_developer_operation_requires_token(self):
        client = FakeClient()
        client.token = ""
        with self.assertRaises(ValueError):
            MCPServer(client).call_tool("developer_manageable_apps", {})


if __name__ == "__main__":
    unittest.main()
