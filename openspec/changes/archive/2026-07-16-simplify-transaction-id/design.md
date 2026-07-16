## Context

3IS-Auto-App 的事务 ID 由 `TransactionService._generate_id(prefix)` 方法生成（`backend/services/transaction_service.py:43-44`）：

```python
def _generate_id(self, prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
```

调用方：
- `create_transaction()` 中 `self._generate_id("TXN")` 生成事务 ID（`transaction_service.py:67`）
- `create_transaction()` 中 `self._generate_id("ATT")` 生成附件 ID（`transaction_service.py:89`）

此外，`backend/api/v1/transactions.py:42` 中有一段**绕过 `_generate_id`** 的硬编码附件 ID 生成逻辑：

```python
attachment_id = f"ATT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx:04d}"
```

此 `attachment_id` 仅用于上传失败时的 `uploaded_ids` 追踪，真正的附件 ID 在 `TransactionService.create_transaction` 中重新生成。但该硬编码格式也应同步调整以保持一致。

数据库模型（`backend/models/transaction.py:25`）：
- `transaction_id = Column(String(32), primary_key=True)` — 当前最大 ID 长度 28，新格式 19，`String(32)` 足够
- `attachment_id = Column(String(32), primary_key=True)`（`attachment.py:30`）— 同理

前端仅透传后端返回的 `transaction_id`，无格式假设：
- `TrackApplications.tsx:47-51` 显示 `transaction_id` 列
- `ApplicationDetail.tsx:85` 显示 `txn.transaction_id`
- API 路径 `/staff/detail/{id}` 使用 React Router 参数，格式无关

## Goals / Non-Goals

**Goals:**
- 事务 ID 新格式：`T-YYYYMMDD-XXXXXXXX`（示例：`T-20260714-a1b2c3d4`，长度 19）
- 附件 ID 新格式：`A-YYYYMMDD-XXXXXXXX`（示例：`A-20260714-a1b2c3d4`，长度 19）
- 同步修改 `transactions.py` 中的硬编码 `attachment_id` 生成逻辑
- 保持新旧格式 ID 在数据库中共存（无迁移）

**Non-Goals:**
- 不迁移历史数据
- 不修改 UUID 生成算法
- 不修改前端代码
- 不修改 Worker 代码

## Decisions

### 1. 前缀：`T` 和 `A`

**选择：** 事务前缀 `T`（Transaction），附件前缀 `A`（Attachment）

**理由：**
- 单字符前缀语义清晰，`T` = Transaction，`A` = Attachment
- 与原 `TXN`/`ATT` 缩写对应关系明确
- 减少前缀长度 2-3 字符

**备选方案：** 保持 `TXN`/`ATT` 前缀仅缩短日期 — 但用户明确要求"首字母 T"

### 2. 日期格式：`YYYYMMDD`（8 位）

**选择：** 仅保留年月日，去掉时分秒

**理由：**
- 8 位 hex 随机码已保证同秒内唯一性，时分秒对去重无贡献
- 日期部分用于人类可读性（知道事务是哪天创建的），精确到日足够
- 减少 6 字符（`HHMMSS`）
- 简化后 `T-20260714-a1b2c3d4` 比 `TXN-20260714150302-a1b2c3d4` 短 9 字符

**备选方案：** 保持 14 位时间戳 — 但用户明确要求"日期"而非"时间戳"

### 3. 唯一码：`uuid4().hex[:8]`（8 位）

**选择：** 保持现有 8 位 hex 随机码不变

**理由：**
- 8 位 hex = 32 位随机性，单日同前缀冲突概率约 1/43亿，足够
- 不引入数据库序列，保持无状态生成
- 与现有逻辑一致，减少改动面

### 4. `transactions.py` 硬编码 `attachment_id` 统一

**选择：** 将 `transactions.py:42` 的 `f"ATT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx:04d}"` 改为 `f"A-{datetime.now().strftime('%Y%m%d')}-{idx:04d}"`

**理由：**
- 此 `attachment_id` 仅用于上传追踪返回值，真正的附件 ID 在 `TransactionService` 中生成
- 但保持格式一致避免混淆
- 唯一码部分用 `idx:04d`（4 位序号）而非 hex，因为此处无 UUID 调用；保持序号风格但日期和前缀同步简化

### 5. 数据库列长度

**选择：** 保持 `String(32)` 不变

**理由：**
- 新格式最长 19 字符，`String(32)` 足够
- 历史 ID 最长 28 字符，`String(32)` 也兼容
- 修改列长度需要 migration，不必要

## Risks / Trade-offs

- **[风险] 同日冲突概率上升** -> 从 `TXN-YYYYMMDDHHMMSS-XXXXXXXX`（秒级+8hex）变为 `T-YYYYMMDD-XXXXXXXX`（日级+8hex），但 8 位 hex（32 位随机）单日冲突概率仍极低（~1/43亿），可接受
- **[权衡] 新旧格式共存** -> 前端、Worker 代码均以不透明字符串处理 ID，格式无关，共存无影响
- **[风险] `transactions.py:42` 的 `attachment_id` 与 `TransactionService` 生成的可能不一致** -> 此 ID 仅用于上传失败返回，真正 ID 在 Service 层重新生成；但若用户用此 ID 查询会困惑 — 保持格式一致降低混淆

## Architecture Changes

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| TransactionService._generate_id | `backend/services/transaction_service.py:43-44` | 日期格式从 `%Y%m%d%H%M%S` 改为 `%Y%m%d` |
| TransactionService.create_transaction | `backend/services/transaction_service.py:67` | 前缀从 `"TXN"` 改为 `"T"` |
| TransactionService.create_transaction | `backend/services/transaction_service.py:89` | 前缀从 `"ATT"` 改为 `"A"` |
| transactions.create_transaction | `backend/api/v1/transactions.py:42` | 硬编码格式同步简化 |

### 不修改的组件

| 组件 | 位置 | 原因 |
|------|------|------|
| Transaction model | `backend/models/transaction.py:25` | `String(32)` 已兼容新格式 |
| Attachment model | `backend/models/attachment.py:30` | 同上 |
| 前端组件 | `frontend/src/...` | 透传 ID，无格式假设 |
| Worker | `worker/...` | 透传 ID，无格式假设 |
| API 路由 | `backend/api/v1/transactions.py` | 路由参数为字符串，格式无关 |
