## Why

代码审查发现 `add-frontend-web` 变更存在多个 bug 和质量问题：最关键的是后端 `GET /api/v1/transactions` 接口在加密手机号字段上做 `contains` 查询导致搜索永远不返回结果（高严重性，破坏功能），同时存在 N+1 查询、缺失服务层、测试存根等问题。

## What Changes

- 修复后端手机号搜索 bug：解密后在 Python 中匹配，或增加明文搜索字段
- 修复 `GET /api/v1/workers` 接口的 N+1 查询（单次批量查询 device）
- 修复 `GET /api/v1/statistics/dashboard` 中最近申请的 N+1 查询
- 将 `statistics.py` 中重复的状态-文本映射收敛到后端返回统一数据
- 将 `get_dashboard_stats` 拆分到服务层
- 将 `get_transactions` 列表查询的 inline import 提升到文件顶部
- 补全后端测试用例，使用 in-memory SQLite 或 dependency override 真正执行断言
- 前端：使用后端返回的 `data.stats.online`/`offline` 统计值，不再二次计算
- 前端：弱化 TrackApplications 中 phone/id 的正则判断，改为后端同时支持模糊搜索

## Capabilities

### New Capabilities
<!-- No new capabilities; this is a fix change -->
- `bugfix-frontend-review`: 修复 `add-frontend-web` 变更代码审查中发现的所有 bug

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing -->
- `track-applications`: 搜索行为变化——后端改为同时支持 phone 或 transaction_id 模糊匹配，前端不再做正则分流
- `admin-dashboard`: 状态分布图改为使用后端返回的本地化 label（成功/处理中/待处理/失败），不再显示英文

## Impact

- `backend/api/v1/transactions.py`: 修改 `list_transactions` 的搜索逻辑
- `backend/api/v1/workers.py`: 优化 `list_workers` 的 device 查询
- `backend/api/v1/statistics.py`: 优化查询，调整 status_distribution 返回结构，拆分到 service
- `backend/services/`: 新增 `dashboard_service.py`
- `frontend/src/pages/staff/TrackApplications.tsx`: 简化搜索调用
- `frontend/src/pages/admin/WorkerMonitor.tsx`: 使用后端统计
- `frontend/src/types/index.ts`: 调整 `DashboardStats.status_distribution` 字段类型
- `tests/backend/`: 补全 test_transactions_list.py、test_workers_list.py、test_statistics.py
