# aivudaAppStore

aivudaAppStore 现已拆分为独立的后端与前端目录。

## 目录

- `backend/`: python FastAPI 后端（开发者管理 + 公开商店接口）
- `frontend_dev/`: 开发者管理前端（Vue 3 + Vite）

## 快速启动

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

打开 `http://127.0.0.1:5174`。

如果后端不在同域，登录页填写 `Backend URL`（例如 `http://127.0.0.1:9001`）。

## 默认开发者账号

- 用户名: `admin`
- 密码: `admin123`

## 安装包说明（manifest.yaml）

- AppStore 已切换为 aivudaOS 对齐的 `manifest.yaml` 规范。
- 上传新应用与上传/编辑版本时，会先自动解析包内 manifest 回填表单。
- 提交后，后端会使用表单内容重新生成并覆盖安装包中的 `manifest.yaml`。
