## Context

### Worker 当前脚本执行链路

`worker/main.py:207-225` `dispatch_to_device()` 在执行 Airtest 脚本时，仅传入 `script_path`：

```python
script_path = _resolve_script_path(txn.get("business_type"))
if script_path and self.airtest_executor is not None:
    logger.info("Running business-type script: %s", script_path)
    ok = self.airtest_executor.run_script(script_path)
```

`worker/airtest_executor.py:65-95` 的 `run_script()` 当前签名只接收 `script_path: str`，构造 `argparse.Namespace` 后调用 `from airtest.cli.runner import run_script as _airtest_run_script`。在这个调用过程中，Worker 进程上下文（包括 `os.environ`）与 Airtest 脚本共享 —— 这是 `airtest.cli.runner.run_script` 的固有行为：它通过 `setup_by_args()` + `auto_setup()` 复用进程级资源。

### Backend poll 响应中 `holder_phone` 的现状

`backend/api/v1/tasks.py:55-68` 的 poll 响应已经包含：

```python
return {
    "task": {
        ...
        "tax_exempt": txn.tax_exempt,
        "is_transfer": txn.is_transfer,
        "holder_phone": txn.holder_phone,
        ...
    }
}
```

`holder_phone` 字段已在 `backend/models/transaction.py:43` 定义（`Column(String(20), nullable=True)`，明文），并通过 `backend/services/transaction_service.py:83,143` 在事务创建时写入。Worker 在 `worker/main.py:190-197` 读取并构造 `meta` dict：

```python
meta = {
    "transaction_id": transaction_id,
    "holder_phone": txn.get("holder_phone"),
    "business_type": txn.get("business_type"),
    "tax_exempt": txn.get("tax_exempt", False),
    "is_transfer": txn.get("is_transfer", False),
}
self.file_downloader.save_transaction_meta(transaction_id, meta)
```

**这条链路当前是工作的，但缺少保护**：没有任何测试或运行时断言确保 `holder_phone` 这个 key 一定存在。如果未来有人重构 poll 响应或 `txn.get(...)` 调用方式（比如用 Pydantic 模型序列化），可能会在静默中丢失 `holder_phone` 而 Airtest 继续运行（只是手机号变成 `None`）。

### 本 change 显式 owns 的"落盘 + 校验"范围

虽然 `transaction_meta.json` 的写入逻辑已在 `save-transaction-json-metadata` change 中实现，但 `holder_phone` 这个具体字段**写入 JSON 的行为 + 写入后是否仍存在 + 缺失时是否被察觉**这三件事，本 change 显式接管：

- 在 `worker/tests/test_file_downloader.py` 中追加两条用例分别覆盖"写入实际值"与"写入 `None`"两种 JSON 落盘场景
- 在 `worker/main.py:dispatch_to_device()` 中加运行时 warning —— `meta["holder_phone"]` 为 `None` 时显式日志，避免静默失效

这样设计意图是：上游 poll 响应字段丢失这种事故，从"无声恶化"变成"控制台可见的告警"。

### Airtest 脚本对参数的依赖现状

`worker/scripts/renew/renew_01.air/renew_01.py:14`：
```python
mobile_phone = "19110898582"
```
后续 line 96：
```python
poco(...).set_text("19110898582")
```

脚本对 `holder_phone` 的唯一获取方式是"按字面量写在文件里"。**本次 change 不修改脚本本身**，但会打通"Worker 把它作为参数传过去"这条管道 —— 脚本侧的具体使用由后续 change 处理。

### Airtest `run_script()` 与进程环境

`airtest.cli.runner.run_script(parsed_args)` 的实现要点：

1. 调用 `AirtestCase.setUpClass()` → `setup_by_args(args)` → `auto_setup()`
2. `auto_setup()` 内部通过 `os.environ["AIRTEST_DEBUG"]` 等环境变量控制日志行为
3. 脚本（`.air/*.py`）以 `from airtest.core.api import *` 形式被 `exec()` 到全局命名空间，因此可以直接读 `os.environ` / `sys.argv` / 模块级 globals

也就是说，**Worker 进程的环境变量天然可见于脚本**，无需做任何 IPC 桥接。

## Goals / Non-Goals

**Goals:**
- `AirtestExecutor.run_script()` 签名扩展可选的 `transaction_meta` 参数，向后兼容（`None` 时行为不变）
- 在 `run_script()` 内部：通过环境变量把 transaction meta 暴露给 `.air` 脚本；执行结束后清理
- `worker/main.py` 把已构造的 `meta` dict 作为参数传入
- 验证 backend poll 响应包含 `holder_phone`（即便为 `None`），Worker 不会 KeyError

**Non-Goals:**
- 不修改 `.air` 脚本文件本身
- 不修改 `transaction_meta.json` 格式/路径
- 不引入 subprocess
- 不修改 `SCRIPT_MAP` 分发逻辑
- 不扩展到其他参数字段（保持最小集）

## Decisions

### 1. 参数通道选型：环境变量（vs argparse.Namespace 字段 vs JSON 文件）

