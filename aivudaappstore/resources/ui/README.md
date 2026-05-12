# Frontend (Vue + Vite)

开发者前端（登录后默认进入商店首页）：

- 商店首页：全部应用卡片
- 应用详情：查看版本并上传/编辑版本
- 全局右下角版本角标：显示当前运行中的 `aivudaappstore` 包版本
- 顶栏（右上角）：
  - 中英文切换
- 账户菜单（右上角）：
  - 上传新应用
  - 导出数据库：先勾选要导出的 app，支持全选和取消全选，再下载 zip 归档，排除 `data/tmp`
  - 导入数据库：上传导出的 data zip，先预检 `repo.db`，再勾选要导入的 app，支持全选和取消全选；遇到同名 `app_id` 时逐项选择跳过或整应用覆盖
  - 退出登录

上传与编辑版本流程：

- 新应用上传：先上传安装包归档并解析，必须存在 `manifest.yaml`，支持 `zip` / `tar.gz` / `tgz` / `tar` / `tar.xz` / `txz`
- 解析成功后展示包内文件树（最多 3 层）
- 新应用提交时仅编辑并校验 4 个必填字段：`app_id`、`name`、`description`、`version`
- 应用详情里的上传新版本/替换包会预检包内 `manifest.name`，若与当前应用名称不同会直接提示，但提交时仍会按当前应用名称重写
- 提交时以后端重写的 `manifest.yaml` 覆盖包内原 manifest

数据库导入导出流程：

- 导出入口在账户菜单中，先加载当前库的 app 列表，勾选后再下载归档
- 导出的 zip 中 `data/repo.db` 会裁剪为仅包含勾选 app 的子库，不再携带未勾选 app 的数据库记录
- 导入入口会先选择 zip 并执行预检，展示应用数、版本数、安装包数，再勾选需要导入的 app
- 导入和导出都支持 `全选` / `取消全选`
- 对已选择且已存在的 `app_id`，可选择 `跳过` 或 `覆盖`
- `覆盖` 会替换当前同名应用的所有版本、记录和 `data/files/apps/{app_id}` 文件
- 导入导出相关前端状态放在 `src/composables/useDataPortability.js`，不要把业务逻辑直接写入 Vue 模板组件

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
右下角版本角标通过只读接口 `/aivuda_app_store/store/meta/version` 获取版本；请求失败时会降级显示 `unknown`，不阻断页面使用。

## 构建

```bash
npm run build
npm run preview
```
