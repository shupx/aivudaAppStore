# Aivuda AppStore 开发说明

## 目录结构

- `aivudaappstore/backend/`：Python 后端入口
- `aivudaappstore/backend/app/`：FastAPI 路由、服务、配置
- `aivudaappstore/resources/ui/`：前端源码与构建产物
- `aivudaappstore/resources/caddy/`：Caddy 模板
- `aivudaappstore/resources/scripts/`：CLI 调用的运维脚本
- `aivudaappstore/resources/samples/`：只读示例应用源码

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

生产式本地启动：

```bash
cd aivudaappstore/resources/ui
npm run build
cd ../../..
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh
```

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

## 更多架构细节

