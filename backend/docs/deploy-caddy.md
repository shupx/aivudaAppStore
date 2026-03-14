# Caddy 部署（前端托管 + 后端代理）

公网部署得用caddy做前端托管和后端反代理，保持外部暴露接口固定。

caddy比nginx使用起来更简单，尤其是对于公网域名的服务器可以自动申请https证书，更简单。

本方案用于 `aivudaAppStore`：

- Caddy 托管前端静态文件（`frontend_dev/dist`）
- Caddy 反向代理后端 API（`127.0.0.1:9001`）
- HTTP `8580` 仅反代 `/store*` 到后端公开商店接口，并把其余路径作为 `backend/data/files/apps` 文件服务
- HTTPS `8543` 保持原有 `appstore_site` 路由（前端静态托管 + `/aivuda_app_store*` 反代）

## 1. 安装 Caddy（无 sudo）

如果你没有 sudo 权限，推荐使用用户目录安装二进制。

> 当前仓库.tools目录下已经下载caddy amd64二进制文件，无需再下载，下文只展示下载方法。

### 1.0 推荐：一键安装脚本

在仓库根目录执行：

```bash
bash scripts/install_caddy_local.sh
```

安装完成后可执行：`./.tools/caddy/caddy version`

### 1.1 Linux（用户目录安装）

在仓库根目录执行：

```bash
mkdir -p .tools/caddy
cd .tools/caddy
curl -L -o caddy.tar.gz https://github.com/caddyserver/caddy/releases/latest/download/caddy_2_linux_amd64.tar.gz
tar -xzf caddy.tar.gz
chmod +x caddy
cd ../../
```

后续可直接使用：`./.tools/caddy/caddy`

### 1.2 macOS（无 sudo）

若本机已配置用户态 Homebrew，可直接：

```bash
brew install caddy
```

若不具备 Homebrew 权限，可参考 Linux 方式下载对应 macOS 二进制到用户目录。

### 1.3 验证安装

```bash
./.tools/caddy/caddy version
```

## 2. 构建前端

在仓库根目录执行：

```bash
cd frontend_dev
npm install
npm run build
```

构建产物默认在 `frontend_dev/dist`。

## 3. 启动后端

```bash
cd aivudaAppStore/
PYTHONPATH=backend gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app -b 127.0.0.1:9001
```

## 4. 启动 Caddy

在仓库根目录（`aivudaAppStore/`）执行：

```bash
./.tools/caddy/caddy run --config Caddyfile
```

可选：先校验配置再启动。

```bash
./.tools/caddy/caddy validate --config Caddyfile --adapter caddyfile
```

默认监听：

- HTTP: `http://<host>:8580`（仅 `/store*` 走后端，其他路径走 `backend/data/files/apps` 文件服务）
- HTTPS: `https://<host>:8543` （当前 `tls internal`，浏览器可能提示证书不受信任）

使用：

- 浏览器打开 `https://<host>:8543`，`<host>` 替换成安装脚本设置的公网 IP/域名；本机可用 `https://127.0.0.1:8543`

### 4.1 重要：在仓库根目录启动

当前 `Caddyfile` 使用相对路径：`root * ./frontend_dev/dist`。

因此请确保在 `aivudaAppStore/` 目录下执行 `./.tools/caddy/caddy run --config Caddyfile`，否则可能找不到静态资源目录。

说明：

- `Caddyfile` 中使用 `tls internal` 生成本地内部证书，适合内网/开发环境。
- 若用于公网正式域名，可改为 `https://your-domain.com` 站点块并移除 `tls internal`，由 Caddy 自动申请可信证书。

## 4.2 用户自启动（backend + caddy 一起）

如果是开发模式，要先先编译生成前端静态文件：

```bash
cd frontend_dev
npm run build
```

然后在仓库根目录执行设置开机自启动脚本：

```bash
bash scripts/install_user_services.sh
```

脚本会要求输入两个 HTTPS 地址：

- 公网 IP/域名：`APPSTORE_PUBLIC_HTTPS_HOST`
- 内网 IP/域名：`APPSTORE_PRIVATE_HTTPS_HOST`

输入内网地址时，脚本会先列出当前服务器检测到的本机 IPv4 地址供选择，也可以手工输入。

并写入 `aivuda-appstore.service` 的环境变量：

- `APPSTORE_PUBLIC_HTTPS_HOST`
- `APPSTORE_PRIVATE_HTTPS_HOST`

`Caddyfile` 会读取这两个环境变量来绑定 HTTPS 站点。

`8580/8543` 均为非特权端口，Caddy 无需额外 `setcap` 授权。

执行前请先停止你手工启动的后端（例如 `uvicorn --reload`），避免占用 `127.0.0.1:9001` 导致 service 启动失败。

该脚本会：

- 创建单个 `systemd --user` 服务：
	- `aivuda-appstore.service`（同时启动 backend + caddy）
- 执行 `systemctl --user enable --now ...`，加入用户自启动并立即启动。

常用命令：

```bash
systemctl --user status aivuda-appstore.service
systemctl --user restart aivuda-appstore.service
journalctl --user -u aivuda-appstore.service -f
```

脚本还会自动执行“未登录也自启动”配置（需管理员权限）：

```bash
sudo loginctl enable-linger $USER
```

设置好后可直接访问 `https://<公网IP或域名>:8543` 或 `https://<内网IP或域名>:8543`。

如需修改公网/内网地址，可重新执行安装脚本并输入新的 `APPSTORE_PUBLIC_HTTPS_HOST` / `APPSTORE_PRIVATE_HTTPS_HOST`，然后重启服务：

```bash
systemctl --user restart aivuda-appstore.service
```

## 5. CORS 说明

当前 CORS 由 FastAPI 处理（`backend/app/app.py` 中间件），Caddy 不再设置 CORS 响应头。

FastAPI 仅对公开接口开放跨域：

- `/aivuda_app_store/store*`

`/aivuda_app_store/dev/*` 等鉴权接口不开放跨域。

## 6. 路由行为

- HTTP `:8580`
	- `/store*` -> rewrite 到 `/aivuda_app_store/store*` 后反代到 `127.0.0.1:9001`
	- 其他路径 -> `backend/data/files/apps` 文件服务（`file_server`）
- HTTPS `:8543`
	- `/aivuda_app_store*` -> 反代到 `127.0.0.1:9001`
	- 其他路径 -> 前端静态资源，SPA 回退到 `/index.html`
