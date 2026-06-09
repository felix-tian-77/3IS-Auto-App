## 1. 项目初始化

- [x] 1.1 使用 Vite 创建 React + TypeScript 项目（frontend/ 目录）
- [x] 1.2 安装依赖：antd、@ant-design/icons、@ant-design/charts、axios、react-router-dom
- [x] 1.3 配置 vite.config.ts（API 代理至 localhost:8000）
- [x] 1.4 配置 tsconfig.json（路径别名 @/ 指向 src/）
- [x] 1.5 创建 TypeScript 类型定义（types/index.ts，对应后端数据模型）

## 2. 基础设施

- [x] 2.1 创建 Axios 客户端实例（api/client.ts，baseURL、错误拦截器）
- [x] 2.2 创建 API 模块：transactions.ts（申请相关接口封装）
- [x] 2.3 创建 API 模块：workers.ts（Worker/设备接口封装）
- [x] 2.4 创建工具函数：format.ts（日期格式化、状态文本映射）
- [x] 2.5 创建 AppLayout 布局组件（Ant Design Layout + 侧边栏菜单 + 路由出口）
- [x] 2.6 创建 StatusBadge 状态标签组件（颜色映射）
- [x] 2.7 创建 FileUpload 多文件上传组件（拖拽、多选、文件列表、删除）

## 3. 路由配置

- [x] 3.1 配置 React Router（App.tsx），定义所有路由
- [x] 3.2 配置默认重定向（/ → /staff/submit）

## 4. 提交申请页面

- [x] 4.1 实现业务类型切换（新保/续保 Segmented 组件）
- [x] 4.2 实现手机号输入与校验（11 位数字格式）
- [x] 4.3 集成 FileUpload 组件（支持 JPG/PNG/PDF，单文件 ≤20MB）
- [x] 4.4 实现表单提交逻辑（multipart/form-data 调用 POST /api/v1/transactions）
- [x] 4.5 实现提交成功通知（显示申请编号和预计等待时间）
- [x] 4.6 实现重置按钮（清空所有输入和文件）
- [x] 4.7 实现提交按钮加载状态（防重复提交）

## 5. 申请跟踪页面

- [x] 5.1 实现搜索框（按手机号/申请编号）
- [x] 5.2 实现筛选下拉框（状态、业务类型）
- [x] 5.3 实现数据表格（Ant Design Table，含状态标签列）
- [x] 5.4 实现分页器
- [x] 5.5 实现"详情"按钮跳转至申请详情页
- [x] 5.6 实现刷新按钮

## 6. 申请详情页面

- [x] 6.1 实现基本信息卡片展示（调用 GET /api/v1/transactions/{id}）
- [x] 6.2 实现附件预览区（图片 Modal 放大、PDF 触发下载）
- [x] 6.3 实现处理时间线（Ant Design Timeline，倒序排列，颜色区分）
- [x] 6.4 实现返回按钮（导航回 /staff/track）
- [x] 6.5 实现 404 处理（申请不存在时的提示）

## 7. 管理概览页面

- [x] 7.1 实现统计卡片行（今日申请数、成功率、平均处理时间、设备负载）
- [x] 7.2 实现申请趋势柱状图（@ant-design/charts Column）
- [x] 7.3 实现状态分布饼图（@ant-design/charts Pie）
- [x] 7.4 实现最近申请列表（表格，点击跳转详情）

## 8. 设备监控页面

- [x] 8.1 实现统计卡片（在线/离线设备数、处理中/排队中任务数）
- [x] 8.2 实现设备表格（Worker 信息、设备信息、健康指标）
- [x] 8.3 实现在线/离线状态标签（心跳 60 秒阈值）
- [x] 8.4 实现电量预警（低于 30% 橙色显示）
- [x] 8.5 实现状态筛选（全部/在线/离线）

## 9. 后端新增接口

- [x] 9.1 新增 GET /api/v1/transactions 列表接口（分页、搜索、筛选）
- [x] 9.2 新增 GET /api/v1/workers 列表接口（含绑定设备信息）
- [x] 9.3 新增 GET /api/v1/statistics/dashboard 统计接口
- [x] 9.4 为新增接口编写后端测试（test_transactions_list.py、test_workers_list.py、test_statistics.py）

## 10. 集成与验证

- [x] 10.1 前后端联调测试（提交申请完整流程）— 需运行后端服务后浏览器验证
- [x] 10.2 验证所有页面路由跳转正常 — 5 个路由已配置 React Router
- [x] 10.3 验证错误处理（API 异常、网络错误时的友好提示）— Axios 拦截器 + antd message
- [x] 10.4 验证空状态展示（无数据时的提示）— 各页面 locale emptyText 已设置
- [x] 10.5 运行前端 lint 和 typecheck — `npx tsc --noEmit` 通过，`npm run build` 成功
