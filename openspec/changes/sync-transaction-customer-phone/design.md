## Context

### Backend Poll Response

`backend/api/v1/tasks.py:55-68` 的 poll 响应返回两个手机号字段：

```python
"customer_phone": txn.customer_phone,    # Line 61
"holder_phone": txn.holder_phone,        # Line 66
```

### Worker Meta Construction

`worker/main.py:190-197` 当前只同步 `holder_phone`：

```python
meta = {
    "transaction_id": transaction_id,
    "holder_phone": txn.get("holder_phone"),
    "business_type": txn.get("business_type"),
    "tax_exempt": txn.get("tax_exempt", False),
    "is_transfer": txn.get("is_transfer", False),
}
```

### Airtest Environment Mapping

`worker/airtest_executor.py:13-19` 当前映射：

```python
_META_TO_ENV = {
    "transaction_id": "TRANSACTION_ID",
    "holder_phone":   "HOLDER_PHONE",
    "business_type":  "BUSINESS_TYPE",
    "tax_exempt":     "TAX_EXEMPT",
    "is_transfer":    "IS_TRANSFER",
}
```

## Goals / Non-Goals

**Goals:**
- 在 `worker/main.py` 的 `meta` dict 中增加 `customer_phone` 字段
- 在 `worker/airtest_executor.py` 的 `_META_TO_ENV` 中增加 `customer_phone → CUSTOMER_PHONE` 映射
- 在 `transaction_meta.json` 中包含 `customer_phone` 字段
- 当 `customer_phone` 缺失时输出 `logger.warning`
- 添加 pytest 测试覆盖

**Non-Goals:**
- 不修改 backend poll 响应（已包含 `customer_phone`）
- 不修改 `.air` 脚本
- 不修改 `holder_phone` 的现有行为

## Decisions

### 1. 字段命名：CUSTOMER_PHONE

**选择：** 新增环境变量 `CUSTOMER_PHONE`

**理由：** 与 `HOLDER_PHONE` 命名一致，语义清晰区分"客户手机号"与"被保险人手机号"

### 2. 缺失处理：warning 不阻断

**选择：** `customer_phone` 缺失时输出 `logger.warning`，不阻断执行

**理由：** 与 `holder_phone` 缺失处理策略一致，避免单笔 transaction 失败影响整批派发

## Architecture Changes

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| `meta` dict | `worker/main.py:190-197` | 增加 `customer_phone: txn.get("customer_phone")` |
| `_META_TO_ENV` | `worker/airtest_executor.py:13-19` | 增加 `customer_phone: "CUSTOMER_PHONE"` |
| warning check | `worker/main.py:203-208` | 增加 `customer_phone` 缺失的 warning |

### 新增的测试

> **注意**：`test_airtest_executor.py` 与 `test_main_warning.py` 在代码库中均不存在，archive change `pass-transaction-info-to-airtest` 声称会创建但实际未落地。以下用例均为**新建**。

| 测试 | 位置 | 内容 |
|------|------|------|
| `test_run_script_injects_customer_phone` | `worker/tests/test_airtest_executor.py`（新建） | 验证 `customer_phone` 注入到环境变量 `CUSTOMER_PHONE`，且调用后清理 |
| `test_save_transaction_meta_writes_customer_phone` | `worker/tests/test_file_downloader.py`（追加） | 验证 JSON 文件包含 `customer_phone` 字段 |
| `test_dispatch_warns_when_customer_phone_missing` | `worker/tests/test_main_warning.py`（新建） | 验证 `customer_phone` 缺失时 warning 输出（需 mock `_download_with_refresh` 使流程走到 warning 处） |