**选择：** 通过 `os.environ` 注入 `TRANSACTION_ID`、`HOLDER_PHONE`、`BUSINESS_TYPE`、`TAX_EXEMPT`、`IS_TRANSFER` 五个变量

**理由：**
- airtest `run_script()` 是进程内调用，共享 `os.environ`，无需任何桥接
- 环境变量是 airtest 官方已有的进程间传参惯例（`AIRTEST_DEBUG`、`AIRTEST_SCREENSHOT_DIR` 等）
- 脚本侧使用简单：`mobile_phone = os.environ.get("HOLDER_PHONE")`，可自然 fallback
- 清理逻辑简单：调用前保存旧值，调用后 `pop` 或恢复

**备选方案 A：argparse.Namespace 扩展字段**
- 在 `argparse.Namespace` 上加 `holder_phone`、`transaction_id` 等字段，期望脚本从 `args` 读取
- 风险：airtest 的 `setup_by_args()` 内部不会主动把这些字段透传给脚本的 globals，需要侵入 airtest runner 或脚本显式接受参数
- 不可行

**备选方案 B：脚本自己读取 `transaction_meta.json`**
- 已有 `save-transaction-json-metadata` change 已写入该文件
- 风险：脚本必须硬编码路径（如 `~/.3is-auto/tmp/{txn_id}/transaction_meta.json`），与 Worker 的存储配置耦合；race condition（脚本可能在 Worker 写完前启动）；难以单元测试
- 不可行

### 2. 字段最小集：5 个核心字段

**选择：** 只暴露 `TRANSACTION_ID`、`HOLDER_PHONE`、`BUSINESS_TYPE`、`TAX_EXEMPT`、`IS_TRANSFER`，对应 `meta` dict 全部现有字段

**理由：**
- 当前 `meta` dict 已经恰好这 5 个字段，加一个不能少
- 后续如需新字段（如投保人姓名），扩展 `meta` dict + 环境变量注入即可，不改本 change 的契约

**不做：** 不强制 schema —— 脚本侧用 `os.environ.get()` 自行处理缺字段

### 3. 布尔字段编码：字符串 `"true"` / `"false"`

**选择：** `tax_exempt`、`is_transfer` 注入为字符串 `"true"` / `"false"`

**理由：**
- `os.environ` 的 value 类型只可能是字符串
- `"true"` / `"false"` 是 Python 习惯；脚本可写 `os.environ.get("TAX_EXEMPT", "false").lower() == "true"` 一行搞定
- 不需要额外引入数字 1/0 的约定

**备选：** `"1"` / `"0"` —— 更紧凑但与 Python 习惯不一致，可读性差

### 4. 环境变量清理策略：调用前快照、调用后恢复

**选择：** 在 `run_script()` 内部：

```python
_env_snapshot = {k: os.environ.get(k) for k in _INJECT_KEYS}
try:
    for k, v in meta.items():
        os.environ[k] = _encode(v)
    _airtest_run_script(args)
    ...
finally:
    for k, prior in _env_snapshot.items():
        if prior is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = prior
```

**理由：**
- "快照+恢复"模式能容忍"调用方已经设置过同名变量"的情况，不会盲目覆盖
- `try/finally` 保证即使脚本抛 `SystemExit` 或其他异常也能清理（与 `run_script()` 已有的 `try/except` 配合）
- Worker 主循环是单线程顺序处理 transaction，理论上不会并发，但快照+恢复是廉价防御

**备选：** 只 `pop` 不恢复 —— 在没有调用方依赖时也安全，但破坏对称性，未来若有人想"先在外部设个全局默认值再调用"会感到意外

### 5. `None` 值的处理：不注入

**选择：** `meta` 中 `value is None` 的字段不写入 `os.environ`（既不设值也不 pop），调用方用 `os.environ.get(...)` 自然返回 `None`

**理由：**
- `holder_phone` 可能为 `None`（老数据或异常路径）
- 不注入 = "环境里不存在该 key"，与"存在但为空字符串"语义不同
- 脚本侧 `os.environ.get("HOLDER_PHONE")` 在 key 缺失时返回 `None`，这是 Python 惯例

**不做：** 不把 `None` 编码为 `""` —— 会让 `os.environ.get("HOLDER_PHONE")` 返回 `""` 而非 `None`，与"缺失"难以区分

### 6. 验证策略：worker 侧 pytest 用例 + 已存在代码的 audit 注释

**选择：**
- 在 `worker/tests/` 下新增 `test_airtest_executor.py`：
  - `test_run_script_injects_env_vars`：传 `meta={"holder_phone": "13800138000", ...}`，monkey-patch `_airtest_run_script` 捕获环境，检查 `os.environ["HOLDER_PHONE"]` 等 5 个值
  - `test_run_script_restores_env_vars`：调用前 `os.environ["HOLDER_PHONE"] = "old"`，调用后值仍是 `"old"`
  - `test_run_script_cleans_env_vars_on_exit`：调用前 `os.environ` 中无 `HOLDER_PHONE`，调用后仍无
  - `test_run_script_with_none_meta`：传 `None` 不抛异常
