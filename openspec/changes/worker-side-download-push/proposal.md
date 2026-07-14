# Proposal: Worker 端接管下载与推送，移除 Device Agent APK

## Summary

将事务附件的下载职责从 Android Device Agent APK 迁移到 Worker 桌面端。Worker 直接从 Backend 拉取签名 URL，下载文件到本地临时目录，校验 MD5 后通过 `adb push` 推送到手机 `/sdcard/3is/{transaction_id}/` 目录下。同时移除 Device Agent APK 以及相关的 Socket 通信、download-ack REST 接口。

## Motivation

当前架构（见 `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md`）中，Device Agent APK 承担附件下载职责，为此维护了 ~702 行 Kotlin 代码（10 个文件）：Downloader、SocketClient、BackendApi、SandboxManager、Foreground Service、状态机、权限申请、通知渠道等。这与新架构"Worker 端执行 + Device 极简化"的设计方向相矛盾：

1. **复杂度下沉错误**：RPA 执行已回归 Worker，但下载逻辑仍留在 Device。Device 为"下载器 + ADB 目标"，但下载器本身可以由 Worker 一行 `requests.get()` + 一行 `device.push()` 替代
2. **跨进程协作开销**：Socket 指令 -> Device 下载 -> Socket ACK -> REST download-ack，涉及双通道确认、跨语言 JSON 解析、Android 进程生命周期管理
3. **错误处理分散**：URL 过期需 Device 检测后回传 Worker 续签，MD5 校验失败需跨进程传递，调试需 `adb logcat`
4. **"不中转字节流"原则前提已消失**：该原则诞生于 V1.1（Worker 作为远程/局域网节点）。新架构下 Worker 通过 USB 直连 Device，`adb push` 走 USB 通道不占用网络带宽
5. **调试便利性未最大化**：文档 §1.2 明确"脚本在桌面 Python 进程执行，可直接用 PyCharm/VSCode 断点调试"，下载逻辑也应享受同样便利

## User Impact

- **RPA 开发/运维**：下载逻辑全部在 Worker Python 进程内，可断点调试；无需再维护 Android APK 工程
- **站点部署**：部署链路简化为 Worker + 手机（USB 线），无需安装/授权 Device Agent APK
- **后端**：移除 `POST /devices/{id}/download-ack` 接口，Worker 直接推进事务状态

## Scope

### In Scope

- Worker 新增 `FileDownloader` 模块：HTTP 下载 -> MD5 校验 -> 临时文件管理
- Worker 新增 `DevicePusher` 模块：`adb push` 到 `/sdcard/3is/{transaction_id}/` 目录 + 沙箱清理
- Worker `main.py` 重写 `dispatch_to_device` 流程：下载 + push 替代 Socket 指令
- Worker 接管 Device 心跳/就绪上报（通过 `adb shell` 采集设备状态，代为调用 Backend API）
- 移除 `android/` 目录下的 Device Agent APK 源码
- 移除 Backend `POST /devices/{id}/download-ack` 接口
- 移除 Worker `device_dispatcher.py`（Socket 服务端）
- 设备沙箱路径从平铺 `/sdcard/3is/<attachment_id>.<ext>` 改为按事务隔离 `/sdcard/3is/{transaction_id}/<attachment_id>.<ext>`

### Out of Scope

- Backend 签名 URL 生成逻辑（`/transactions/{id}/download-urls`）不变
- Backend 状态机核心逻辑不变
- Airtest 执行层（`airtest_executor.py`）不变
- WiFi ADB 支持（仍为 USB MVP）
- `POST /devices/{id}/ready` 和 `POST /devices/{id}/status` 接口本身保留（Worker 代为调用）

## Success Criteria

1. Worker 接收任务后，在单进程内完成：签名 URL 获取 -> HTTP 下载 -> MD5 校验 -> `adb push` -> Airtest 执行
2. 文件推送到 `/sdcard/3is/{transaction_id}/<attachment_id>.<ext>` 路径
3. 事务终态后 Worker 通过 `adb shell rm -rf /sdcard/3is/{transaction_id}/` 清理设备沙箱
4. `android/` 目录 APK 源码被移除，部署不再需要安装 Device Agent APK
5. URL 过期在 Worker 进程内直接续签重试，无需跨进程通信
6. 现有 Airtest 执行流程与 Step 映射不受影响

## Non-Goals

- 不修改 Airtest 脚本内容或 Step 映射规则
- 不引入 WiFi ADB 或远程设备支持
- 不修改 Backend 调度逻辑或 Redis Stream 配置
- 不修改前端 Web 界面
- 不重构 Worker 的 Airtest 执行层
