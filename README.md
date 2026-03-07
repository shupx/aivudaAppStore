# aivudaAppStore

aivudaAppStore 现已拆分为独立的后端与前端目录。

## 目录

- `backend/`: python FastAPI 后端（开发者管理 + 公开商店接口）
- `frontend_dev/`: 开发者管理前端（Vue 3 + Vite）

## 开发环境快速启动

1. 启动后端

```bash
cd backend
python3 -m pip install --user -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 9001 --reload
```

2. 启动前端（应用开发者界面）

```bash
cd frontend_dev
npm install
npm run dev
```

> 开发环境由 `vite.config.js` 代理 `/aivuda_app_store` 到 `http://127.0.0.1:9001`，无需手工输入 Backend URL。

打开 `http://127.0.0.1:5174`进入前端网页

如果还没安装node和npm，建议手动安装24版的(仅开发需要)：

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo bash -
sudo apt remove libnode-dev nodejs #删除旧的nodejs
sudo apt install -y nodejs
node -v # v24.14.0
npm -v  # 11.9.0
```


## 生产部署（本地快速）

简单一点的话，直接启动后端（fastapi后端也托管了前端静态文件，虽然性能差点），没有https，只适合本地启动：

```bash
cd aivudaAppStore/
PYTHONPATH=backend gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app -b 127.0.0.1:9001
```

然后浏览器输入http://127.0.0.1:9001，前后端都在这。


## 生产部署Caddy 启动（前端托管 + 后端代理）

默认仅 HTTPS `443`、前端静态托管、后端反代，见：

[backend/docs/deploy-caddy.md](backend/docs/deploy-caddy.md)

在仓库根目录可直接启动：

```bash
bash scripts/install_user_services.sh
```

上面脚本会在安装时要求输入 HTTPS 公网 IP/域名（`APPSTORE_HTTPS_HOST`），并安装启用单个用户服务 `aivuda-appstore.service`（同时启动 backend + caddy）。

由于 `443` 是特权端口，脚本会调用一次：

```bash
sudo setcap cap_net_bind_service=+ep ./.tools/caddy/caddy
```

这一步需要 sudo 权限。

```bash
./.tools/caddy/caddy run --config Caddyfile
```

安装脚本也会自动执行以下命令（需要 sudo）：

```bash
sudo loginctl enable-linger $USER
```


## 安装包说明（manifest.yaml）

- AppStore 已切换为 aivudaOS 对齐的 `manifest.yaml` 规范。
- 上传新应用与上传/编辑版本时，会先自动解析包内 manifest 回填表单。
- 提交后，后端会使用表单内容重新生成并覆盖安装包中的 `manifest.yaml`。

## 默认开发者账号

- 用户名: `admin`
- 密码: `admin123`