# Aivuda AppStore Backend API 使用说明

本文档说明 `aivudaAppStore/backend` 提供的 API、鉴权方式和典型调用流程。

## 1. 基础信息

- 默认服务地址：`http://127.0.0.1:9001`
- API 前缀：`/aivuda_app_store`
- 完整 API 基址：`http://127.0.0.1:9001/aivuda_app_store`

接口分两类：

- 开发者接口（需要 Bearer Token）：`/dev/*`
- 公开商店接口（无需 token）：`/store/*`

## 2. 鉴权（仅 dev 接口）

### 2.1 登录

- **POST** `/aivuda_app_store/dev/auth/login`
- `Content-Type: multipart/form-data`
- 表单字段：
  - `username`
  - `password`

示例：

```bash
curl -X POST "http://127.0.0.1:9001/aivuda_app_store/dev/auth/login" \
  -F "username=admin" \
  -F "password=admin123"
```

返回示例：

```json
{
  "access_token": "<token>",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

后续 dev 接口都带请求头：

```http
Authorization: Bearer <access_token>
```

### 2.2 当前用户

- **GET** `/aivuda_app_store/dev/me`
- 需要 `Authorization: Bearer <token>`

## 3. 开发者接口（`/dev`）

> 以下接口均需要 Bearer Token。

### 3.1 新建应用并发布首个版本

- **POST** `/aivuda_app_store/dev/apps/upload-package`
- 表单字段：
  - `manifest_json`（必填，JSON 字符串）
  - `package_zip`（必填，zip 文件）
  - `name` / `version` / `description`（可传空，最终以 manifest 为准）

成功返回：

```json
{
  "ok": true,
  "app_id": "app_demo",
  "version": "1.0.0",
  "status": "published",
  "download_url": "/aivuda_app_store/store/apps/app_demo/versions/1.0.0/download"
}
```

### 3.2 解析上传包中的 manifest（前端预检）

- **POST** `/aivuda_app_store/dev/apps/manifest/parse-package`
- 表单字段：`package_zip`（必填）

成功返回字段包括：

- `has_manifest`
- `found_path`
- `manifest`
- `normalized_manifest`
- `package_entries`

### 3.3 给已有应用上传新版本

- **POST** `/aivuda_app_store/dev/apps/{app_id}/versions`
- 表单字段：
  - `manifest_json`（必填）
  - `package_zip`（必填）
  - `version` / `description`（可选）

说明：

- `manifest.version` 必填。
- 若传了 `version`，必须与 `manifest.version` 一致。
- `manifest.name` 必须与已有 app 名称一致。
- 前端在上传新版本/替换包前会预检包内 `manifest.name`，若与当前 app 名称不同会提示；提交时仍会按当前 app 名称重写后再上传。

### 3.4 修改版本（描述与/或包）

- **PATCH** `/aivuda_app_store/dev/apps/{app_id}/versions/{version}`
- 表单字段：
  - `description`（可选）
  - `manifest_json`（替换包时必需）
  - `package_zip`（可选，传了表示替换安装包）

### 3.5 下架版本

- **POST** `/aivuda_app_store/dev/apps/{app_id}/versions/{version}/unpublish`

说明：至少保留 1 个 `published` 版本，否则会返回 400。

### 3.6 重新发布版本

- **POST** `/aivuda_app_store/dev/apps/{app_id}/versions/{version}/publish`

### 3.7 删除版本

- **DELETE** `/aivuda_app_store/dev/apps/{app_id}/versions/{version}`

说明：至少保留 1 个版本，否则会返回 400。

### 3.8 删除整个应用

- **DELETE** `/aivuda_app_store/dev/apps/{app_id}`

### 3.9 导出数据库

- **GET** `/aivuda_app_store/dev/data/export/apps`
- 返回当前库中可导出的 app 列表，用于前端勾选

返回示例：

```json
{
  "ok": true,
  "apps": [
    {
      "app_id": "app_demo",
      "name": "Demo",
      "description": "Demo app",
      "version_count": 2
    }
  ]
}
```

- **GET** `/aivuda_app_store/dev/data/export`
- Query 参数：
  - `selected_app_ids`（JSON 数组字符串，例如 `["app_demo","app_other"]`）
- 返回：`application/zip`
- 内容：运行时 `$HOME/aivudaAppStore_ws/data` 目录，归档内路径以 `data/` 开头
- 排除：`data/tmp`

说明：

- 该接口只导出 AppStore 数据库和已发布的文件数据，不导出运行时临时文件。
- 前端会先拉取可导出 app 列表，用户勾选需要导出的 app，支持全选和取消全选。
- 归档中的 `data/repo.db` 会被裁剪为仅包含所选 app 的 `app`、`app_version`、`app_target`、`app_audit_log` 数据。
- 下载文件名形如 `aivudaAppStore-data-YYYYMMDD-HHMMSS.zip`。

### 3.10 预检数据库导入包

- **POST** `/aivuda_app_store/dev/data/import/inspect`
- `Content-Type: multipart/form-data`
- 表单字段：
  - `data_zip`（必填，导出的 data zip）

成功返回示例：

```json
{
  "ok": true,
  "summary": {
    "app_count": 2,
    "version_count": 3,
    "artifact_count": 3
  },
  "apps": [
    {
      "app_id": "app_demo",
      "name": "Demo",
      "description": "Demo app",
      "versions": [
        { "version": "1.0.0", "status": "published", "artifact_count": 1 }
      ],
      "version_count": 1,
      "artifact_count": 1
    }
  ],
  "conflicts": [],
  "importable_apps": []
}
```

说明：

- 导入包必须包含 `data/repo.db`。
- 后端会按包内 `repo.db` 逐条读取 app、version、artifact 信息。
- 前端会先展示包内 app 列表，用户勾选需要导入的 app，支持全选和取消全选。
- `conflicts` 表示当前库中已经存在同名 `app_id` 的应用；实际导入时只对已勾选 app 中的冲突项进行决议。

### 3.11 执行数据库导入

- **POST** `/aivuda_app_store/dev/data/import/apply`
- `Content-Type: multipart/form-data`
- 表单字段：
  - `data_zip`（必填，导出的 data zip）
  - `resolutions`（必填，JSON 字符串，形如 `{"app_demo":"skip","app_other":"overwrite"}`）
  - `selected_app_ids`（必填，JSON 数组字符串，表示本次真正要导入的 app）

成功返回示例：

```json
{
  "ok": true,
  "imported_apps": ["new_app"],
  "overwritten_apps": ["app_demo"],
  "skipped_apps": ["old_app"],
  "failed_apps": [],
  "messages": []
}
```

冲突规则：

- `skip`：跳过该 `app_id`，不导入其任何版本或文件。
- `overwrite`：整应用覆盖，先删除当前同名 app 的全部版本、记录和 `data/files/apps/{app_id}`，再导入包内该 app。
- 已勾选的非冲突 app 会直接导入；未勾选 app 不参与导入。
- `developer_user` 和 `dev_session` 不从导入包恢复，当前登录账号体系保持不变。
- 后端只复制包内 `repo.db` 引用到的 artifact 文件，不盲目合并整个 `data/files`。

## 4. 商店公开接口（`/store`）

> 这些接口默认不要求 token，可被客户端直接访问。

### 4.1 首页索引（每个应用仅最新已发布版本）

- **GET** `/aivuda_app_store/store/index`

返回示例：

```json
{
  "generated_at": 1772500000,
  "items": [
    {
      "app_id": "app_demo",
      "version": "1.1.0",
      "manifest": { "app_id": "app_demo", "name": "Demo", "version": "1.1.0" },
      "updated_at": 1772499999
    }
  ]
}
```

### 4.2 应用详情（含全部版本）

- **GET** `/aivuda_app_store/store/apps/{app_id}`

返回字段：

- `app`: 应用基础信息
- `versions`: 所有版本（包含 published / unpublished）
- `items`: 仅 published 版本（兼容字段）

### 4.3 获取指定已发布版本 manifest

- **GET** `/aivuda_app_store/store/apps/{app_id}/versions/{version}/manifest`

### 4.4 获取下载地址

- **GET** `/aivuda_app_store/store/apps/{app_id}/versions/{version}/download-url`

返回示例：

```json
{
  "url": "/aivuda_app_store/files/apps/app_demo/1.1.0/package.zip",
  "sha256": "...",
  "size": 12345
}
```

### 4.5 下载安装包

- **GET** `/aivuda_app_store/store/apps/{app_id}/versions/{version}/download`
- 返回 `307` 重定向到 Caddy 静态文件路径 `/aivuda_app_store/files/*`
- 实际文件由 Caddy 直接托管，不再由后端 `FileResponse` 流式输出

### 4.6 下载示例包

- **GET** `/aivuda_app_store/store/sample-package`
- 返回文件名：`aivuda-app-pkg-example.zip`

## 5. 常见错误码

- `400`：参数或包格式错误（如 manifest 缺字段、zip 非法）
- `401`：token 缺失/无效/过期（仅 dev 接口）
- `404`：app 或 version 不存在，或资源文件不存在
- `409`：资源冲突（如 app_id 已存在、version 已存在）

错误响应示例：

```json
{
  "detail": "Version 1.0.0 already exists"
}
```

## 6. 推荐调用流程

### 6.1 开发者上传新应用

1. 登录拿 token
2. 可选：`parse-package` 预检查
3. `upload-package` 创建 app 并发布首版
4. 前端通过 `/store/index` 或 `/store/apps/{app_id}` 验证展示

### 6.2 客户端下载

1. 先调 `/store/apps/{app_id}/versions/{version}/download-url`
2. 再访问返回的 `url` 下载 zip
