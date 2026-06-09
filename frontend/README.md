# 3IS-Auto-App Frontend

React + TypeScript + Vite + Ant Design Web 界面。

## 技术栈

- React 18 + TypeScript
- Vite 5
- Ant Design 5
- React Router 6
- Axios
- @ant-design/charts

## 开发

```bash
cd frontend
npm install
npm run dev
```

开发服务器：<http://localhost:5173>

Vite 会将 `/api` 代理到 `http://localhost:8000`（后端服务）。

## 生产构建

```bash
npm run build
```

产物输出到 `frontend/dist/`，使用 Nginx 提供服务（参考 `scripts/nginx.conf`）。

## 页面

| 路径 | 说明 |
|------|------|
| `/staff/submit` | 提交申请（员工） |
| `/staff/track` | 申请跟踪（员工） |
| `/staff/detail/:id` | 申请详情（员工） |
| `/admin/dashboard` | 管理概览（管理员） |
| `/admin/workers` | 设备监控（管理员） |

## 项目结构

```
frontend/src/
├── api/           # Axios API 客户端
├── components/    # 共享组件
├── pages/         # 页面（staff、admin）
├── types/         # TypeScript 类型
├── utils/         # 工具函数
├── App.tsx        # 根组件（路由配置）
└── main.tsx       # 入口
```
