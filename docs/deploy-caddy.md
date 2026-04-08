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

开发模式：

```bash
bash aivudaappstore/resources/scripts/_run_aivudaappstore_stack.sh --dev
```

当前路由保持：

- `https://<public-host>:8580`
  - `/aivuda_app_store/store*` 反代到 `127.0.0.1:9001`
  - 其他路径浏览 `$HOME/aivudaAppStore_ws/data/files/apps`
- `https://<private-host>:8543`
  - `/aivuda_app_store*` 反代到 `127.0.0.1:9001`
  - 其他路径托管前端 SPA
