## 1. 数据库 schema 变更

- [x] 1.1 在 `backend/models/transaction.py` 增加 `customer_phone_search` 字段（VARCHAR 20，nullable，加索引）
- [x] 1.2 在 `scripts/init_db.sql` 中同步增加 `customer_phone_search` 列和索引
- [x] 1.3 在 `backend/services/transaction_service.py` 的创建逻辑中同时写入 `customer_phone_search`

## 2. 后端手机号搜索修复

- [x] 2.1 修改 `backend/api/v1/transactions.py` 的 `list_transactions`，将 `phone` 参数从 `customer_phone_encrypted.contains()` 改为 `customer_phone_search.contains()`
- [x] 2.2 将 `list_transactions` 内的 inline import（`Transaction`、`TransactionStatus`、`BusinessType`）提升到文件顶部

## 3. N+1 查询优化

- [x] 3.1 重构 `backend/api/v1/workers.py` 的 `list_workers`，使用 `Device.device_id.in_(...)` 批量查询
- [x] 3.2 重构 `backend/api/v1/statistics.py` 中 `recent_list` 循环，改为单次 `Worker.worker_id.in_(...)` 批量查询（已迁移到 dashboard_service.py）

## 4. Dashboard 服务层拆分

- [x] 4.1 新建 `backend/services/dashboard_service.py`，迁移 `get_dashboard_stats` 的所有查询逻辑
- [x] 4.2 修改 `backend/api/v1/statistics.py` 路由处理器仅做依赖注入和调用 service
- [x] 4.3 router.py 无需修改（service 通过 Depends 注入到路由处理器）

## 5. 状态文本统一

- [x] 5.1 后端 `dashboard_service.py` 中 `status_distribution` 的 `status` 字段改为中文 label（成功/处理中/待处理/失败）
- [x] 5.2 更新 `frontend/src/types/index.ts` 中 `DashboardStats.status_distribution` 类型（加注释说明现在是中文）
- [x] 5.3 更新 `frontend/src/pages/admin/Dashboard.tsx`（无需修改：原代码已直接使用 `item.status`，后端返回中文后自然显示中文）

## 6. 前端 WorkerMonitor 修复

- [x] 6.1 修改 `frontend/src/pages/admin/WorkerMonitor.tsx`，用 `data.stats.online` / `data.stats.offline` 替换 `workers.filter(...).length`

## 7. 前端 TrackApplications 搜索简化

- [x] 7.1 修改 `frontend/src/pages/staff/TrackApplications.tsx`，移除 `if (/^1\d{10}$/.test(searchText))` 的正则分流逻辑，统一发送 `search` 参数
- [x] 7.2 后端 `list_transactions` 同时按 phone 和 transaction_id 模糊匹配（通过 `or_` 条件 + `search` 参数）

## 8. 后端测试补全

- [x] 8.1 创建根 `conftest.py` 提供 in-memory SQLite 引擎、session、`seed_devices` 辅助 fixture
- [x] 8.2 补全 `tests/backend/test_transactions_list.py`：分页、手机号搜索、ID 搜索、状态筛选 4 个测试
- [x] 8.3 补全 `tests/backend/test_workers_list.py`：基础列表、设备信息、心跳超时、统计计数器 4 个测试
- [x] 8.4 补全 `tests/backend/test_statistics.py`：空数据、状态分布中文、趋势 11 bucket、最近申请 4 个测试
- [x] 8.5 运行 `pytest tests/backend/` 确认 18 个新测试全部通过

## 9. 跨变更污染修复

- [x] 9.1 回滚 `docs/superpowers/specs/2026-06-08-user-manu-design.md` 中的 `STORAGE_LOCAL_PATH` 修改（用 `git checkout` 恢复）
- [x] 9.2 在根目录创建 `.gitignore`，覆盖 `__pycache__/`、`frontend/node_modules/`、`frontend/dist/`、`.venv/`、`.superpowers/` 等
- [x] 9.3 `.superpowers/` 已加入 `.gitignore`

## 10. 集成验证

- [x] 10.1 后端 `python -c "from backend.api.v1 import ..."` 验证模块加载，9 个路由注册
- [x] 10.2 前端 `npx tsc --noEmit` 通过
- [x] 10.3 前端 `npm run build` 成功（2.69MB bundle）
- [x] 10.4 `pytest tests/backend/` 全部 18 个测试通过
