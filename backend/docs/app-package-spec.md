# App 安装包规范（MVP）

目标：统一打包格式，具备通用性和后续扩展空间。

## 包结构（推荐）

```
app/
  app.yaml
  bin/
  scripts/
  config/
  assets/
  README.md
```

## 必需内容（MVP）

- `app.yaml`
- `scripts/install.sh`
- `scripts/uninstall.sh`
- `scripts/start.sh`
- `assets/icon.png`（建议 256x256）

## app.yaml 最小字段

```yaml
name: "example-app"
version: "0.1.0"
description: "short description"
```

## 可选内容

- `scripts/stop.sh`
- `scripts/upgrade.sh`
- `config/`：默认配置
- `README.md`：使用说明

## 打包

上传时：`app.yaml` 由表单生成，其余文件打成 `package.zip` 上传（不包含 `app.yaml`）。
后端会校验 `app.yaml` 字段及 `package.zip` 是否包含必须文件。
当前仅支持 `zip`。

## 示例包下载

`GET /store/sample-package` 可下载示例 `package.zip` 作为参考。
