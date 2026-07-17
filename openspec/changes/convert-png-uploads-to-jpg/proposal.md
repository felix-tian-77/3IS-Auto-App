## Why

当前 Backend 在接收上传附件时，直接将客户端原始字节写入存储，仅根据上传文件名后缀拼出存储文件名（`file_type + ext`）。这意味着上传的 PNG 图片会以 `.png` 后缀和 PNG 字节原样落盘。

业务侧希望统一附件存储格式，避免在 Worker 下载、设备推送、Airtest 脚本选择文件时出现 JPG/PNG 两种命名共存的情况，并减少设备端图片解码兼容性问题。将所有 PNG 图片在 Backend 落盘前统一转换为 JPG 格式，可以保证存储文件类型与 `file_format` 默认值（`JPG`）一致，并简化下游消费者。

## What Changes

- Backend 在 `TransactionService.create_transaction` 保存附件前，对 PNG 格式图片进行解码并重新编码为 JPEG 字节后再写入存储。
- 转换后的存储文件名固定使用 `.jpg` 后缀（`{file_type}.jpg`），不再保留上传文件名的 `.png` 后缀。
- 对应的 `Attachment.file_format` 在 PNG 被转换后归一化为 `JPG`，使 DB 元数据与磁盘文件一致。
- 仅对图片附件执行转换；PDF 及其他非 PNG 文件维持现有行为，原样保存。
- 转换失败（如字节不是有效 PNG）时按现有附件保存失败流程处理，事务回滚或不写入该附件。
- 在 Backend `pyproject.toml` 中新增 Pillow 作为图片处理依赖。
- 更新 `tests/backend/test_attachment_storage_layout.py` 中 PNG 用例，断言存储为 `.jpg` 后缀且文件体为 JPEG 字节，并新增转换失败回退用例。

## Capabilities

### New Capabilities

- `backend-image-format-normalization`: 定义 Backend 在持久化上传附件时将 PNG 图片统一转换为 JPG 格式并归一化文件名与元数据的行为。

### Modified Capabilities

无。`attachment-filename-preservation` 中关于 basename 取自存储路径的契约保持不变——本变更改变的是该 basename 本身的生成规则（PNG 一律变为 `{file_type}.jpg`），不改变契约结构。

## Impact

- `backend/services/transaction_service.py`：保存循环中新增 PNG 检测、解码、JPEG 重编码、文件名/`file_format` 归一化逻辑。
- `backend/pyproject.toml`：新增 `Pillow` 运行时依赖。
- `backend/storage/local.py` 与 `backend/storage/base.py`：不变；转换发生在调用 `storage.put` 之前。
- `backend/api/v1/downloads.py`：`filename` 字段自动反映新的 `.jpg` basename，无需改动。
- `backend/api/v1/transactions.py`：上传端点不变；`file_format` 仍由客户端提供作为"声明值"，但服务层会在 PNG 转换后覆写为 `JPG`。
- `tests/backend/test_attachment_storage_layout.py`：既有 PNG 用例需要更新断言，新增转换失败回退用例。
- Worker、Airtest 脚本及 `docs/user-manu.md`：无需改动；它们已通过 Backend basename 消费文件，只是 PNG 上传后会看到 `.jpg` 文件。
