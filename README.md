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
python3 -m uvicorn main:app --host 0.0.0.0 --port 9001 --reload --workers 4
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
