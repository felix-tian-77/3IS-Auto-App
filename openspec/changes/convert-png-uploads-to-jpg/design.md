## Context

Backend 当前在 `TransactionService.create_transaction`（`backend/services/transaction_service.py:86-113`）保存上传附件时：

1. 从客户端上传文件名取后缀 `ext = Path(file_meta["filename"]).suffix.lower()`。
2. 拼出存储文件名 `filename = f"{file_type}{ext}"`，存储 key 为 `{transaction_id}/{filename}`。
3. 通过 `self.storage.put(storage_key, file_data, file_meta["content_type"])` 原样写入字节。
4. 写入 `Attachment` 行时 `file_format` 取自 `file_meta["file_format"]`（客户端声明，端点默认 `JPG`），与实际字节不做校验。

因此 PNG 上传会以 `ID_CARD_BACK.png` 落盘、字节为 PNG，而 `file_format` 可能同时是 `PNG`（客户端声明）或 `JPG`（默认），三者无一致性保证。`backend/pyproject.toml` 目前没有任何图片处理库。

本变更只在 Backend 写入存储前插入一步"PNG -> JPEG"转换，不改变存储后端抽象、下载 URL 契约或 Worker 端文件名透传逻辑（后者已由 `preserve-backend-image-filenames` 建立）。

## Goals / Non-Goals

**Goals:**

- 所有 PNG 图片附件在 Backend 落盘时字节为 JPEG，文件名后缀为 `.jpg`。
- `Attachment.file_format` 对被转换的附件统一为 `JPG`，与磁盘文件一致。
- 仅作用于 PNG 图片；JPG 图片、PDF 及其他类型保持现有"原样保存"行为。
- 转换发生在内存中，在 `storage.put` 调用之前；存储后端接口不变。
- 转换失败（损坏 PNG、解码异常）按现有"附件保存失败"语义处理，不写入半成品文件。
- 覆盖单元测试：PNG 转换为 JPG（字节 + 文件名 + `file_format`）、JPG 透传、PDF 透传、无扩展名透传、损坏 PNG 失败回退。

**Non-Goals:**

- 不做图片 resize / 压缩 / 缩略图 / 元数据剥离，只做格式转码。
- 不迁移历史已存储的 PNG 文件；仅对新上传生效。
- 不改变上传端点 multipart 契约、`attachments_meta.file_format` 字段含义（仍是客户端声明），仅在服务层覆写最终落库值。
- 不引入 OSS / MinIO 存储后端实现。
- 不处理动画 PNG（APNG）；按 Pillow 默认行为取首帧或直接转码，不专门保留动画。
- 不处理透明通道保留策略以外的色彩空间调整；统一以白底合成 RGBA PNG（避免 JPEG 不支持 alpha 导致黑底）。

## Decisions

### 使用 Pillow 作为图像处理依赖

新增 `Pillow` 到 `backend/pyproject.toml` 的 `dependencies`。Pillow 是 Python 生态事实标准的图像库，纯 Python wheel 可用，依赖体积可控，且后端运行时为 Python 3.13（`backend/pyproject.toml` 要求 `>=3.13`），Pillow 主线已长期支持。

备选方案：`opencv-contrib-python`（已在 `worker/pyproject.toml` 使用）。但 OpenCV 体积更大、API 更底层，且其 wheel 在 Windows 上安装更重；Backend 不需要计算机视觉能力，Pillow 更合适。

备选方案：调用外部 `ffmpeg`/`imagemagick` 子进程。引入系统级二进制依赖，部署复杂度上升，且无法在进程内拿到字节，性能与可观测性都更差。否决。

### 在 service 层转换，不动 storage 后端

转换逻辑放在 `TransactionService.create_transaction` 的保存循环内、`storage.put` 之前：

```python
ext = Path(file_meta["filename"]).suffix.lower()
file_type = file_meta["file_type"]
file_format = file_meta.get("file_format", "JPG")
data = file_data

if ext == ".png":
    converted = _png_to_jpeg_bytes(file_data)
    if converted is None:
        raise ValueError(f"PNG conversion failed for {file_type}")
    data = converted
    ext = ".jpg"
    file_format = "JPG"

filename = f"{file_type}{ext}"
storage_key = f"{transaction_id}/{filename}"
await self.storage.put(storage_key, data, "image/jpeg")
```

理由：`LocalStorageBackend.put` 只负责把字节写入文件系统并做路径校验，不应承担格式语义；保持 storage 层职责单一便于将来替换为 OSS / MinIO 时无需重写转换逻辑。

### PNG 判定基于上传文件名后缀

