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
  "download_url": "/aivuda_app_store/files/apps/app_demo/1.0.0/package.zip"
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
  "url": "/aivuda_app_store/store/apps/app_demo/versions/1.1.0/download",
  "sha256": "...",
  "size": 12345
}
```

### 4.5 下载安装包

- **GET** `/aivuda_app_store/store/apps/{app_id}/versions/{version}/download`
- 返回 `application/zip` 文件

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
