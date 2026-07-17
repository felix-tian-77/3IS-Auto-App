## Why

当前 Backend 保存的附件文件名与 Worker 下载、推送到设备及 Airtest 脚本使用的文件名不一致，导致脚本无法稳定定位图片，且交付回报中的路径无法准确反映实际文件。需要建立 Backend 文件名向 Worker 端透传并端到端保持一致的契约。

## What Changes

- Backend 下载 URL 元数据显式返回附件的 `filename`，以 Backend 存储文件 basename（如 `ID_CARD_FRONT.jpg`）为准。
- Worker 将 `filename` 从任务数据传递至下载器、设备推送器和交付回报逻辑。
- Worker 临时目录和 Android 设备目录使用 Backend 文件名保存和推送图片。
- 更新现有 Airtest 脚本、测试夹具及用户文档，使其使用统一文件名和事务目录结构。
- **BREAKING**：设备端附件路径从基于 `attachment_id` 的命名切换为 Backend 文件名命名，相关消费者和断言需要同步调整。

## Capabilities

### New Capabilities

- `attachment-filename-preservation`: 定义 Backend 附件文件名向 Worker 下载、设备推送和业务脚本端到端保持一致的行为。

### Modified Capabilities

无。

## Impact

- Backend 下载 URL API 响应及附件元数据契约。
- `worker/main.py`、`worker/file_downloader.py`、`worker/device_pusher.py` 及 Airtest 脚本。
- Backend、Worker 单元测试和分发流程测试。
- `docs/user-manu.md` 及相关附件存储/下载说明。
