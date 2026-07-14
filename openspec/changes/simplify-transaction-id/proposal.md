# Proposal: 简化 Transaction ID 生成规则

## Summary

将事务 ID 格式从 `TXN-YYYYMMDDHHMMSS-<8hex>` 简化为 `T-YYYYMMDD-<8hex>`。前缀从 `TXN` 缩短为 `T`，日期部分从 14 位时间戳（年月日时分秒）缩短为 8 位日期（年月日），唯一码保持 8 位 hex 不变。新格式示例：`T-20260714-a1b2c3d4`。

## Motivation

当前事务 ID 格式为 `TXN-YYYYMMDDHHMMSS-XXXXXXXX`（如 `TXN-20260714150302-a1b2c3d4`），总长度 28 字符。存在以下问题：

1. **过长**：28 字符在前端表格、移动端展示、日志中占用空间大
2. **时间戳精度冗余**：8 位唯一码已保证唯一性，时分秒（`HHMMSS`）对业务无意义，反而让 ID 更难记忆和口头交流
3. **前缀冗余**：`TXN` 3 字符前缀偏长，单字符 `T` 即可表达 Transaction 语义
4. **与附件 ID 风格不一致**：`_generate_id` 方法同时用于生成 `ATT-` 前缀附件 ID，统一简化后风格更一致

## User Impact

- **前端用户**：申请编号更短、更易阅读和交流（从 `TXN-20260714150302-a1b2c3d4` 缩短到 `T-20260714-a1b2c3d4`，减少 8 字符）
- **运维/开发**：日志、调试中事务 ID 更简洁
- **后端**：仅影响新生成的事务 ID，历史数据不受影响（ID 为字符串主键，新旧格式可共存）

## Scope

### In Scope

- 修改 `_generate_id` 方法的日期格式（去掉时分秒）
- 事务 ID 前缀从 `"TXN"` 改为 `"T"`
- 附件 ID 前缀从 `"ATT"` 改为 `"A"`（与事务 ID 同步简化风格一致）
- 修改 `transactions.py` 中附件 ID 的硬编码生成逻辑（统一到 `_generate_id` 同款风格）
- 不调整 `transaction_id`/`attachment_id` 列长度（`String(32)` 已兼容新旧格式）

### Out of Scope

- 历史数据迁移（旧格式 ID 保留不变）
- 修改前端展示逻辑（前端仅显示后端返回的 ID，无硬编码格式）
- 修改 Worker/Backend 中引用 `transaction_id` 的业务逻辑（ID 作为不透明字符串传递，格式变更不影响）
- 修改 `_generate_id` 方法的唯一码生成算法（仍用 `uuid4().hex[:8]`）

## Success Criteria

1. 新创建的事务 ID 格式为 `T-YYYYMMDD-XXXXXXXX`
2. 新创建的附件 ID 格式为 `A-YYYYMMDD-XXXXXXXX`（统一简化）
3. 现有 API、Worker、前端功能不受影响
4. `transaction_id` 列仍能容纳新旧格式

## Non-Goals

- 不迁移历史数据
- 不修改 UUID 生成算法（仍用 `uuid4().hex[:8]`）
- 不引入数据库序列或自增 ID
- 不修改 API 路径中 `{transaction_id}` 的路由匹配（FastAPI 路由参数为字符串，格式无关）
