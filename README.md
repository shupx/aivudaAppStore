# aivudaAppStore

aivudaAppStore 现已拆分为独立的后端与前端目录。

支持本地部署和服务器部署。一个已经部署在阿里云服务器上的例子：https://123.56.143.44/

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

先编译生成前端静态文件：

```bash
cd frontend_dev
npm run build
```

在仓库根目录可直接启动安装自启动脚本：

```bash
bash scripts/install_user_services.sh
```

上面脚本会在安装时要求输入两个 HTTPS 地址：

- 公网 IP/域名：`APPSTORE_PUBLIC_HTTPS_HOST`
- 内网 IP/域名：`APPSTORE_PRIVATE_HTTPS_HOST`

输入内网地址时，脚本会先列出当前服务器检测到的本机 IPv4 地址供选择，也可以手工输入。

并写入 `aivuda-appstore.service` 的环境变量：

- `APPSTORE_PUBLIC_HTTPS_HOST`
- `APPSTORE_PRIVATE_HTTPS_HOST`

`Caddyfile` 会读取这两个环境变量来绑定 HTTPS 站点。

设置好后可直接访问 `https://<公网IP或域名>` 或 `https://<内网IP或域名>`。


## 安装包说明（manifest.yaml）

- AppStore 已切换为 aivudaOS 对齐的 `manifest.yaml` 规范。
- 上传新应用与上传/编辑版本时，会先自动解析包内 manifest 回填表单。
- 提交后，后端会使用表单内容重新生成并覆盖安装包中的 `manifest.yaml`。

## 默认开发者账号

- 用户名: `admin`
- 密码: `admin123`