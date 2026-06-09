## Why

当前 3IS-Auto-App 仅有后端 API 和 Worker/Device 组件，缺少面向用户的 Web 界面。员工无法通过浏览器提交保险申请、跟踪处理进度，管理员也无法直观监控系统运行状态。增加前端 Web 服务可以填补这一空白，让系统具备完整的用户交互能力。

## What Changes

- 新增 `frontend/` 目录，基于 React 18 + TypeScript + Vite 5 + Ant Design 5 构建 SPA 前端
- 实现员工门户：提交保险申请（含文件上传）、申请列表跟踪、申请详情查看
- 实现管理后台：运营数据概览仪表盘、Worker/设备实时监控
- 后端新增 3 个 API 接口：申请列表、Worker 列表、仪表盘统计数据
- 新增前端项目配置文件（package.json、vite.config.ts、tsconfig.json）
- 新增 Nginx 配置支持生产部署

## Capabilities

### New Capabilities
- `submit-application`: 员工提交保险申请，选择业务类型（新保/续保），输入客户手机号，上传资料文件，提交至后端
- `track-applications`: 查看所有申请列表，支持搜索、筛选、分页，跟踪处理状态
- `application-detail`: 查看单个申请完整信息，包括基本信息、附件预览、处理时间线
- `admin-dashboard`: 管理概览仪表盘，展示今日申请数、成功率、平均处理时间、设备负载、趋势图和状态分布
- `worker-monitor`: 实时监控 Worker 节点和 Android 设备状态，包括在线状态、CPU、内存、电量、心跳

### Modified Capabilities
<!-- No existing capabilities are modified at the spec level -->

## Impact

- 新增 `frontend/` 目录（约 20+ 源文件）
- 后端新增 3 个 API 端点：`GET /api/v1/transactions`、`GET /api/v1/workers`、`GET /api/v1/statistics/dashboard`
- 新增依赖：React、Ant Design、Axios、React Router、图表库
- 部署变更：新增 Nginx 配置用于前端静态资源服务和 API 反向代理
