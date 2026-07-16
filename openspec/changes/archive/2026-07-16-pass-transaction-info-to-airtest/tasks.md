## 1. 扩展 `AirtestExecutor.run_script` 接受 transaction_meta

- [ ] 1.1 修改 `worker/airtest_executor.py`
  - 新增模块级常量 `_META_TO_ENV = ("transaction_id", "holder_phone", "business_type", "tax_exempt", "is_transfer")`（仅作为文档/参考，不影响实现）
  - 新增内部函数 `_encode_meta_to_env(meta: dict) -> dict[str, str]`：对 `meta` 中 `value is not None` 的字段，按下表映射写入：
    - `transaction_id → TRANSACTION_ID`
    - `holder_phone → HOLDER_PHONE`
    - `business_type → BUSINESS_TYPE`
    - `tax_exempt → TAX_EXEMPT`（bool 转 `"true"` / `"false"` 字符串）
    - `is_transfer → IS_TRANSFER`（同上）
  - 新增内部函数 `_restore_env(snapshot: dict[str, str | None])`：调用方传入的快照，`None` 表示"调用前不存在该 key"，使用 `pop` 清理；非 `None` 用 `os.environ[k] = prior` 恢复
  - 修改 `run_script(self, script_path: str, transaction_meta: dict | None = None) -> bool`：
    - 函数开头 `import os`（如文件顶部没有）
    - 调用 `_airtest_run_script(args)` 前：
      - 计算 `_KEYS = {"TRANSACTION_ID", "HOLDER_PHONE", "BUSINESS_TYPE", "TAX_EXEMPT", "IS_TRANSFER"}`
      - `_env_snapshot = {k: os.environ.get(k) for k in _KEYS}` 保存调用前值
      - 若 `transaction_meta` 不为 `None`，调用 `_encode_meta_to_env(transaction_meta)` 并写入 `os.environ`
    - 调用结束后（无论成功/失败）通过 `try/finally` 进入 `_restore_env(_env_snapshot)`

## 2. `Worker.dispatch_to_device` 把 meta 传给 run_script

- [ ] 2.1 修改 `worker/main.py`
  - 在 `_resolve_script_path(...)` 之后、`airtest_executor.run_script(...)` 调用处，把已经构造好的 `meta` dict 作为第二个参数传入：
    ```python
    ok = self.airtest_executor.run_script(script_path, transaction_meta=meta)
    ```
  - 在 `meta = {...}` 构造处（line 190-197）添加注释，明确"5 个字段会作为环境变量注入 Airtest 脚本"
  - **【本 change 显式 owns】在 `self.file_downloader.save_transaction_meta(transaction_id, meta)` 之后、`self.device_pusher.push_files(...)` 之前**，添加 holder_phone 缺失的运行时 warning：
    ```python
    if meta.get("holder_phone") is None:
        logger.warning(
            "txn %s: holder_phone missing from poll response (business_type=%s); "
            "Airtest script will see HOLDER_PHONE unset",
            transaction_id, meta.get("business_type"),
        )
    ```
  - 行为契约：warning 不改变后续 `push_files` / `run_script` 调用逻辑；缺字段时按现状继续派发

## 3. 添加 pytest 测试覆盖

- [ ] 3.1 新建 `worker/tests/test_airtest_executor.py`
  - `import`：`os`、`sys`、`pytest`、`unittest.mock`，以及 `from worker.airtest_executor import AirtestExecutor`
  - `_make_executor()` fixture：跳过 `__init__`（不连接设备，直接 `AirtestExecutor.__new__(AirtestExecutor)` + 设 `adb_serial = "test_serial"`）
  - 用例 1：`test_run_script_injects_env_vars`
    - monkey-patch `_airtest_run_script` 为一个能感知环境的 `MagicMock`
    - 调用 `executor.run_script("/tmp/fake.air", transaction_meta={"transaction_id": "T-1", "holder_phone": "13800138000", "business_type": "NEW_VEHICLE", "tax_exempt": False, "is_transfer": True})`
    - 断言在调用 `_airtest_run_script` 时刻（即 mock 内），`os.environ["TRANSACTION_ID"] == "T-1"`、`os.environ["HOLDER_PHONE"] == "13800138000"`、`os.environ["BUSINESS_TYPE"] == "NEW_VEHICLE"`、`os.environ["TAX_EXEMPT"] == "false"`、`os.environ["IS_TRANSFER"] == "true"`
  - 用例 2：`test_run_script_restores_env_when_called_with_existing`
    - 调用前设置 `os.environ["HOLDER_PHONE"] = "old"`，调用 `run_script(..., meta={"holder_phone": "new", ...})`
    - 调用结束后断言 `os.environ["HOLDER_PHONE"] == "old"`
  - 用例 3：`test_run_script_cleans_env_when_no_prior_value`
    - 调用前确保 `os.environ` 不含 `HOLDER_PHONE`，调用 `run_script(..., meta={"holder_phone": "13800138000", ...})`
    - 调用结束后断言 `"HOLDER_PHONE" not in os.environ`
  - 用例 4：`test_run_script_with_none_meta`
    - 调用 `run_script("/tmp/fake.air")`（不传 `transaction_meta`），断言不抛异常、mock 被调用一次
  - 用例 5：`test_run_script_skips_none_values`
    - 传 `transaction_meta={"holder_phone": None, "business_type": "NEW_VEHICLE"}`
    - 断言 `os.environ` 在 mock 内不含 `HOLDER_PHONE`、但含 `BUSINESS_TYPE`
  - 验证：`cd worker && pytest tests/test_airtest_executor.py -v`

