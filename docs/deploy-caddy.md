# Caddy 部署

`aivudaappstore` 已改为包内只读资源 + 用户工作区模式：

- 前端静态文件来自 `aivudaappstore/resources/ui/dist`
- 运行时 Caddy 配置写入 `$HOME/aivudaAppStore_ws/config/Caddyfile`
- 运行时文件目录写入 `$HOME/aivudaAppStore_ws/data/files`
- Caddy 二进制写入 `$HOME/aivudaAppStore_ws/.tools/caddy/caddy`

推荐方式：

```bash
aivudaappstore install
```

这会自动：

- 下载或校验 Caddy
- 复制运行时 Caddy 配置
- 写入 `aivudaappstore.service`
- 注入 `APPSTORE_PUBLIC_HTTPS_HOST` 与 `APPSTORE_PRIVATE_HTTPS_HOST`

已有安装升级后重新运行 `aivudaappstore install`，以同步包含 HTTP 8540 入口的 Caddy 模板。

常用命令：

```bash
aivudaappstore web
aivudaappstore status
aivudaappstore restart
```

如果只想前台运行整套服务：

```bash
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh
```

如果你是通过 `conda` 安装 `aivudaappstore`，请先激活环境再执行启动脚本：

```bash
conda activate aivuda
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh
```

脚本会优先使用 `AIVUDAAPPSTORE_PYTHON`，其次自动识别 `CONDA_PREFIX/bin/python`、`VIRTUAL_ENV/bin/python`，最后才回退到当前 `PATH` 中的 `python3`。

开发模式：

```bash
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh --dev
```

如果当前 shell 已激活 `conda` 环境，安装脚本会把该环境对应的 Python 解释器写入 `aivudaappstore.service` 的 `AIVUDAAPPSTORE_PYTHON`，这样 `systemd --user` 在重启或开机自启动时也不会丢失到系统 Python。

当前路由保持：

- `http://127.0.0.1:8540`：仅监听回环地址，供 MCP 调用完整管理 API 和静态文件下载。
- 所有入口的 `/aivuda_app_store/files/*` 均由 Caddy 直接提供静态文件。
- `https://<public-host>:8580`
  - `/aivuda_app_store/store*` 反代到 `127.0.0.1:9001`
  - 其他路径浏览 `$HOME/aivudaAppStore_ws/data/files/apps`
- `https://<private-host>:8543`
  - `/aivuda_app_store*` 反代到 `127.0.0.1:9001`
  - 其他路径托管前端 SPA
