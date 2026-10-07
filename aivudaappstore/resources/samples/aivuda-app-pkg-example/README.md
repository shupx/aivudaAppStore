# aivuda-app-pkg-example

示例应用安装包目录，用于：

- AppStore 前端“下载示例包”功能。
- 开发者本地验证安装包结构与 `manifest.yaml` 字段。

## 当前结构

- `manifest.yaml`：示例 manifest（位于包根目录）。
- `assets/icon.png`：示例图标。
- `scripts/pre_install.sh`：安装前脚本示例。
- `scripts/pre_uninstall.sh`：卸载前脚本示例。
- `scripts/update_this_version.sh`：版本内更新脚本示例。
- `scripts/docker_helpers.sh`：可复制到新 App 的 host/Docker 执行 helper（默认入口不启用 Docker）。
- `start.sh`：app入口sh。
- `ui/index.html`：示例内置 UI 首页（供 aivudaOS iframe 挂载）。
- `config/default_config.yaml`：默认配置文件。
- `config/config_schema.yaml`：配置 schema 文件。

## 用作 sample-package 的打包规则

AppStore 后端会将本目录打成 `tar.gz` 作为示例包下载，规则如下：

- tar.gz 根目录直接包含 `manifest.yaml`（不会额外包一层目录）。
- 会忽略 `.git` 元数据目录。

### 本地打包脚本

目录根下提供了 `pack.sh`：

- 默认将当前目录内容打成 `aivuda-app-pkg-example.tar.gz`
- 默认输出到当前目录的上一层
- 可传入第一个参数指定输出目录

示例：

```bash
./pack.sh
./pack.sh /tmp/aivuda-packages
```

## App 安装包规范（manifest.yaml）

目标：与 aivudaOS 安装器要求对齐，上传后产物可直接用于 aivudaOS 安装。

### 包结构

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

### manifest 必填字段

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

### manifest 支持字段（与 aivudaOS 对齐）

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
- `ui_index_path`
- `caddyfile_config_path`
- `default_config_path`
- `config_schema_path`
- 额外自定义字段（透传）

说明：

- `default_config_path` 必须是包内相对路径，且文件解析后必须是对象
- `config_schema_path` 必须是包内相对路径，且文件解析后必须是对象
- `ui_index_path` 为包内相对路径，通常指向 `ui/index.html`，用于 aivudaOS 前端“进入内置 UI”入口
- `caddyfile_config_path` 为包内相对路径，指向 app 级 Caddy 片段；aivudaOS 会在安装/卸载/切版本时自动将 active 版本片段写入顶层 Caddy import 并 reload
- hooks 路径（如 `pre_install`）若提供，必须是包内文件路径

### 上传与编辑版本流程

1) 前端上传压缩包后，调用解析接口自动读取包内 `manifest.yaml` 并回填表单。
2) 用户可在表单中编辑字段。
3) 提交时始终由表单生成新的 `manifest.yaml`，并覆盖安装包内原 manifest。

当前支持文件格式：`zip`、`tar.gz`、`tgz`、`tar`、`tar.xz`、`txz`。建议尽量用 `tar.gz` / `tgz` 格式，避免 zip 在不同平台解压时可能出现的权限/换行符问题。

### 解析接口

- `POST /aivuda_app_store/dev/apps/manifest/parse-package`
	- 入参：`package_zip`（multipart file，历史字段名，实际支持多种压缩格式）
	- 返回：`has_manifest`、`found_path`、`normalized_manifest`、`warnings`

### 示例包下载

`GET /aivuda_app_store/store/sample-package` 可下载示例 `package.tar.gz`。示例默认使用 `tar.gz`，便于保留包内文件权限。

## 维护建议

- 保持 `manifest.yaml` 与目录中的脚本/资源路径一致。
- 新增字段优先保持向后兼容，避免破坏前端示例上传链路。

## 运行时配置读取（AivudaOS）

该 sample 的 `start.sh` 按 AivudaOS 新约定读取配置：

- `AIVUDA_APP_CONFIG_PATH`：配置 YAML 文件路径
- `AIVUDA_APP_HELPERS_ENTRY_PATH`：统一 helper 入口脚本路径

示例脚本会先 `source "$AIVUDA_APP_HELPERS_ENTRY_PATH"`，再通过 `aivuda_yaml_get` 读取例如 `robot.motion.max_speed_mps` 这类 dotted path 参数。

## 新 App 使用 Docker helper

通过 AppStore“下载示例包”或 MCP `store_sample_package` 获取本包后，将
`scripts/docker_helpers.sh` 复制到新 App 的同名路径。它随示例包分发，不需要
ACEswarm/AivudaOS 源码，也不是 `AIVUDA_APP_HELPERS_ENTRY_PATH` 自动提供的文件。
当前示例默认仍在宿主机运行；复制 helper 并不意味着自动创建或启用容器。

在新 App 的入口或安装 hook 中调用：

```bash
APP_ROOT="${AIVUDA_APP_INSTALL_PATH:?}"
source "${APP_ROOT}/scripts/docker_helpers.sh"
docker_helper_target_use_docker_container 'my-running-container'
docker_helper_target_require_available '[start.sh]'
docker_helper_target_exec_bash 'exec bash /opt/my-app/scripts/run_in_target.sh'
```

上述容器名和容器内路径需要替换为实际配置；`run_in_target.sh` 由新 App 提供。
容器必须已运行，且工作负载文件和依赖必须已存在于容器。helper 不自动创建容器、
挂载文件或转发宿主机环境变量。命令参数来自配置时，使用 `printf %q` 逐项转义；
显式传入工作负载需要的 `AIVUDA_*` 环境变量，并映射对应配置/runtime 路径。

主要接口：

| 接口 | 用途 |
|---|---|
| `docker_helper_target_use_host` | 选择宿主机执行 |
| `docker_helper_target_use_docker_container NAME` | 选择已有容器 |
| `docker_helper_target_require_available [PREFIX]` | 校验执行目标 |
| `docker_helper_target_exec_bash COMMAND` | 在目标运行 Bash 命令字符串，返回退出码 |
| `docker_helper_target_select_install_target` | 安装时交互选择宿主机或运行中的容器，非 TTY 默认宿主机 |
| `docker_helper_target_is_docker` / `docker_helper_target_container` | 查询选择结果 |
| `docker_helper_set_yaml_value PATH KEY TYPE VALUE` | 修改 dotted key 的 YAML 值，需要宿主机 Python3/PyYAML |

Docker 执行会记录容器内 PID/进程组，在退出/信号时尝试清理工作负载；容器具备
`setsid` 时可按进程组清理。每个入口进程不支持并发/嵌套 managed exec；多个节点
应由一个容器内 supervisor 管理。不要用 `exec` 调用 shell helper 函数，也不要覆盖
helper 的清理 trap。上线前验证停止/重启后容器内没有残留或重复进程；不要停止共享
容器来代替停止单个 App。
