## Context

3IS-Auto-App 是一个分布式 RPA 编排平台，用于自动化处理车险投保申请。当前系统由三部分组成：FastAPI 后端（REST API + PostgreSQL + Redis）、Worker 桌面端（Airtest RPA 执行器）、Device Android 端（文件下载器）。缺少面向用户的 Web 界面，员工无法通过浏览器提交申请和跟踪进度，管理员无法直观监控系统状态。

本次设计为系统增加独立的 React SPA 前端，通过 Axios 调用现有后端 API，实现员工门户和管理后台两大功能模块。

## Goals / Non-Goals

**Goals:**
- 提供员工提交保险申请的 Web 表单（含文件上传）
- 提供申请列表跟踪和详情查看页面
- 提供管理概览仪表盘（统计数据 + 图表）
- 提供 Worker/设备实时监控页面
- 后端新增必要的列表和统计 API
- 前后端分离，独立部署

**Non-Goals:**
- 用户认证与权限控制（MVP 阶段，内网环境）
- 移动端适配
- 国际化（仅中文）
- 实时 WebSocket 推送（使用轮询或手动刷新）
- 申请编辑/删除/重试功能

## Decisions

### 1. 技术栈：React + Vite + Ant Design

**选择：** React 18 + TypeScript + Vite 5 + Ant Design 5

**理由：**
- React 生态成熟，社区资源丰富，团队成员熟悉度高
- Vite 开发体验优秀（热更新快），构建产物小
- Ant Design 提供完整的中文表单、表格、上传、图表组件，与业务需求高度匹配
- TypeScript 提供类型安全，与后端 Pydantic 模型对应

**备选方案：**
- Vue 3 + Element Plus：同样优秀，但团队更偏好 React
- Next.js：SSR 能力对本项目价值有限，增加复杂度

### 2. 项目结构：独立 frontend/ 目录

**选择：** 在项目根目录创建独立的 `frontend/` 目录，与 `backend/` 平级

**理由：**
- 前后端完全解耦，可独立开发、测试、部署
- 符合现有项目目录约定（backend/、worker/、device/ 均为独立目录）
- Vite 项目结构标准化，便于新成员上手

### 3. API 对接：Vite Proxy（开发）+ Nginx 反向代理（生产）

**选择：** 开发环境使用 Vite `server.proxy` 将 `/api` 转发至 `http://localhost:8000`，生产环境使用 Nginx 反向代理

**理由：**
- 开发时避免 CORS 问题
- 生产部署时 Nginx 同时服务静态资源和 API 代理，架构简洁
- 不需要在 FastAPI 端配置 CORS

### 4. 状态管理：React 内置状态 + API 层

**选择：** 不引入 Redux/Zustand 等状态管理库，使用 React useState/useEffect + 自定义 hooks

**理由：**
- 页面间数据独立，无复杂跨页面共享状态
- 每个页面自行通过 API 获取数据，数据流清晰
- 减少依赖，降低学习成本

### 5. 图表库：@ant-design/charts

**选择：** @ant-design/charts（基于 G2Plot）

**理由：**
- 与 Ant Design 风格一致
- 封装程度高，几行代码即可生成柱状图、饼图
- 备选：echarts（功能更强但配置更复杂，MVP 阶段不需要）

### 6. 后端新增接口设计

**选择：** 在现有 `backend/api/v1/` 下新增 3 个端点

**理由：**
- 保持 API 版本一致（v1）
- 复用现有 Service 层和 ORM 模型
- 最小化后端改动范围

**新增接口：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/transactions` | 申请列表（分页、搜索、筛选） |
| GET | `/api/v1/workers` | Worker/设备列表 |
| GET | `/api/v1/statistics/dashboard` | 仪表盘统计数据 |

## Risks / Trade-offs

- **[风险] 后端 API 可能缺少前端需要的字段** → 在实现阶段根据前端需求调整后端响应模型
- **[风险] Ant Design 包体积较大** → 使用按需加载（tree shaking），Vite 构建时会自动优化
- **[风险] 无认证可能导致生产环境安全问题** → MVP 阶段依赖内网隔离，后续版本增加认证
- **[权衡] 选择轮询而非 WebSocket 更新设备状态** → MVP 阶段简化实现，后续可升级为 WebSocket 实时推送
