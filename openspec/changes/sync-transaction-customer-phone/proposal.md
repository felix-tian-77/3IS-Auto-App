# Proposal: Worker 同步 Transaction 时增加 `customer_phone` 字段

## Summary

Worker 从 backend `GET /api/v1/tasks/poll` 同步 transaction 信息时，在 `meta` dict 中增加 `customer_phone` 字段，并将其作为环境变量传递给 Airtest 脚本，使脚本能够访问到真实的客户手机号。

## Motivation

当前 backend poll 响应中包含两个手机号字段：

- `holder_phone`：被保险人手机号（当前已同步）
- `customer_phone`：客户手机号（当前未同步）

但 Airtest 脚本可能需要使用 `customer_phone` 而非 `holder_phone` 进行操作。现有 `pass-transaction-info-to-airtest` change 仅同步了 `holder_phone`，导致 `customer_phone` 无法传递给 Airtest 脚本。

## User Impact

- **Airtest 脚本**：可通过 `os.environ["CUSTOMER_PHONE"]` 读取客户手机号
- **业务场景**：某些 renewal 流程需要使用客户手机号而非被保险人手机号

## Scope

### In Scope

- 在 `worker/main.py` 的 `meta` dict 中增加 `customer_phone` 字段，从 `txn.get("customer_phone")` 获取
- 在 `worker/airtest_executor.py` 的 `_META_TO_ENV` 映射中增加 `customer_phone → CUSTOMER_PHONE`
- 在 `save_transaction_meta()` 调用时确保 `customer_phone` 写入 JSON 文件
- 运行时 warning：当 `customer_phone` 缺失时输出日志
- 添加 pytest 测试覆盖

### Out of Scope

- 不修改 backend poll 响应（已包含 `customer_phone`）
- 不修改 `.air` 脚本（由后续 change 处理脚本侧适配）
- 不修改 `holder_phone` 的现有行为

## Success Criteria

1. `meta` dict 包含 `customer_phone` 字段
2. `transaction_meta.json` 文件包含 `customer_phone` 字段
3. Airtest 脚本可通过 `os.environ["CUSTOMER_PHONE"]` 读取到客户手机号
4. `customer_phone` 缺失时输出 `logger.warning`
5. pytest 测试覆盖 `customer_phone` 的注入逻辑
