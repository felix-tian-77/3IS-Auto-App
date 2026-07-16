## Context

### Worker 注入的环境变量

`worker/airtest_executor.py:13-19` 的 `_META_TO_ENV` 定义了 6 个环境变量，在 `run_script()` 调用 `airtest.cli.runner.run_script(args)` 之前注入到 `os.environ`，调用结束后清理：

```python
_META_TO_ENV = {
    "transaction_id": "TRANSACTION_ID",
    "holder_phone":   "HOLDER_PHONE",
    "customer_phone": "CUSTOMER_PHONE",
    "business_type":  "BUSINESS_TYPE",
    "tax_exempt":     "TAX_EXEMPT",
    "is_transfer":    "IS_TRANSFER",
}
```

Airtest `run_script()` 通过 `exec()` 在进程内执行脚本，因此 `os.environ` 天然可见。

### 3 个脚本的当前状态

| 脚本 | 参数处理 | 问题 |
|------|----------|------|
| `old_vehicle.air/old_vehicle.py:12` | `customer_phone = "19110898582"` | 硬编码；`:94` 引用 `mobile_phone`（未定义）-> NameError |
| `new_vehicle.air/old_vehicle.py:14-15` | `mobile_phone = os.environ.get("CUSTOMER_PHONE") or os.environ.get("HOLDER_PHONE") or "19110898582"` | 仅手机号参数化，缺其他 5 个参数 |
| `renew/renew_01.air/renew_01.py:14` | `mobile_phone = "19110898582"` | 硬编码；`:96` 也硬编码 `"19110898582"` |

## Goals / Non-Goals

**Goals:**
- 3 个脚本头部建立统一的参数声明块
- 修复 `old_vehicle.air` 的 `mobile_phone` 未定义 bug
- `renew_01.air` 不再硬编码手机号

**Non-Goals:**
- 不抽取共享模块（每个 `.air` 独立运行）
- 不修改 Worker 代码
- 不修改业务操作流程

## Decisions

### 1. 参数声明块格式

**选择：** 在 `auto_setup(__file__)` 之后、`poco` 初始化之前，插入统一参数块：

```python
import os

# ---- Parameters (injected by Worker via environment variables) ----
transaction_id = os.environ.get("TRANSACTION_ID")
holder_phone   = os.environ.get("HOLDER_PHONE")
customer_phone = os.environ.get("CUSTOMER_PHONE")
business_type  = os.environ.get("BUSINESS_TYPE")
tax_exempt     = os.environ.get("TAX_EXEMPT", "false").lower() == "true"
is_transfer    = os.environ.get("IS_TRANSFER", "false").lower() == "true"

# 手机号 fallback：优先客户手机号，其次被保险人手机号，最后测试默认值
mobile_phone = customer_phone or holder_phone or "19110898582"
```

**理由：**
- 6 个参数全部声明，即使当前脚本只用手机号 -- 统一格式便于复制和未来扩展
- `tax_exempt` / `is_transfer` 解析为 `bool`（Worker 注入的是 `"true"` / `"false"` 字符串）
- `mobile_phone` 保留为便捷别名，因为脚本中 `set_text(mobile_phone)` 已广泛使用
- `import os` 放在参数块紧邻处（而非文件顶部），因为 airtest 生成的脚本头部是固定模板

### 2. 变量命名统一

**选择：** `set_text` 使用 `mobile_phone` 变量（不是 `customer_phone`）

**理由：**
- `mobile_phone` 是脚本中已有的约定（`new_vehicle.air` 已使用）
- `customer_phone` 是参数源（环境变量），`mobile_phone` 是业务变量 -- 两者职责不同
- `mobile_phone = customer_phone or holder_phone or "default"` 表达了 fallback 优先级

### 3. 不抽取共享模块

**选择：** 每个脚本自带参数块，复制粘贴

**理由：**
- `.air` 脚本通过 `airtest run_script` 以 `exec()` 执行，`import` 本地模块的路径解析不可靠
- 脚本数量少（3 个），复制成本低于维护共享模块的复杂度
- airtest IDE 打开 `.air` 目录时只加载该目录下的文件，共享模块不在搜索路径中

## Architecture Changes

### 修改的组件

| 脚本 | 修改内容 |
|------|----------|
| `old_vehicle.air/old_vehicle.py` | 替换 `:12` 的 `customer_phone = "19110898582"` 为统一参数块；`:94` 的 `set_text(mobile_phone)` 不变（修复了未定义 bug） |
| `new_vehicle.air/old_vehicle.py` | 替换 `:14-15` 的部分参数化为完整统一参数块；`:97` 的 `set_text(mobile_phone)` 不变 |
| `renew/renew_01.air/renew_01.py` | 替换 `:14` 的 `mobile_phone = "19110898582"` 为统一参数块；`:96` 的 `set_text("19110898582")` 改为 `set_text(mobile_phone)` |

### 不修改的组件

| 组件 | 原因 |
|------|------|
| `worker/airtest_executor.py` | 环境变量注入已完成 |
| `worker/main.py` | meta dict 已包含全部字段 |
| `.air` 脚本中的业务操作 | 仅修改参数声明和 `set_text` 调用 |
