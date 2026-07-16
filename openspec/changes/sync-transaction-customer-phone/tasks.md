## 1. 修改 `worker/main.py` 增加 `customer_phone` 到 meta dict

- [ ] 1.1 在 `worker/main.py:190-197` 的 `meta` dict 中增加：
  ```python
  "customer_phone": txn.get("customer_phone"),
  ```
- [ ] 1.2 在 `worker/main.py` 的 `holder_phone` warning 之后（约为 line 208），增加 `customer_phone` 缺失的 warning：
  ```python
  if meta.get("customer_phone") is None:
      logger.warning(
          "txn %s: customer_phone missing from poll response "
          "(business_type=%s); Airtest script will see CUSTOMER_PHONE unset",
          transaction_id, meta.get("business_type"),
      )
  ```

## 2. 修改 `worker/airtest_executor.py` 增加环境变量映射

- [ ] 2.1 在 `worker/airtest_executor.py` 的 `_META_TO_ENV` 字典中增加：
  ```python
  "customer_phone": "CUSTOMER_PHONE",
  ```
- [ ] 2.2 更新 `run_script()` 的 docstring（约 line 86）：将 "the 5 known keys" 改为 "the 6 known keys"，并在 `os.environ.get("HOLDER_PHONE")` 示例旁补充 `CUSTOMER_PHONE` 示例

## 3. 添加 pytest 测试覆盖

> **注意**：`test_airtest_executor.py` 与 `test_main_warning.py` 在代码库中**均不存在**（archive change `pass-transaction-info-to-airtest` 声称会创建但实际未落地）。以下用例均为**新建**，不存在可修改的既有用例。

- [ ] 3.1 **新建** `worker/tests/test_airtest_executor.py`，增加 `test_run_script_injects_customer_phone` 用例：
  - `_make_executor()` fixture：跳过 `__init__`（`AirtestExecutor.__new__` + 设 `adb_serial = "test_serial"`）
  - monkey-patch `_airtest_run_script` 为 `MagicMock`（不真实连接设备）
  - 调用 `run_script("/tmp/fake.air", transaction_meta={"transaction_id": "T-1", "holder_phone": "13800138000", "customer_phone": "13900139000", "business_type": "NEW_VEHICLE", "tax_exempt": False, "is_transfer": True})`
  - 断言在 mock 调用期间 `os.environ["CUSTOMER_PHONE"] == "13900139000"`（同时验证 `HOLDER_PHONE` 等已有字段仍正常）
  - 断言调用结束后 `CUSTOMER_PHONE` 被清理（不在 `os.environ` 中）

- [ ] 3.2 在 `worker/tests/test_file_downloader.py` 中**新增** `test_save_transaction_meta_writes_customer_phone`（无既有 holder_phone 版本可参照，从零编写）：
  - 用 `tmp_path` fixture
  - 实例化 `FileDownloader(str(tmp_path))`
  - 调 `fd.save_transaction_meta("T-1", {"transaction_id": "T-1", "holder_phone": "13800138000", "customer_phone": "13900139000", "business_type": "NEW_VEHICLE", "tax_exempt": False, "is_transfer": False})`
  - 读回 `tmp_path / "T-1" / "transaction_meta.json"`，断言 `data["customer_phone"] == "13900139000"`

- [ ] 3.3 **新建** `worker/tests/test_main_warning.py`，增加 `test_dispatch_warns_when_customer_phone_missing`（无既有 holder_phone 版本可参照，需完整 mock `dispatch_to_device` 链路）：
  - 构造 `Worker` 子类或 `__new__` 跳过 `__init__`，手动设 `file_downloader`、`device_pusher`、`airtest_executor`（均 mock，不真实连接）
  - mock `fetch_download_urls()` 返回空 attachments（提前返回避免走到下载路径），或 mock `_download_with_refresh()` 返回空列表导致 `dispatch_to_device` 在 warning 之前 return
  - **注意**：warning 位于 `save_transaction_meta` 之后（line 197）、`push_files` 之前（line 210）。要走到 warning，必须先通过 line 184-185 的下载检查。因此需 mock `_download_with_refresh` 返回非空且全 md5_ok 的结果，或直接在更细粒度上测试 `meta` 构造 + warning 逻辑（提取为可测函数）
  - 构造 `task = {"task": {"transaction_id": "T-1", "customer_phone": None, "holder_phone": "13800138000", "business_type": "OLD_VEHICLE", "tax_exempt": False, "is_transfer": False, "attachments": []}}`
  - 用 `caplog` 捕获 warning 日志，断言 `"customer_phone missing"` 出现在日志中

- [ ] 3.4 验证所有测试通过：
  ```bash
  cd worker && python -m pytest tests/test_airtest_executor.py tests/test_file_downloader.py tests/test_main_warning.py -v
  ```

## 4. 端到端冒烟测试

- [ ] 4.1 启动 Worker，确认 `customer_phone` 被正确写入 `transaction_meta.json`
- [ ] 4.2 在 `.air` 脚本内临时添加 `print(os.environ.get("CUSTOMER_PHONE"))` 验证参数传递
