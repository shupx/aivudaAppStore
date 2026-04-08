# Frontend (Vue + Vite)

开发者前端（登录后默认进入商店首页）：

- 商店首页：全部应用卡片
- 应用详情：查看版本并上传/编辑版本
- 顶栏（右上角）：
  - 中英文切换
- 账户菜单（右上角）：
  - 上传新应用
  - 退出登录

上传与编辑版本流程：

- 新应用上传：先上传 zip 并解析，必须存在 `manifest.yaml`
- 解析成功后展示包内文件树（最多 3 层）
- 新应用提交时仅编辑并校验 4 个必填字段：`app_id`、`name`、`description`、`version`
- 提交时以后端重写的 `manifest.yaml` 覆盖包内原 manifest

## 路由

- `/login`
- `/store`
- `/apps/:appId`
- `/me/new`

## 启动

```bash
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5174`。

开发环境通过 `vite.config.js` 将 `/aivuda_app_store` 代理到 `http://127.0.0.1:9001`，无需在登录页手工填写后端地址。

## 构建

```bash
npm run build
npm run preview
```
