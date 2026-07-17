## 1. 依赖与转换辅助

- [x] 1.1 在 `backend/pyproject.toml` 的 `dependencies` 中新增 `Pillow`（指定与 Python 3.13 兼容的版本，例如 `Pillow==11.0.0` 或更新），并执行 lock 安装确认 `PIL` 可导入。
- [x] 1.2 新增 `backend/services/image_convert.py`，实现 `png_to_jpeg_bytes(data: bytes) -> bytes | None`：
  - 用 `PIL.Image.open(BytesIO(data))` 解码；
  - RGBA / LA / 带 transparency 的 P 模式先合成到白底 RGB；
  - 其他模式直接 `convert("RGB")`；
  - `out.save(buf, format="JPEG", quality=92)`；
  - 任何异常返回 `None`（不向上抛原始栈）。
- [x] 1.3 为 `image_convert.py` 写最小单元测试（可选，若 backend 下已有 services 测试目录则放 `backend/services/tests/test_image_convert.py`）：用一个真实 1x1 RGBA PNG 字节断言返回值可被 Pillow 再次打开且 mode 为 `RGB`；用 `b"not-a-png"` 断言返回 `None`。

## 2. Service 层接入转换

- [x] 2.1 修改 `backend/services/transaction_service.py` 的 `create_transaction` 保存循环（当前 `transaction_service.py:86-113`）：
  - 计算 `ext = Path(file_meta["filename"]).suffix.lower()`；
  - 若 `ext == ".png"`：调用 `png_to_jpeg_bytes(file_data)`；
  - 返回 `None` 时 `raise ValueError(f"PNG conversion failed for {file_type}")`（与 `_validate_required_files` 同样的失败语义）；
  - 成功时将 `file_data` 替换为 JPEG 字节、`ext = ".jpg"`、`file_format = "JPG"`；
  - 非 PNG 分支保持现有行为不变。
- [x] 2.2 确认 `storage.put` 调用对被转换的附件使用 `content_type="image/jpeg"`（当前已传入 `file_meta["content_type"]`，需在转换分支内覆写）。
- [x] 2.3 确认 `Attachment.file_format` 字段写入归一化后的 `JPG`，而非 `file_meta["file_format"]`（当前 `transaction_service.py:104`）。
- [x] 2.4 确认 `md5` / `sha256` 基于转换后的字节计算（当前 `transaction_service.py:89-90` 在循环开头计算，需要把 hash 计算移到转换之后，或对转换分支重新计算）。

## 3. 测试更新

- [x] 3.1 更新 `tests/backend/test_attachment_storage_layout.py` 的 `test_storage_key_uses_transaction_id_and_backend_filename`：
  - 把 `ID_CARD_BACK` 用例的 `file_format` 改为 `PNG`、`filename` 仍为 `back.PNG`、`content_type` 为 `image/png`，但**字节改为一个真实的 PNG**（用 Pillow 在测试内构造 2x2 RGBA PNG 字节）；
  - 断言 `storage_path == f"{transaction_id}/ID_CARD_BACK.jpg"`；
  - 断言磁盘文件存在且 `PIL.Image.open(...).format == "JPEG"`；
  - 断言 `attachment["file_format"] == "JPG"`；
  - 断言 `attachment["file_size"]` 反映 JPEG 字节长度而非原 PNG 长度。
- [x] 3.2 更新 `test_storage_key_handles_missing_extension`：保持 ID_CARD_FRONT 无扩展名用例不变（继续断言 `ID_CARD_FRONT` 无后缀），但把 ID_CARD_BACK 用例也改为真实 PNG 并断言落盘为 `.jpg`。
- [x] 3.3 新增 `test_png_conversion_failure_aborts_transaction`：
  - 用 `back.png` 文件名 + `b"not-a-real-png"` 字节；
  - 用 `pytest.raises(ValueError)` 包裹 `await service.create_transaction(...)`；
  - 断言事务未提交、无 `Attachment` 行、磁盘上无该附件文件（注意：现有 `create_transaction` 失败路径是否回滚 DB 需在实现时确认，若不回滚则测试断言聚焦于"未写入存储文件"和"抛出 ValueError"）。
- [x] 3.4 新增 `test_rgba_png_composited_on_white`：
  - 构造一个四角透明、中心红色的 4x4 RGBA PNG；
  - 上传；
  - 读回 JPEG，断言四个角像素为白色 `(255,255,255)`、中心像素接近红色。
- [x] 3.5 运行 `python -m pytest tests/backend/test_attachment_storage_layout.py -v` 确认全部通过。

## 4. 回归与文档

- [x] 4.1 运行 Backend 全量测试 `python -m pytest tests/backend/ -v`，确认无回归（特别是 `test_attachments_delivered.py`、`test_transactions.py`）。
- [x] 4.2 在 `docs/user-manu.md`（若存在附件存储说明段落）补充一行说明："上传的 PNG 图片会在 Backend 自动转换为 JPG 存储"，若无相关段落则不强制新增。
- [ ] 4.3 手动冒烟（可选）：用 curl 上传一个真实 PNG 证件图，确认下载 URL 返回的 `filename` 以 `.jpg` 结尾，且再次下载得到的字节是 JPEG。
