# Backend

后端代码现已作为 `aivudaappstore` Python 包的一部分发布，实际入口位于：

- `aivudaappstore.backend.main:app`

接口前缀保持不变：

- 开发者管理接口：`/aivuda_app_store/dev/*`
- 公开商店接口：`/aivuda_app_store/store/*`

MCP 默认连接 Caddy 回环 HTTP 入口 `http://127.0.0.1:8540/aivuda_app_store`，
由该入口提供 API 代理和 `/files/*` 静态文件下载。

本地开发、安装、构建与服务管理请优先参考仓库根目录：

- [README.md](../README.md)
- [README_dev.md](../README_dev.md)

补充文档：

- [app-package-spec.md](../aivudaappstore/resources/samples/aivuda-app-pkg-example/README.md)
- [api-usage.md](api-usage.md)
- [mcp.md](mcp.md)
- [deploy-caddy.md](deploy-caddy.md)
