## 1. 修改 backend poll 响应增加 transaction 元数据字段

- [ ] 1.1 修改 `backend/api/v1/tasks.py:55-65` 的 `poll_task` 返回值
  - 在 `"task"` dict 中增加 `"tax_exempt": txn.tax_exempt`
  - 增加 `"is_transfer": txn.is_transfer`
  - 增加 `"holder_phone": txn.holder_phone`

## 2. 在 FileDownloader 中新增 save_transaction_meta 方法

- [ ] 2.1 在 `worker/file_downloader.py` 中新增 `save_transaction_meta` 方法
  - 参数：`transaction_id: str`, `meta: dict`
  - 调用 `_txn_dir(transaction_id)` 获取目录
  - 将 `meta` dict 序列化为 JSON（`json.dumps`，`ensure_ascii=False`，`indent=2`）
  - 写入 `{txn_dir}/transaction_meta.json`
  - 使用 `json` 模块（在文件顶部 `import json`）

## 3. 在 Worker.dispatch_to_device 中调用 save_transaction_meta

- [ ] 3.1 修改 `worker/main.py:129-173` 的 `dispatch_to_device` 方法
  - 在 `_download_with_refresh()` 成功后（line 158-162 的 if 块之后）、`push_files()` 之前
  - 构建 meta dict，从 `txn` 中提取 `transaction_id`、`holder_phone`、`business_type`、`tax_exempt`、`is_transfer`
  - 调用 `self.file_downloader.save_transaction_meta(transaction_id, meta)`

## 4. 验证

- [ ] 4.1 启动 backend 和 worker，创建 transaction（包含 tax_exempt、is_transfer、holder_phone）
- [ ] 4.2 验证 `GET /api/v1/tasks/poll` 响应中包含 `tax_exempt`、`is_transfer`、`holder_phone` 字段
- [ ] 4.3 验证 Worker 下载完成后 `{WORKER_TMP_DIR}/{transaction_id}/transaction_meta.json` 文件存在
- [ ] 4.4 验证 JSON 文件内容包含正确的 5 个字段值
- [ ] 4.5 验证 `cleanup()` 删除 transaction 目录时 JSON 文件一并被清除
