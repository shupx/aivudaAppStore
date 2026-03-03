# Backend

FastAPI 后端，提供：

- 开发者管理接口：`/aivuda_app_store/dev/*`
- 公开商店接口：`/aivuda_app_store/store/*`
- 文件下载：`/aivuda_app_store/files/*`

## 启动

```bash
python3 -m pip install --user -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 9001 --reload
```

## 默认账号

- 用户名: `admin`
- 密码: `admin123`

## 安装包规范

见 `backend/docs/app-package-spec.md`。

## API 使用说明

见 `backend/docs/api-usage.md`。

上传与编辑版本时：

- 先解析包内 `manifest.yaml` 回填表单
- 提交时统一用表单生成 `manifest.yaml` 并覆盖包内 manifest
- 新应用上传流程中，解析阶段若缺失 `manifest.yaml` 会直接返回 400
- 解析接口会返回包内文件树（最多 3 层）用于前端展示
- 新应用提交阶段仅强制校验 `app_id`、`name`、`description`、`version`

解析接口：`POST /aivuda_app_store/dev/apps/manifest/parse-package`

示例包下载：`GET /aivuda_app_store/store/sample-package`（文件名：`aivuda-app-pkg-example.zip`）。

## 示例包子模块

`backend/samples/aivuda-app-pkg-example` 已改为 git 子模块，指向：

- `git@gitee.com:aivuda_app_pkgs/aivuda-app-pkg-example.git`

首次克隆或拉取后请执行：

```bash
git submodule update --init --recursive
```
