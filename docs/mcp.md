# Streamable HTTP MCP

完成 `aivudaappstore install` 后，直接运行 `aivudaappstore-mcp` 或
`python3 -m aivudaappstore.mcp_server` 启动 MCP；默认通过 Caddy 入口
`http://127.0.0.1:8540/aivuda_app_store` 调用 API，客户端连接 `http://127.0.0.1:28795/mcp`。

## 传输与调用约定

客户端连接 `http://127.0.0.1:28795/mcp`。这是无会话 Streamable HTTP：
POST 可返回 JSON；通知返回 202；GET 和 DELETE 返回 405；不分配
`Mcp-Session-Id`。支持协议版本 2025-06-18、2025-03-26 和 2024-11-05。
HTTP POST 的 Accept 必须包含 `application/json, text/event-stream`，
Content-Type 为 `application/json`。不需要单独的 SSE 连接。

工具从后端路由生成，名称为路由函数名（原有工具名保留）。`tools/list`
提供参数类型、必填项及 API 方法/路径；JSON 请求体放在 `body` 参数中，
路径、query、header、form 参数使用各自名称。使用 `tools/call` 调用。
所有写操作仍通过后端认证及权限检查，不绕过业务服务。

| 环境变量 | 用途 |
|---|---|
| `AIVUDAAPPSTORE_MCP_BASE_URL` | Caddy API 和文件入口，默认 `http://127.0.0.1:8540/aivuda_app_store`，必须包含服务前缀 |
| `AIVUDAAPPSTORE_MCP_TOKEN` | 默认后端 API token |
| `AIVUDAAPPSTORE_MCP_HOST` | MCP 监听地址，默认 127.0.0.1 |
| `AIVUDAAPPSTORE_MCP_PORT` | MCP 监听端口，默认 28795 |
| `AIVUDAAPPSTORE_MCP_ACCESS_TOKEN` | MCP 入站 Bearer token，与后端 token 独立 |
| `AIVUDAAPPSTORE_MCP_ALLOWED_HOSTS` | 可接受的 Host 主机名，逗号分隔 |
| `AIVUDAAPPSTORE_MCP_ALLOWED_ORIGINS` | 额外允许的 Origin，逗号分隔，默认仅同源 |
| `AIVUDAAPPSTORE_MCP_MAX_BYTES` | HTTP 请求、上传、后端响应和事件读取的字节上限，默认 64 MiB |

绑定非回环地址必须设置 MCP_ACCESS_TOKEN。远程使用应通过 HTTPS 反向代理，
并根据代理入口设置允许的 Host/Origin。API token 可以逐次覆盖；登录返回值
不会保存为整个 MCP 服务的默认账号。上游错误以 MCP `isError` 返回。

文件上传字段使用以下对象；表单中的 JSON 字符串（例如 manifest_json）
仍按原 API 传入字符串：

```json
{
  "package_zip": {
    "filename": "app.zip",
    "content_type": "application/zip",
    "content_base64": "UEsDB..."
  }
}
```

文件字段名称以工具 schema 为准。下载返回原始 `filename`、`content_base64`、`content_type`、
`content_disposition` 和 `size`；HEAD 返回状态和响应头。MCP 不读取调用者
指定的服务器本地路径。超限文件使用原 HTTP API，或提高字节上限；base64
以及 JSON/multipart 包装也占用字节额度。

目前提供全部 33 个 HTTP 操作对应的工具，包括公开索引/详情/manifest/下载、
登录注册与密码管理、版本上传修改/发布撤回删除、应用删除、成员和管理员管理、
数据导入导出、示例包与证书下载。

`dev_login` 接收顶层 username、password 表单字段。之后每次调用传入
`authorization: "Bearer <token>"`，或预设 MCP_TOKEN（仅填写 token 本身）。
原有 `store_index`、`store_app_detail`、`store_download_metadata`、
`developer_manageable_apps` 名称保留；`store_download_file` 可直接下载包内容。
`dev_inspect_data_import` 和 `dev_apply_data_import` 的上传字段名为 data_zip。

## 完整工具清单

目前共 33 个工具，按用途分组如下。具体参数、类型和必填项以 `tools/list`
返回的 `inputSchema` 为准；新增后端路由后，工具列表会随之更新。

| 用途 | Tools |
|---|---|
| 登录与账号 | `dev_login`、`dev_register`、`dev_me`、`dev_change_password`、`dev_reset_password`、`dev_list_users` |
| 数据导入导出 | `dev_exportable_apps`、`dev_export_data`、`dev_inspect_data_import`、`dev_apply_data_import` |
| 包上传与解析 | `dev_upload_package`、`dev_parse_package_manifest` |
| 版本管理 | `dev_upload_version`、`dev_modify_version`、`dev_publish_version`、`dev_unpublish_version`、`dev_delete_version` |
| 应用管理 | `developer_manageable_apps`、`dev_delete_app` |
| 成员与管理员 | `dev_list_app_members`、`dev_add_app_member`、`dev_remove_app_member`、`dev_transfer_app_admin`、`dev_batch_update_app_memberships` |
| 商店查询 | `store_index`、`store_version`、`store_app_detail`、`store_manifest` |
| 包下载 | `store_download_metadata`、`store_download_file`、`store_sample_package` |
| 证书 | `store_caddy_local_ca_root`、`store_caddy_local_ca_root_head` |

## 验证

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p test_mcp_server.py -v
```
