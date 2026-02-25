# Frontend (Vue + Vite)

开发者前端（登录后默认进入商店首页）：

- 商店首页：全部应用卡片
- 应用详情：查看版本与平台信息
- 账户菜单（右上角）：
  - 我的应用（卡片）
  - 上传新应用
  - 退出登录
- 我的应用详情：可创建版本、上传平台构建、发布/下架

## 路由

- `/login`
- `/store`
- `/apps/:appId`
- `/me/apps`
- `/me/apps/:appId`
- `/me/new`

## 启动

```bash
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5174`。

如果后端不是同域，登录页填写 `Backend URL`，例如 `http://127.0.0.1:9001`。

## 构建

```bash
npm run build
npm run preview
```
