# Aivuda AppStore 开发说明

## 目录结构

- `aivudaappstore/backend/`：Python 后端入口
- `aivudaappstore/backend/app/`：FastAPI 路由、服务、配置
- `aivudaappstore/resources/ui/`：前端源码与构建产物
- `aivudaappstore/resources/caddy/`：Caddy 模板
- `aivudaappstore/resources/scripts/`：CLI 调用的运维脚本
- `aivudaappstore/resources/samples/`：只读示例应用源码

示例包包含可复用的 `scripts/docker_helpers.sh`，通过“下载示例包”或 MCP
`store_sample_package` 分发。开发新 App 时可直接复制，无需平台源码。默认示例
不启用 Docker；接口、路径/环境要求和停止清理限制见
[示例包说明](aivudaappstore/resources/samples/aivuda-app-pkg-example/README.md)。

## 运行时工作区

运行时默认写入：

- `$HOME/aivudaAppStore_ws/data/repo.db`
- `$HOME/aivudaAppStore_ws/data/files/...`
- `$HOME/aivudaAppStore_ws/data/tmp/...`
- `$HOME/aivudaAppStore_ws/config/Caddyfile`
- `$HOME/aivudaAppStore_ws/.tools/caddy/caddy`
- `$HOME/aivudaAppStore_ws/samples/*.zip`

可通过环境变量覆盖：

```bash
export AIVUDAAPPSTORE_WS_ROOT=/your/custom/path
```

包目录必须保持只读，不允许把数据库、上传文件、`.tools`、示例 zip 写回源码树或 site-packages。

## Python 3.8 约束

- 后端代码必须兼容 `Python 3.8`
- 使用 `typing.Dict/List/Set/Tuple/Optional/Union`
- 不使用 `X | None`、`dict[str, Any]` 这类新语法

## 本地开发

安装依赖：

```bash
python3 -m pip install -r requirements.txt
bash aivudaappstore/resources/scripts/_download_caddy.sh
cd aivudaappstore/resources/ui
npm install
```

开发模式启动（以下环境变量也可以不设置，下方展示默认值）：

```bash
AIVUDAAPPSTORE_WS_ROOT="$HOME/aivudaAppStore_ws" \
APPSTORE_PUBLIC_HTTPS_HOST=127.0.0.1 \
APPSTORE_PRIVATE_HTTPS_HOST=127.0.0.1 \
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh --dev
```

如果当前 shell 已激活 `conda` 环境，脚本会优先使用该环境的 `python`。

生产式本地启动：

```bash
cd aivudaappstore/resources/ui
npm run build
cd ../../..
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh
```

如果执行安装脚本时已经激活 `conda` 环境，生成的 `aivudaappstore.service` 会固定使用该环境对应的 Python 解释器。

## 打包与发布

构建：

```bash
AIVUDAAPPSTORE_BUILD_SEQ=01 python -m build
```

发布脚本：

```bash
AIVUDAAPPSTORE_BUILD_SEQ=01 ./publish_aivudaappstore_pypi.sh --skip-upload
```

CI 流程包含：

- 前端构建
- wheel + sdist 构建
- wheel/sdist 内容校验
- Python 3.8 smoke test

## 兼容性说明

- HTTP API 前缀保持 `/aivuda_app_store`
- 默认管理员账号保持：
  - 用户名：`admin`
  - 密码：`admin123`

- 如果忘记 `admin` 密码，可以在本机执行：
  - `aivudaappstore reset-admin-password`
  - 或非交互方式：`aivudaappstore reset-admin-password --password NEW_PASSWORD`

## 更多架构细节

## 独立 MCP 服务

AppStore 提供独立的 Streamable HTTP MCP 服务，默认地址为
`http://127.0.0.1:28795/mcp`：

```bash
python3 -m aivudaappstore.mcp_server --host 127.0.0.1 --port 28795
# 或安装后：aivudaappstore-mcp
```

根据后端路由生成全部 33 个 HTTP 操作（含 HEAD），支持登录、注册、上传、
版本发布与删除、成员管理、数据导入导出、公开下载和证书下载。
原有 4 个工具名保留，其余工具名采用路由函数名。
完成 `aivudaappstore install` 后可直接运行 `aivudaappstore-mcp` 或上述 Python 命令。
`AIVUDAAPPSTORE_MCP_BASE_URL` 默认 `http://127.0.0.1:8540/aivuda_app_store`，
通过 Caddy 回环 HTTP 入口调用 API 和下载应用包；此入口与 HTTPS 管理入口使用相同路由。
受保护工具默认用 `admin / admin123` 自动登录并缓存临时 token，失效后重登重试一次；公开查询无需登录。
默认登录失败才需提供当前账号密码；可设置 `AIVUDAAPPSTORE_MCP_USERNAME`/`AIVUDAAPPSTORE_MCP_PASSWORD`，
或调用 `dev_login` 后逐次传入 `authorization: "Bearer <token>"`。
`AIVUDAAPPSTORE_MCP_TOKEN` 是可选的显式覆盖，后端仍执行正常权限检查。
MCP 入站认证使用独立的 `AIVUDAAPPSTORE_MCP_ACCESS_TOKEN`。
详细配置和文件调用见 [docs/mcp.md](docs/mcp.md)。
