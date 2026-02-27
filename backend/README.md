# Backend

FastAPI 后端，提供：

- 开发者管理接口：`/dev/*`
- 公开商店接口：`/store/*`
- 文件下载：`/files/*`

## 启动

```bash
python3 -m pip install --user -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 9001 --reload --workers 4
```

## 默认账号

- 用户名: `admin`
- 密码: `admin123`

## 安装包规范

见 `backend/docs/app-package-spec.md`。

示例包下载：`GET /store/sample-package`。