是否触发转换以 `Path(file_meta["filename"]).suffix.lower() == ".png"` 为准，不做 magic-byte 嗅探。理由：

- 现有代码已基于文件名后缀生成存储文件名，行为一致。
- 引入 magic-byte 嗅探会扩大变更范围，且当前上传端点已通过 `attachments_meta.file_format` 表达客户端意图。
- 若客户端把 PNG 命名为 `.jpg` 上传，则按 JPG 处理（Pillow 在 JPEG 重编码时会因非 JPEG 字节失败并走失败回退，行为可接受且明确）。

备选方案：用 `imghdr.what()` 或 Pillow `Image.open()` 探测真实格式。扩大检测面但与现有"信任文件名"的存储契约不一致，留作未来增强。

### 透明通道以白底合成

Pillow 将 RGBA PNG 转 JPEG 时必须先合成到不透明背景，否则 alpha 通道丢失后会出现黑底。统一使用白底：

```python
from io import BytesIO
from PIL import Image

def _png_to_jpeg_bytes(data: bytes) -> bytes | None:
    try:
        with Image.open(BytesIO(data)) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im.convert("RGBA"), mask=im.split()[-1])
                out = bg
            else:
                out = im.convert("RGB")
            buf = BytesIO()
            out.save(buf, format="JPEG", quality=92)
            return buf.getvalue()
    except Exception:
        return None
```

`quality=92` 在肉眼无差异与文件体积之间取折中。备选 `quality=95` 体积明显增大但视觉收益有限；备选 `quality=85` 在文字类证件图上可能出现压缩伪影。选 92 作为默认，未来可配置化。

### 失败回退：抛错让事务回滚

转换失败时直接 `raise ValueError`，让 `create_transaction` 的外层异常处理（HTTP 端点会捕获 `ValueError` 返回 422）感知失败，不写入半成品文件，不创建 `Attachment` 行。这与现有 `_validate_required_files` 抛 `ValueError` 的模式一致。

备选方案：跳过该附件但继续提交其余附件。会导致事务部分成功、必需附件缺失的语义混乱，且现有 `file_missing` 错误类型语义不匹配。否决，统一走失败回退。

### `file_format` 归一化

转换成功后 `Attachment.file_format` 强制写 `JPG`，忽略客户端传入的 `PNG`。这样下游 Worker / Airtest 脚本通过 `filename` basename 推断格式时与 DB 元数据一致。

`FileFormat` 枚举（`backend/models/attachment.py:17-20`）保留 `PNG` 取值不变，兼容历史数据查询；本变更不删除枚举项。

## Risks / Trade-offs

- [依赖新增] 引入 Pillow 增加 Backend 镜像体积约 10-15MB。-> 可接受，Pillow 是纯 Python wheel，无需系统级二进制。
- [转换失败导致提交失败] 损坏 PNG 会让整个事务提交失败而非跳过单文件。-> 与现有"必需附件缺失"语义一致，用户需重新上传有效文件。
- [透明通道颜色变化] RGBA PNG 合成到白底后，原本透明区域变白。-> 这是 JPEG 格式限制的必然结果，且证件照片通常本身就是不透明背景，影响可控。
- [历史 PNG 文件不迁移] 已存的 `.png` 文件不会自动转换。-> 仅对新上传生效；若需迁移，另开 change 处理，避免影响线上稳定存储。
- [文件名后缀信任] 客户端把非 PNG 文件命名为 `.png` 会导致 Pillow 解码失败。-> 走失败回退，用户得到明确错误；不扩大到 magic-byte 嗅探。
- [压缩质量选择] `quality=92` 是经验值。-> 在 `test_attachment_storage_layout.py` 中用真实 PNG 字节断言转码后体积合理、可被 Pillow 再次打开，覆盖该默认值的稳定性。

## Migration Plan

1. 在 `backend/pyproject.toml` 增加 `Pillow` 依赖并更新 lock。
2. 在 `backend/services/transaction_service.py`（或新增 `backend/services/image_convert.py` 辅助模块）实现 `_png_to_jpeg_bytes`。
3. 修改 `create_transaction` 保存循环，按上述决策插入转换与 `file_format` 归一化。
4. 更新 `tests/backend/test_attachment_storage_layout.py`：PNG 用例断言 `.jpg` 后缀与 JPEG 字节；新增损坏 PNG 失败回退用例。
5. 运行 Backend 测试集（`pytest tests/backend/`）确认全绿。
6. 部署后对线上历史 PNG 文件不做迁移；新上传自动按新规则落盘。

## Open Questions

无。`quality` 参数当前固定为 92，未做配置化，未来若有调优需求可提取到 `Settings`。
