# Frontend (Vue + Vite)

开发者前端（登录后默认进入商店首页）：

- 商店首页：全部应用卡片
- 应用详情：查看版本并上传/编辑版本
- 账户菜单（右上角）：
  - 中英文切换
  - 上传新应用
  - 退出登录

上传与编辑版本流程：

- 选择 zip 后自动解析包内 `manifest.yaml`
- 表单可编辑全部 aivudaOS 识别字段
- 提交时以表单生成 `manifest.yaml` 覆盖包内原 manifest

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

如果后端不是同域，登录页填写 `Backend URL`，例如 `http://127.0.0.1:9001`。

## 构建

```bash
npm run build
npm run preview
```
