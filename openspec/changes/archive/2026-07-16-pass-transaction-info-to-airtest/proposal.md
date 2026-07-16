# Proposal: 将 Transaction 信息（含用户手机号）作为参数传递给 Airtest 脚本

## Summary

在 Worker 调用 Airtest 脚本之前，将已经保存的 transaction 信息（`transaction_id`、`holder_phone`、`business_type`、`tax_exempt`、`is_transfer`）以环境变量形式注入到脚本执行环境中，让 `.air` 脚本能够读取到本次任务的真实手机号和业务属性，而不是依赖脚本里硬编码的值。

同时确认并固化"Worker 从 backend poll 响应中能拿到用户手机号（`holder_phone`）"这条数据链路 —— backend `GET /api/v1/tasks/poll` 已在响应中返回 `holder_phone` 字段，Worker 在 `dispatch_to_device()` 中读取并写入 `transaction_meta.json`；本 change 通过添加测试与运行时断言，确保该链路不会在后续重构中被静默打断。

## Motivation

当前 Worker 端的 Airtest 调用流程存在三个直接相关的问题：

1. **脚本里的手机号是硬编码的**
   `worker/scripts/renew/renew_01.air/renew_01.py:14` 定义了 `mobile_phone = "19110898582"`，并在 line 96 调用 `.set_text("19110898582")` 把这个硬编码值填进设备端表单。这意味着无论 backend 推送给哪个 transaction 的任务，Airtest 脚本永远都只能填同一个测试号码。本次任务的真实投保人手机号无法被使用。

2. **transaction 信息已经被保存，但没有被"传"给脚本**
   `save-transaction-json-metadata` change 已经实现了 `transaction_meta.json` 落盘 —— 文件里已经包含了 `holder_phone`。但是 Airtest 脚本目前唯一获取上下文的方式是自己再去 `open()` 这个 JSON 文件，不仅路径硬编码、还存在 race condition（脚本可能在 JSON 写入之前就开始读）。
   而更自然的做法是 **Worker 把 transaction 信息作为参数传递给脚本**，与"在磁盘上留下一份副本用于调试/审计"这两个职责应当解耦。

3. **holder_phone 落盘链路没有运行时校验**
   虽然 `worker/main.py:190-197` 的 `meta` dict 已经写入 `holder_phone`，但（a）没有任何测试断言 JSON 文件实际包含该字段；（b）Worker 进程没有任何运行时 guard —— 如果 backend poll 响应因任何原因（字段重命名、Pydantic `exclude_none=True`、schema 调整等）丢失了 `holder_phone`，Worker 会静默地把 `None` 写入 JSON、把 `None` 注入 airtest 环境变量，整条"用户手机号"链路在没有任何日志告警的情况下失效。

合并起来：Worker 既然已经从 backend 拿到了 `holder_phone`，就应当负责把它**写入 JSON（带测试与运行期校验）、同时作为入参传递给 Airtest 脚本**，不要让脚本再去猜测，也不要让链路任何一段静默失效。

## User Impact

- **Airtest 脚本作者**：可通过 `os.environ["HOLDER_PHONE"]` 等环境变量直接读取本次任务的真实手机号和业务属性，不再需要硬编码或手动解析 JSON
- **运维 / 调试**：本地仍然保留 `transaction_meta.json` 文件用于审计、调试，调用参数与持久化文件职责分离，互不依赖
- **Worker 主流程**：保持现有的"推送完成 → 回报 → 执行脚本"顺序，参数注入仅发生在 `run_script()` 调用前后，对外不暴露新接口

## Scope

### In Scope

