# Caddy 部署（前端托管 + 后端代理）

公网部署得用caddy做前端托管和后端反代理，保持外部暴露接口固定。

caddy比nginx使用起来更简单，尤其是对于公网域名的服务器可以自动申请https证书，更简单。

本方案用于 `aivudaAppStore`：

- Caddy 托管前端静态文件（`frontend_dev/dist`）
- Caddy 反向代理后端 API（`127.0.0.1:9001`）
- 对免鉴权公开接口开启 CORS（仅 `/aivuda_app_store/store*`、`/aivuda_app_store/files*`）
- 同时支持 HTTP 与 HTTPS

## 1. 安装 Caddy

### 1.1 Ubuntu / Debian（推荐）

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

### 1.2 macOS（Homebrew）

```bash
brew install caddy
```

### 1.3 验证安装

```bash
caddy version
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

`apt` 安装后的 Caddy 默认由 `systemd` 管理，默认是开机自启动。

### 4.1 推荐：一条命令自动设置绝对路径并部署

在仓库根目录（`aivudaAppStore/`）执行：

```bash
sudo ./scripts/install_caddy_systemd.sh
```

脚本会自动完成：

- 检测仓库绝对路径并写入 `root * <绝对路径>/frontend_dev/dist`
- 生成并安装 `/etc/caddy/Caddyfile`
- 校验配置
- `systemctl enable --now caddy`
- `systemctl reload caddy`（失败则自动 `restart`）

如果你的前端构建目录不是默认路径，可传参数：

```bash
./scripts/install_caddy_systemd.sh /your/absolute/path/to/frontend_dev/dist
```

### 4.2 手动方式：部署 Caddyfile 到系统路径

在仓库根目录（`aivudaAppStore/`）执行：

```bash
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

### 4.3 使用 systemd 启动与重载

```bash
sudo systemctl enable --now caddy
sudo systemctl restart caddy
sudo systemctl status caddy --no-pager
```

后续修改配置后建议使用热重载：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

默认监听：

- HTTP: `http://<host>:80`
- HTTPS: `https://<host>:443` （局域网下需要用户浏览器安装后端服务器上的caddy证书才能打开）

使用：

- 浏览器点击 http://host 或者 https://host, <host>替换成它的IP，本机可以用 http://127.0.0.1 或者 https://127.0.0.1

### 4.4 重要：静态目录请使用绝对路径

`systemd` 启动时的工作目录不是仓库目录，`root * ./frontend_dev/dist` 这类相对路径会失效。

请把 `/etc/caddy/Caddyfile` 里的 `root` 改成真实绝对路径，例如：

```caddy
root * /home/your-user/aivuda/aivudaAppStore/frontend_dev/dist
```

并确保 `caddy` 服务用户对该目录有读取权限。

说明：

- `Caddyfile` 中使用 `tls internal` 生成本地内部证书，适合内网/开发环境。
- 若用于公网正式域名，可改为 `https://your-domain.com` 站点块并移除 `tls internal`，由 Caddy 自动申请可信证书。

## 5. CORS 说明

Caddy 只对以下公开下载/商店接口增加跨域响应头：

- `GET/OPTIONS /aivuda_app_store/store*`
- `GET/OPTIONS /aivuda_app_store/files*`

这可满足跨域读取应用商店列表、详情与安装包下载地址。

其余接口（例如 `/aivuda_app_store/dev/*`）不在 Caddy 层开放跨域。

## 6. 路由行为

- `/aivuda_app_store/*` -> 反代到 `127.0.0.1:9001`
- 其他路径 -> 前端静态资源，SPA 回退到 `/index.html`
