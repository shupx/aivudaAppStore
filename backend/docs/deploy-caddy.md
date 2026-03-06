# Caddy 部署（前端托管 + 后端代理）

公网部署得用caddy做前端托管和后端反代理，保持外部暴露接口固定。

caddy比nginx使用起来更简单，尤其是对于公网域名的服务器可以自动申请https证书，更简单。

本方案用于 `aivudaAppStore`：

- Caddy 托管前端静态文件（`frontend_dev/dist`）
- Caddy 反向代理后端 API（`127.0.0.1:9001`）
- 同时支持 HTTP 与 HTTPS

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
./.tools/caddy/caddy run --config Caddyfile.nosudo
```

可选：先校验配置再启动。

```bash
./.tools/caddy/caddy validate --config Caddyfile.nosudo --adapter caddyfile
```

默认监听：

- HTTP: `http://<host>:8080`
- HTTPS: `https://<host>:8443` （局域网下需要用户浏览器安装后端服务器上的caddy证书才能无警告地打开）

使用：

- 浏览器点击 http://host:8080 或者 https://host:8443，`<host>` 替换成它的IP；本机可用 http://127.0.0.1:8080 或 https://127.0.0.1:8443

### 4.1 重要：在仓库根目录启动

当前 `Caddyfile.nosudo` 使用相对路径：`root * ./frontend_dev/dist`。

因此请确保在 `aivudaAppStore/` 目录下执行 `./.tools/caddy/caddy run --config Caddyfile.nosudo`，否则可能找不到静态资源目录。

说明：

- `Caddyfile` 中使用 `tls internal` 生成本地内部证书，适合内网/开发环境。
- 若用于公网正式域名，可改为 `https://your-domain.com` 站点块并移除 `tls internal`，由 Caddy 自动申请可信证书。

## 4.2 用户自启动（backend + caddy 一起）

在仓库根目录执行：

```bash
bash scripts/install_user_services.sh
```

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

若希望“未登录也自启动”，需管理员执行：

```bash
sudo loginctl enable-linger $USER
```

设置好后开机登录账户后即可登录 http://127.0.0.1:8080，https://127.0.0.1:8443 或者 http://本机IP:8080 。

https目前设置了127.0.0.1，如果要改成实际IP或者域名，需要去手动修改Caddyfile.nosudo文件里的`https://127.0.0.1:8443`，然后重启服务`systemctl --user restart aivuda-appstore.service`

## 5. CORS 说明

当前 CORS 由 FastAPI 处理（`backend/app/app.py` 中间件），Caddy 不再设置 CORS 响应头。

FastAPI 仅对公开接口开放跨域：

- `/aivuda_app_store/store*`

`/aivuda_app_store/dev/*` 等鉴权接口不开放跨域。

## 6. 路由行为

- `/aivuda_app_store/*` -> 反代到 `127.0.0.1:9001`
- 其他路径 -> 前端静态资源，SPA 回退到 `/index.html`
