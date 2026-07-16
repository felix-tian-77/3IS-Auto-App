# Proposal: 统一参数化 Airtest 脚本头部参数读取

## Summary

在所有 `.air` 脚本的头部（`auto_setup()` 之后、业务逻辑之前）建立统一的参数声明块，从 `os.environ` 读取 Worker 注入的 6 个环境变量（`TRANSACTION_ID`、`HOLDER_PHONE`、`CUSTOMER_PHONE`、`BUSINESS_TYPE`、`TAX_EXEMPT`、`IS_TRANSFER`），并提供合理的 fallback 默认值，替换脚本中散落的硬编码值。

## Motivation

当前 3 个 `.air` 脚本对参数的处理极不一致，且存在 bug：

| 脚本 | 头部变量 | `set_text` 调用 | 问题 |
|------|----------|----------------|------|
| `old_vehicle.air/old_vehicle.py` | `customer_phone = "19110898582"`（硬编码，变量名与实际用途不符） | `set_text(mobile_phone)`（引用了未定义的 `mobile_phone`） | **运行时 NameError 崩溃** |
| `new_vehicle.air/old_vehicle.py` | `mobile_phone = os.environ.get("CUSTOMER_PHONE") or ...`（仅手机号参数化） | `set_text(mobile_phone)` | 缺少其他 5 个参数声明 |
| `renew/renew_01.air/renew_01.py` | `mobile_phone = "19110898582"`（硬编码） | `set_text("19110898582")`（硬编码） | 完全未参数化 |

根本原因：Worker 端已经通过 `pass-transaction-info-to-airtest` 和 `sync-transaction-customer-phone` 两个 change 实现了 6 个环境变量的注入，但脚本侧从未建立统一的参数读取模式。

## User Impact

- **脚本开发者**：每个脚本头部一目了然地看到所有可用参数及其来源，新增脚本时可直接复制参数块
- **运维**：脚本行为可预测 -- 环境变量缺失时使用明确的 fallback 值，而非崩溃或使用错误号码
- **调试**：参数声明集中在头部，便于排查"为什么脚本填了错误的手机号"等问题

## Scope

### In Scope

- 在 3 个 `.air` 脚本头部建立统一的参数声明块（`import os` + 6 个变量读取）
- 修复 `old_vehicle.air/old_vehicle.py` 中 `mobile_phone` 未定义的 bug
- 将 `renew_01.air/renew_01.py` 中的硬编码值替换为参数变量
- 统一变量命名：`customer_phone`（用于 `set_text`），与业务语义一致

### Out of Scope

- 不修改 Worker 端的环境变量注入逻辑（已在 `sync-transaction-customer-phone` 完成）
- 不修改 `.air` 脚本中的业务操作流程（点击、滑动等）
- 不引入参数校验或类型转换（脚本侧用 `os.environ.get()` 自行处理空值）

## Success Criteria

1. 3 个脚本头部都有统一的参数声明块，包含全部 6 个环境变量读取
2. `old_vehicle.air/old_vehicle.py` 的 `set_text` 使用已定义的变量，不再因 `mobile_phone` 未定义而崩溃
3. `renew_01.air/renew_01.py` 不再硬编码 `"19110898582"`
4. 参数声明块格式在 3 个脚本间完全一致（可复制粘贴）

## Non-Goals

- 不将参数块抽取到共享模块（如 `params.py`）-- 保持每个 `.air` 脚本独立可运行
- 不修改 Worker 代码
- 不新增 `.air` 脚本
