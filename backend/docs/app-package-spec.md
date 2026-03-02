# App 安装包规范（manifest.yaml）

目标：与 aivudaOS 安装器要求对齐，上传后产物可直接用于 aivudaOS 安装。

## 包结构

支持两种目录层级：

1) 根目录直接放 `manifest.yaml`
2) 根目录只有一个子目录，`manifest.yaml` 在该子目录中

示例：

```text
manifest.yaml
scripts/
assets/
config/
```

或：

```text
app/
  manifest.yaml
  scripts/
  assets/
```

## manifest 必填字段

```yaml
app_id: hello-world
name: Hello World
description: my app
version: 0.1.0
run:
  entrypoint: scripts/start.sh
  args: []
```

- `app_id`：必填，且在 AppStore 中必须与应用 ID 一致
- `version`：必填；上传新版本时需与版本号一致
- `run.entrypoint`：必填；必须指向安装包内存在的文件

## manifest 支持字段（与 aivudaOS 对齐）

- `app_id`
- `name`
- `description`
- `version`
- `run.entrypoint`
- `run.args`
- `icon`
- `pre_install`
- `pre_uninstall`
- `update_this_version`
- `default_config`
- `config_schema`
- 额外自定义字段（透传）

说明：

- `default_config` 必须是对象
- `config_schema` 必须是对象或 `null`
- hooks 路径（如 `pre_install`）若提供，必须是包内文件路径

## 上传与编辑版本流程

1) 前端上传 zip 后，调用解析接口自动读取包内 `manifest.yaml` 并回填表单。
2) 用户可在表单中编辑字段。
3) 提交时始终由表单生成新的 `manifest.yaml`，并覆盖安装包内原 manifest。

当前支持文件格式：`zip`。

## 解析接口

- `POST /dev/apps/manifest/parse-package`
  - 入参：`package_zip`（multipart file）
  - 返回：`has_manifest`、`found_path`、`normalized_manifest`、`warnings`

## 示例包下载

`GET /store/sample-package` 可下载示例 `package.zip`。