- [ ] 3.2 **【本 change 显式 owns】追加 JSON 落盘验证用例到 `worker/tests/test_file_downloader.py`**
  - 用例 6：`test_save_transaction_meta_writes_holder_phone`
    - 用 `tmp_path` fixture（如 `tests/conftest.py` 中无 `tmp_path`，声明本地 fixture 即可）
    - 实例化 `FileDownloader(tmp_path)`
    - 调 `fd.save_transaction_meta("T-1", {"transaction_id": "T-1", "holder_phone": "13800138000", "business_type": "NEW_VEHICLE", "tax_exempt": False, "is_transfer": False})`
    - 打开 `tmp_path / "T-1" / "transaction_meta.json"` 读取，断言 `data["holder_phone"] == "13800138000"`、`data["transaction_id"] == "T-1"`、`data["business_type"] == "NEW_VEHICLE"`
  - 用例 7：`test_save_transaction_meta_writes_none_when_missing`
    - 同样 setup，调 `fd.save_transaction_meta("T-2", {"transaction_id": "T-2", "holder_phone": None, "business_type": "OLD_VEHICLE", "tax_exempt": False, "is_transfer": False})`
    - 读回 JSON，断言 `data["holder_phone"] is None`（明确"不隐式"行为）
  - 验证：`cd worker && pytest tests/test_file_downloader.py -v`

## 4. 验证 backend ↔ worker 数据链路

- [ ] 4.1 阅读并确认 `backend/api/v1/tasks.py:55-68` 的 poll 响应仍包含 `holder_phone`
  - 无需改代码；如缺失则补上 `"holder_phone": txn.holder_phone`（依据 proposals/save-transaction-json-metadata 的承诺）
- [ ] 4.2 阅读并确认 `worker/main.py:190-197` 使用 `txn.get("holder_phone")` 而不是 `txn["holder_phone"]`
  - 防止 backend 因任何原因缺失该 key 时 Worker 抛 `KeyError`
  - 如有变更，将方括号访问改为 `.get()`
- [ ] 4.3 **【本 change 显式 owns】人工 / 单测覆盖 `holder_phone` 缺失时的 warning 行为**：
  - 在 `worker/tests/` 下新增 `test_main_warning.py`（或合并到现有 test 模块）
  - 用例：`test_dispatch_warns_when_holder_phone_missing`
    - 构造 `Worker` 子类，跳过 `__init__`，手动设 `file_downloader`、`device_pusher`、`airtest_executor`（mock，不真实连接）
    - 构造 `task = {"task": {"transaction_id": "T-NULL", "holder_phone": None, "business_type": "OLD_VEHICLE", "tax_exempt": False, "is_transfer": False, "attachments": []}}`
    - mock 掉 `fetch_download_urls()` 返回空列表（提前返回避免走到下载路径）
    - 用 `caplog` 捕获 warning 日志，断言 `"holder_phone missing"` 出现在日志中
  - 验证：`cd worker && pytest -v`
- [ ] 4.4 运行现有 worker 测试套件，确保未引入回归
  - `cd worker && pytest -v`

## 5. 端到端冒烟

- [ ] 5.1 启动 Worker（`SCRIPT_MAP` 配置一个测试脚本路径）
  - 确认 `airtest run_script` 启动时（即日志 `"Running business-type script: ..."` 之后），日志若开启 airtest DEBUG 能看到环境变量被读取
- [ ] 5.2 在 `.air` 脚本内临时添加 `print(os.environ.get("HOLDER_PHONE"))` 进行一次性确认
  - 看到真实手机号输出后回滚该 `print`
- [ ] 5.3 验证脚本执行结束后 Worker 进程内 `os.environ` 不含本次注入的 key
  - 通过在 `run_script` 退出后 `_restore_env` 后追加 `logger.debug("Env after restore: %s", {k: os.environ.get(k) for k in _KEYS})` 临时确认
  - 确认完后可选移除该 `logger.debug`