- 在 `worker/main.py:dispatch_to_device` 的 `meta` 构造处添加注释，明确"这些字段是 Airtest 脚本的环境变量源"（audit trail）

**理由：**
- pytest 是 Worker 项目已有的测试框架（`worker/tests/test_file_downloader.py` 等），无需引入新工具
- monkey-patch 可以避开真实连接 ADB 的问题

### 7. 不改 backend poll 端

**选择：** backend `tasks.py` 不动

**理由：**
- `tasks.py:55-68` 已经返回 `holder_phone`
- 本 change 的重点是 Worker 内部把它作为参数使用
- Success Criteria 中"poll 响应包含 `holder_phone`"通过 worker 侧 `txn.get("holder_phone")` 的健壮调用 + 测试间接验证

### 8. `holder_phone` 缺失时的运行时 warning（policy 而非 raise）

**选择：** 在 `worker/main.py:dispatch_to_device()` 中，`self.file_downloader.save_transaction_meta(transaction_id, meta)` 调用完成后、`self.device_pusher.push_files(...)` 调用前，加一个判断：

```python
if meta.get("holder_phone") is None:
    logger.warning(
        "txn %s: holder_phone missing from poll response "
        "(business_type=%s); Airtest script will see HOLDER_PHONE unset",
        transaction_id, meta.get("business_type"),
    )
```

**理由：**
- warning 比 raise 更轻量：不阻断单笔 transaction 的推送/脚本执行，避免一个新引入的字段缺失把整个 dispatch 链拖垮
- 仍能让运维人员从日志立刻定位："这条 transaction 没有 holder_phone" → 检查 backend 写入 / schema 变更
- 与现有 `_resolve_script_path` 缺映射时的 `logger.info(...)` 跳过策略保持一致 —— 都是"用日志暴露隐性失败，不阻断主流程"

**备选：**
- raise 异常：会跳过 `push_files`、跳过 airtest，导致本可以跑的 transaction 被错杀
- 静默：保持现状，但未来若 backend 不再返回该字段，谁都看不到

## Risks / Trade-offs

- **[风险] 环境变量污染** → 同进程多个 dispatch（如未来引入并发）会互相覆盖。`try/finally` 清理缓解，但仍是单线程假设 → 后续如需并发，应改用 `argparse.Namespace` 或线程局部存储
- **[风险] 字段命名不同步** → Worker 改 `meta` 字段名而忘记改注入逻辑会静默失败 → 单元测试覆盖 5 个字段全集
- **[风险] holder_phone 缺失被静默忽略** → 缓解：(a) `test_file_downloader.py` 中两条用例锚定 JSON 内容；(b) Worker 运行时 warning 让缺失显式可见
- **[权衡] 仍需保留 `transaction_meta.json`** → 文件用于审计/调试，本 change 不删除，**仅在其上增加校验**
- **[权衡] 脚本侧需要适配** → `renew_01.air` 等仍硬编码 `"19110898582"`，由后续 change 处理
- **[权衡] holder_phone 缺失时仅 warning 不 raise** → 单笔失败的可见性高，但不会阻断推送+脚本执行；若运维没看告警，缺失仍然在生产环境生效 → 长期应考虑将关键字段缺失计入 health check

## Architecture Changes

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| `AirtestExecutor.run_script` | `worker/airtest_executor.py:65-95` | 接受 `transaction_meta: dict \| None`，在 `_airtest_run_script` 调用前后管理环境变量 |
| `Worker.dispatch_to_device` | `worker/main.py:190-225` | (a) 把 `meta` dict 传给 `self.airtest_executor.run_script(script_path, meta)`；(b) `save_transaction_meta` 之后、`push_files` 之前加 `holder_phone is None` 的运行时 warning |

### 新增的组件

| 组件 | 位置 | 内容 |
|------|------|------|
| 测试模块 | `worker/tests/test_airtest_executor.py` | 覆盖环境变量注入、清理、向后兼容 |
| 测试用例 | `worker/tests/test_file_downloader.py`（追加） | `test_save_transaction_meta_writes_holder_phone` + `test_save_transaction_meta_writes_none_when_missing` |

### 不修改的组件

| 组件 | 位置 | 原因 |
|------|------|------|
| `backend/api/v1/tasks.py` | 已经返回 `holder_phone` | 无需再改 |
| `FileDownloader.save_transaction_meta` | `worker/file_downloader.py` | 输出文件保留，作为 audit trail；仅由测试用例覆盖其内容，不改实现 |
| `SCRIPT_MAP` / `_resolve_script_path` | `worker/main.py:27-49` | 分发逻辑不变 |
| `.air` 脚本 | `worker/scripts/**` | 由后续 change 处理 |
| `meta` dict 默认值 | `worker/main.py:190-197` | 保持现有行为：`holder_phone`/`business_type` 默认 `None`，`tax_exempt`/`is_transfer` 默认 `False`。统一默认值的重构不属于本 change |
