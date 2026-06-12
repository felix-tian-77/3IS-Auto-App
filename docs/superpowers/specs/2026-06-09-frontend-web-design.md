`# 前端 Web 服务设计文档

## 概述

为 3IS-Auto-App 增加前端 Web 服务，通过 Web 页面调用 backend 服务，实现保险申请提交、跟踪和系统监控功能。

## 技术选型

| 项目 | 选择 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建工具 | Vite 5 |
| UI 组件库 | Ant Design 5 |
| HTTP 客户端 | Axios |
| 路由 | React Router 6 |
| 图表 | @ant-design/charts（或 echarts） |
| 部署 | 独立静态资源，Nginx 反向代理 |

## 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.ts              # Vite 配置，含 API 代理
├── tsconfig.json
├── src/
│   ├── main.tsx                # 入口
│   ├── App.tsx                 # 根组件，路由配置
│   ├── api/                    # API 层
│   │   ├── client.ts           # Axios 实例，baseURL、拦截器
│   │   ├── transactions.ts     # 申请相关 API
│   │   ├── workers.ts          # Worker/设备 API
│   │   └── downloads.ts        # 下载 URL API
│   ├── pages/
│   │   ├── staff/
│   │   │   ├── SubmitApplication.tsx   # 提交申请
│   │   │   ├── TrackApplications.tsx   # 申请跟踪
│   │   │   └── ApplicationDetail.tsx   # 申请详情
│   │   └── admin/
│   │       ├── Dashboard.tsx           # 管理概览
│   │       └── WorkerMonitor.tsx       # 设备监控
│   ├── components/
│   │   ├── AppLayout.tsx       # 整体布局（侧边栏 + 内容区）
│   │   ├── FileUpload.tsx      # 多文件拖拽上传组件
│   │   └── StatusBadge.tsx     # 状态标签组件
│   ├── types/
│   │   └── index.ts            # TypeScript 类型定义
│   └── utils/
│       └── format.ts           # 格式化工具函数
```

## 页面设计

### 1. 侧边栏导航

使用 Ant Design Layout 组件，左侧可折叠侧边栏，两个菜单分组：

- **员工门户**
  - 提交申请 (`/staff/submit`)
  - 申请跟踪 (`/staff/track`)
- **管理后台**
  - 管理概览 (`/admin/dashboard`)
  - 设备监控 (`/admin/workers`)

### 2. 提交申请 (`/staff/submit`)

**功能：** 员工为客户提交保险申请。

**界面元素：**
- 业务类型切换：新保 / 续保（Ant Design Segmented 或 Radio.Group）
- 手机号码输入框（必填，校验格式）
- 文件上传区域（Ant Design Upload 组件，支持拖拽、多选）
- 已选文件列表（显示文件名、大小，支持删除）
- 重置 / 提交按钮

**交互逻辑：**
1. 选择业务类型（新保/续保）
2. 输入客户手机号
3. 拖拽或点击上传资料文件（支持 JPG/PNG/PDF，可多选）
4. 点击提交，调用 `POST /api/v1/transactions`（multipart/form-data）
5. 成功后弹出通知，显示申请编号和预计等待时间
6. 失败时显示错误信息

**校验规则：**
- 手机号必填，格式为 11 位数字
- 至少上传 1 个文件
- 单文件不超过 20MB

### 3. 申请跟踪 (`/staff/track`)

**功能：** 查看所有已提交的申请，跟踪处理状态。

**界面元素：**
- 搜索框（按手机号或申请编号）
- 筛选下拉框：状态（全部/待处理/已派发/处理中/已完成/失败）、业务类型（全部/新保/续保）
- 查询按钮
- 数据表格：申请编号、手机号码、业务类型、状态（彩色标签）、提交时间、操作（详情）
- 分页器

**交互逻辑：**
1. 页面加载时获取申请列表（默认第1页，每页20条）
2. 支持搜索和筛选组合查询
3. 状态用不同颜色标签：待处理(橙)、已派发(蓝)、处理中(蓝)、已完成(绿)、失败(红)
4. 点击"详情"跳转至申请详情页
5. 支持手动刷新

**API：** `GET /api/v1/transactions`（需后端新增列表接口，支持分页和筛选）

### 4. 申请详情 (`/staff/detail/:id`)

**功能：** 查看单个申请的完整信息。

**界面元素：**
- 返回按钮
- 基本信息卡片：申请编号、手机号码、业务类型、当前状态、提交时间、处理设备
- 附件预览区：网格展示缩略图，点击放大预览（图片）或下载（PDF）
- 处理时间线：按时间倒序展示状态变更历史

**交互逻辑：**
1. 根据路由参数 `id` 调用 `GET /api/v1/transactions/{id}` 获取详情
2. 附件点击可预览（图片用 Modal 放大，PDF 触发下载）
3. 时间线从下往上倒序排列，不同状态用不同颜色圆点

### 5. 管理概览 (`/admin/dashboard`)

**功能：** 全局运营数据一览。

**界面元素：**
- 统计卡片行：今日申请数、成功率、平均处理时间、设备负载（带环比变化）
- 图表行：今日每小时申请趋势（柱状图）、状态分布（饼图）
- 最近申请列表（表格，5-10条）

**交互逻辑：**
1. 页面加载时获取统计数据
2. 图表使用 @ant-design/charts 或 echarts 渲染
3. 最近申请列表点击可跳转详情

**API：** 需后端新增统计接口（如 `GET /api/v1/statistics/dashboard`）

### 6. 设备监控 (`/admin/workers`)

**功能：** 实时查看 Worker 节点和 Android 设备状态。

**界面元素：**
- 统计卡片：在线设备数、离线设备数、处理中任务数、排队中任务数
- 设备表格：Worker 名称/IP、绑定设备型号/Android版本、在线状态、CPU、内存、设备电量、存储、最后心跳时间

**交互逻辑：**
1. 页面加载时获取所有 Worker 及绑定设备信息
2. 设备电量低于 30% 橙色预警
3. 心跳超过 60 秒标记为离线
4. 支持按状态筛选

**API：** `GET /api/v1/workers`（需后端新增列表接口）

## 后端接口需求

现有接口可直接使用：
- `POST /api/v1/transactions` — 创建申请（multipart）
- `GET /api/v1/transactions/{id}` — 获取申请详情

需新增接口：
- `GET /api/v1/transactions` — 申请列表（支持分页、搜索、筛选）
- `GET /api/v1/workers` — Worker/设备列表
- `GET /api/v1/statistics/dashboard` — 仪表盘统计数据

## 数据流

```
浏览器 (React SPA)
    │  HTTP (Axios)
    ▼
Nginx (反向代理，开发环境用 Vite proxy)
    │  转发 /api/* 到 backend:8000
    ▼
FastAPI Backend
    │
    ▼
PostgreSQL / Redis
```

## 开发环境

- Vite dev server 端口：5173
- API 代理：`/api` 转发至 `http://localhost:8000`
- 启动命令：`cd frontend && npm run dev`

## 生产部署

- `npm run build` 生成静态文件至 `dist/`
- Nginx 配置：
  - `/` 指向 `dist/` 静态目录
  - `/api/` 反向代理至 backend 服务

## 非功能需求

- 无用户认证（MVP 阶段，假设内网环境）
- 响应式设计（支持桌面端，移动端暂不作为重点）
- 中文界面
- 错误处理：API 异常时显示友好提示
