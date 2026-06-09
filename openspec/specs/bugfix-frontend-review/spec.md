# Purpose
TBD — describe purpose of bugfix-frontend-review capability.

## Requirements

### Requirement: 手机号明文搜索
系统 SHALL 在 transactions 表存储明文手机号字段 `customer_phone_search`，用于手机号模糊搜索。

#### Scenario: 创建申请时写入 search 字段
- **WHEN** 用户提交申请并提供手机号 "13812341234"
- **THEN** 数据库同时写入 `customer_phone_encrypted`（密文）和 `customer_phone_search`（明文 "13812341234"）

#### Scenario: 列表接口按手机号搜索
- **WHEN** 用户在前端搜索框输入 "1381" 调用 GET /api/v1/transactions?phone=1381
- **THEN** 系统返回所有手机号包含 "1381" 的申请记录

### Requirement: Worker 列表批量查询设备
系统 SHALL 在 GET /api/v1/workers 接口中通过单次批量查询获取所有 worker 的绑定设备信息，不得使用 N+1 查询模式。

#### Scenario: 100 个 worker 设备查询
- **WHEN** 系统中有 100 个已注册 worker
- **THEN** GET /api/v1/workers 接口触发的 SQL 查询数不超过 3 次（worker 查询 + 批量 device 查询 + 计数查询）

### Requirement: 最近申请批量查询 worker
系统 SHALL 在 GET /api/v1/statistics/dashboard 接口中通过单次批量查询获取最近 10 条申请关联的 worker 信息。

#### Scenario: 最近申请 worker 查询
- **WHEN** 系统返回最近 10 条申请
- **THEN** 触发的额外 worker 查询数不超过 1 次（IN 批量查询）

### Requirement: 状态分布使用中文 label
系统 SHALL 在 GET /api/v1/statistics/dashboard 的 `status_distribution` 字段中返回中文标签（成功、处理中、待处理、失败），前端无需再做本地化映射。

#### Scenario: 状态分布响应
- **WHEN** 系统返回 dashboard 统计
- **THEN** `status_distribution` 中每个元素的 `status` 字段为中文 label（"成功"/"处理中"/"待处理"/"失败"）

### Requirement: Dashboard 服务层拆分
系统 SHALL 提供 `DashboardService.get_dashboard_stats(db)` 方法，封装所有 dashboard 统计查询逻辑；路由处理器仅做依赖注入和响应返回，不直接执行 SQL。

#### Scenario: 服务层调用
- **WHEN** 路由处理器收到 GET /api/v1/statistics/dashboard 请求
- **THEN** 路由调用 `DashboardService.get_dashboard_stats(db)` 并返回其结果

### Requirement: 列表接口 imports 提升到文件顶部
系统 SHALL 将 backend/api/v1/transactions.py 中 `list_transactions` 函数体内的 inline imports（`Transaction`、`TransactionStatus`、`BusinessType`）提升到文件顶部 import 区域。

#### Scenario: imports 位置
- **WHEN** 静态分析 transactions.py
- **THEN** 文件顶部包含所有模型和 SQLAlchemy 函数的 import，函数体内不出现 inline model import

### Requirement: 后端测试覆盖
系统 SHALL 为 GET /api/v1/transactions、GET /api/v1/workers、GET /api/v1/statistics/dashboard 三个新接口提供可执行的 pytest 测试用例，每个接口至少包含 1 个 happy-path 测试和 1 个边界场景测试。

#### Scenario: 列表接口测试
- **WHEN** 运行 `pytest tests/backend/test_transactions_list.py`
- **THEN** 至少 2 个测试用例通过，包含基础分页查询和手机号搜索场景

#### Scenario: Worker 列表测试
- **WHEN** 运行 `pytest tests/backend/test_workers_list.py`
- **THEN** 至少 2 个测试用例通过，包含基础列表和心跳超时标记离线场景

#### Scenario: 统计接口测试
- **WHEN** 运行 `pytest tests/backend/test_statistics.py`
- **THEN** 至少 2 个测试用例通过，包含基础统计和空数据场景

### Requirement: 统计字段不再前端重复计算
系统 SHALL 在前端 WorkerMonitor 页面使用后端返回的 `data.stats.online` 和 `data.stats.offline` 统计值，不在 `workers` 数组上重新计算。

#### Scenario: 统计数据来源
- **WHEN** WorkerMonitor 渲染统计卡片
- **THEN** 在线/离线设备数取自 `data.stats.online`/`data.stats.offline`，与 worker 列表状态字段一致