- 在 `worker/airtest_executor.py` 的 `run_script()` 上扩展一个 `transaction_meta: dict | None` 参数
- 在调用 `airtest.cli.runner.run_script(args)` **之前**，把 `transaction_meta` 里的字段以环境变量形式写入进程环境
- 字段映射：`transaction_id → TRANSACTION_ID`，`holder_phone → HOLDER_PHONE`，`business_type → BUSINESS_TYPE`，`tax_exempt → TAX_EXEMPT`，`is_transfer → IS_TRANSFER`
- 在脚本返回（无论成功/失败）**之后**，从环境中清理本次注入的变量，避免污染下一次任务
- `worker/main.py` 的 `dispatch_to_device()` 调用 `run_script()` 时，把已经构造好的 `meta` dict 作为参数传入
- **【本 change 显式 owns】确认 `holder_phone` 实际写入 `transaction_meta.json`**，并以 pytest 形式覆盖该文件内容
- **【本 change 显式 owns】Worker 在 `dispatch_to_device()` 中检测 `meta["holder_phone"] is None` 时输出 `logger.warning(...)`**（仍继续执行，不阻断）
- 添加 backend / worker 侧的轻量验证：
  - backend `GET /api/v1/tasks/poll` 响应必须包含 `holder_phone`（即便值为 `null`/`""`）
  - Worker 读取 `txn.get("holder_phone")` 不得抛 `KeyError`
  - Worker 通过 `pytest` 验证 `save_transaction_meta()` 写出的 JSON 文件包含 `holder_phone` 字段

### Out of Scope

- 不修改现有 `.air` 脚本（`renew_01.air` 等）—— 它们仍硬编码 `"19110898582"`，由后续 change 处理
- 不修改 `transaction_meta.json` 文件格式（字段名/层级）或落盘路径
- 不修改 `backend/api/v1/tasks.py` 已有的 `holder_phone` 输出逻辑（已实现）
- 不引入 subprocess 调用（继续使用 in-process `airtest.cli.runner.run_script`）
- 不修改 `SCRIPT_MAP` 的解析与分发逻辑
- 不实现其他字段（如姓名、身份证）作为参数的扩展（保持最小集）
- 不在 Worker 端对 holder_phone 缺失做硬中断（policy：warning 而非 raise）

## Success Criteria

1. `AirtestExecutor.run_script()` 接受可选的 `transaction_meta` 参数，签名向后兼容（`None` 表示不传递任何环境变量）
2. 调用 `run_script()` 时，脚本进程内可通过 `os.environ.get("HOLDER_PHONE")`、`os.environ["TRANSACTION_ID"]` 等读到对应字段
3. 脚本执行结束后（无论成功失败），上述环境变量被恢复为调用前的状态（不存在、或为调用前值）
4. `worker/main.py` 的 `dispatch_to_device()` 把 `meta` dict 直接传给 `run_script()`
5. backend poll 响应中 `holder_phone` 字段存在（即便值为 `None`），worker 不会因缺字段而 `KeyError`
6. 提供 pytest 用例（worker 侧）覆盖：传入 `meta={"holder_phone": "13800138000", ...}` → 验证执行期间 `os.environ` 包含对应键 → 退出后被清理
7. **`worker/tests/test_file_downloader.py` 中新增 `test_save_transaction_meta_writes_holder_phone` 与 `test_save_transaction_meta_writes_none_when_missing`**，断言 `save_transaction_meta()` 写出的 JSON 文件对 `holder_phone` 字段的处理（前者：实际写入值；后者：写入 `null`）
8. **`worker/main.py:dispatch_to_device()` 在保存 `meta` 后、推文件前，若 `meta["holder_phone"] is None` 输出 `logger.warning(...)`**，包括 `transaction_id` 与 `business_type` 上下文

## Non-Goals

- 不解密 `customer_phone_encrypted`
- 不修改 `dispatch_to_device` 中已有的下载、推送、回报流程
- 不实现参数模板/校验机制（由脚本作者自行处理空值）
- 不修改 Airtest 脚本内容（仅提供参数通道）
- 不为 `transaction_meta.json` 增减字段（本次仅校验现有 `holder_phone` 字段的落盘与传递）
- 不在 `holder_phone` 缺失时硬中断（仅 warning）
