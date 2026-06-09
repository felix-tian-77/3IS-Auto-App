## Context

代码审查发现 `add-frontend-web` 变更存在 17 个问题，按严重性分 4 个等级：
- **High（1 个）**：手机号 `contains()` 搜索在加密字段上查询，永远不返回结果
- **Medium（5 个）**：N+1 查询 ×2、缺失服务层、跨变更的存储路径修改、测试存根
- **Low（11 个）**：状态映射重复、统计字段重复计算、bundle 大小等

最高优先级是修复后端手机号搜索功能，否则该功能完全无法使用。

## Goals / Non-Goals

**Goals:**
- 修复手机号搜索功能（用明文字段或后端解密匹配）
- 消除 N+1 查询，提升接口性能
- 把统计数据查询拆分到 service 层
- 补全后端测试用例，至少能在测试 DB 上跑通
- 收敛状态文本映射，避免前后端双份维护

**Non-Goals:**
- 不重写前端 UI
- 不引入新的依赖
- 不改变后端 API 的接口契约（保持现有路径、参数、响应字段名）
- 不优化 bundle 大小（标记为后续优化）

## Decisions

### 1. 手机号搜索：增加明文搜索字段

**选择：** 给 `transactions` 表加一个 `customer_phone_search` 字段（明文 hash 或明文本身），用于搜索。提交时同时写加密字段和搜索字段。

**理由：**
- 加密字段用随机 IV，`contains()` 查询注定不工作
- 解密所有记录在 Python 中比对性能差且 N+1
- 加一个明文字段最简单，且查询走索引高效

**备选方案：**
- 用 `cryptography` 的 Fernet + 固定 IV 加密：安全性低
- 全文检索（PostgreSQL pg_trgm）：引入新依赖，超出本变更范围

**实现：**
- 数据库 schema：加 `customer_phone_search VARCHAR(20) NULL` + 索引
- 提交逻辑：写明文手机号到 search 字段
- 搜索逻辑：列表查询用 `customer_phone_search.contains(phone)`

### 2. N+1 查询：批量预加载

**选择：**
- `list_workers` 用一次 `SELECT ... WHERE device_id IN (...)` 替代循环查询
- `recent_transactions` 同理用 `IN` 查询所有相关 worker

**理由：**
- 不需要修改模型关系
- 100 个 worker 场景：从 101 次查询降到 2 次

**备选方案：**
- 改用 SQLAlchemy `selectinload`：需要在 Worker 模型加 `relationship`，影响范围更大

### 3. 服务层拆分

**选择：** 新建 `backend/services/dashboard_service.py`，把 `get_dashboard_stats` 的 161 行代码迁移过去，路由处理器只做依赖注入和返回。

**理由：**
- 现有 `transaction_service.py`、`dispatcher_service.py` 已经是这个模式
- 路由层只负责 HTTP 关注点（参数解析、响应格式化）

### 4. 状态文本统一

**选择：** 后端 `status_distribution` 直接返回中文 label，前端不再做英文→中文的二次映射。

**理由：**
- 后端硬编码了中英文映射，重复出现在 `statistics.py` 和前端 `format.ts`
- 让后端做一次，前端只负责展示

### 5. 测试补全

**选择：** 用 `pytest-asyncio` + 内存 SQLite + FastAPI dependency override，每个新接口至少 1 个 happy-path + 1 个边界测试。

**理由：**
- 不需要外部 PostgreSQL/Redis 即可跑测试
- 覆盖 spec 文档中的主要场景

## Risks / Trade-offs

- **[风险] 加 `customer_phone_search` 字段需要数据库迁移** → 同时更新 `scripts/init_db.sql` 和提供 alembic 迁移说明；MVP 阶段可以重建表
- **[风险] 现有数据没有 search 字段** → 第一次部署需要回填：全表 SELECT 解密 → 更新 search 字段
- **[权衡] 明文 hash 不如明文好用，但同样能搜索** → 选择明文，运营平台有访问控制
- **[风险] 测试覆盖增加 CI 时间** → 单测本身应 < 5s，可接受

## Migration Plan

1. 在 `scripts/init_db.sql` 增加 `customer_phone_search` 字段
2. 在 `transaction_service.py` 的创建逻辑中同时写入 `customer_phone_search`
3. 修改 `list_transactions` 使用新字段搜索
4. 优化 `list_workers` 和 `get_dashboard_stats` 的查询
5. 拆分 `get_dashboard_stats` 到 `dashboard_service.py`
6. 修改前端消费新响应
7. 补全测试
8. 全部通过后归档变更

回滚：所有变更都是增量，可通过 git revert 恢复。
