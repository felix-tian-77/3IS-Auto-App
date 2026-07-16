## Context

3IS-Auto-App 的 RPA 执行架构已在 `2026-06-03-rpa-worker-side-architecture-design.md` 中从 "Device 端执行" 调整为 "Worker 端 Airtest 执行 + Device 极简 Agent"。但当前实现中，Device Agent APK 仍承担附件下载职责（~702 行 Kotlin / 10 个文件），通过 Socket 接收 `DOWNLOAD_FILES` 指令、直连 OSS 签名 URL 下载、回传 `DOWNLOAD_COMPLETE` ACK + REST `download-ack` 双通道确认。

本次变更将下载职责完全收敛到 Worker 进程内，移除 Device Agent APK，Worker 通过 `adb push` 将文件推送到手机。

### 当前数据流

```
Backend ──签名URL──▶ Worker ──Socket:8765──▶ Device Agent
                        │                        │ HTTPS 直连 OSS
                        │                        ▼
                        │                   /sdcard/3is/{id}.{ext}
                        │                        │
                        │◀──Socket ACK────────────┘
                        │◀──REST download-ack─────┘
                        ▼
                   Airtest 执行
```

### 目标数据流

```
Backend ──签名URL──▶ Worker
                        │
                   1. requests.get(url) -> {WORKER_TMP_DIR}/{txn_id}/{att_id}.{ext}.part
                   2. hashlib.md5 校验 -> 原子重命名为 {att_id}.{ext}
                   3. device.push(local, "{DEVICE_SANDBOX_ROOT}/{txn_id}/{att_id}.{ext}")
                        │
                        ▼
                   Airtest 执行
                        │
                   4. 清理:
                      - adb shell rm -rf {DEVICE_SANDBOX_ROOT}/{txn_id}/
                      - rm -rf {WORKER_TMP_DIR}/{txn_id}/
```

## Goals / Non-Goals

**Goals:**
- Worker 单进程内完成下载 -> 校验 -> push -> 执行全链路
- 移除 Device Agent APK 及其 Socket/REST/Foreground Service 代码
- 移除 Backend `POST /devices/{id}/download-ack` 接口
- 设备沙箱按事务隔离：`/sdcard/3is/{transaction_id}/<attachment_id>.<ext>`
- Worker 接管设备状态采集与上报（通过 `adb shell` + Backend API）

**Non-Goals:**
- 不修改 Airtest 执行层（`airtest_executor.py`）
- 不修改 Backend 签名 URL 生成逻辑
- 不修改前端
- 不引入 WiFi ADB
- 不修改 Redis Stream 调度

## Decisions

### 1. 下载职责位置：Worker 进程内

**选择：** Worker 用 `requests` 下载 + `hashlib` 校验 + `device.push()` 推送

**理由：**
- Worker 已有 ADB push 能力（`device_controller.py:31-33` `push_file()`）
- Worker 已有 `requests` 依赖（用于 Backend API 通信）
- 下载 + 校验 + push 在 Python 中约 30 行代码，替代 Android 端 702 行
- 符合文档 §1.2 "调试便利诉求"：下载逻辑也可断点调试

**备选方案：** 保持 Device Agent 下载（现状）--但需维护 APK 工程、Socket 协议、双通道 ACK

### 2. 设备沙箱路径：按事务隔离

**选择：** `/sdcard/3is/{transaction_id}/<attachment_id>.<ext>`

**理由：**
- 当前平铺结构 `/sdcard/3is/{att_id}.{ext}` 清理时 `rm -rf /sdcard/3is/` 会误删并发事务的文件
- 按事务隔离后，清理只需 `rm -rf /sdcard/3is/{transaction_id}/`，天然支持并发
- 目标保险 APP 通过 Airtest 的文件选择器访问路径，子目录不影响读取

**备选方案：** 保持平铺目录 + 文件名带事务前缀 --命名复杂，清理需精确匹配

### 3. 设备状态上报：Worker 代为采集

**选择：** Worker 通过 `adb shell` 采集设备状态，代为调用 `POST /devices/{id}/ready` 和 `POST /devices/{id}/status`

**理由：**
- `device_controller.py:39-50` 已能获取电量、型号、Android 版本
- `adb shell dumpsys` 可获取存储、锁屏状态
- 无需 Android 端 App 做心跳，Worker 心跳周期内顺带上报设备状态
- Backend `/devices/{id}/ready` 和 `/devices/{id}/status` 接口保留不变，只是调用方从 Device APK 变为 Worker

**备选方案：** 保留极简 APK 仅做心跳 --但 APK 工程维护成本不值得为一个心跳保留

### 4. 移除 `download-ack` 接口

**选择：** 移除 `POST /devices/{id}/download-ack`，Worker 直接推进事务状态

**理由：**
- Worker 下载 + push 成功后，在进程内即可确认完成
- `download-ack` 的职责（回写 `attachment.local_path`、标记事务 `finished_at`、设置设备状态）全部可由 Worker 直接调用 Backend 内部接口或新增 Worker 端点完成
- 消除跨进程双通道确认

**实现方式：** Worker push 成功后调用新增的 `POST /api/v1/transactions/{id}/attachments-delivered`（简化版 ack，由 Worker 调用，body 含 attachment_id + local_path 列表），或直接复用现有 task result 上报链路

**`finished_at` 语义澄清：** 现有 `download-ack` 在下载阶段完成时即设置 `transaction.finished_at = req.completed_at`（`devices.py:79`），但 `finished_at` 在前端列表接口（`transactions.py:120`）中被作为"事务完成时间"展示，语义不一致。本次变更新接口 `attachments-delivered` **不应在下载阶段设置 `finished_at`**，而只回写 `attachment.local_path` 并将事务状态推进至 `READY`。`finished_at` 应在 Airtest 执行结束、事务进入 `SUCCESS`/`FAIL` 终态时才设置（由现有 task result 上报链路负责）。

### 5. 移除 Socket 通信层

**选择：** 移除 `device_dispatcher.py`（Worker Socket 服务端）和 `android/` 下的 `SocketClient.kt`

**理由：**
- 下载职责移除后，Worker 与 Device 之间唯一的通信通道是 ADB（USB）
- `adb reverse tcp:8765 tcp:8765` 不再需要
- Worker config 中 `WORKER_LISTEN_HOST` / `PORT` 配置项可移除

### 6. URL 过期处理：Worker 进程内闭环

**选择：** Worker 下载时检测 HTTP 403/410，直接调用 `POST /api/v1/transactions/{id}/oss-urls/refresh` 续签后重试

**理由：**
- 不再需要 Device 检测 -> 回传 `URL_EXPIRED` -> Worker 续签 -> 重发指令的跨进程往返
- 一个 try/except 内完成检测 + 续签 + 重试

**前提依赖：** `POST /api/v1/transactions/{id}/oss-urls/refresh` 接口目前不存在，需在 Backend 新增（见 tasks §5.5）。`DownloadUrl.refresh_count` 字段已预留（`download_url.py:19`），续签时递增。备选方案：直接复用现有 `POST /transactions/{id}/download-urls` 重新获取全套签名 URL（实现更简单，但会重新生成所有 URL 而非仅过期的那个）。

## Risks / Trade-offs

- **[风险] 大文件下载阻塞 Worker 进程** -> 附件大小限制 ≤ 20MB（现有约束），单文件下载 < 5s，可接受；未来如需异步可加线程池
- **[风险] `adb push` 速度受 USB 2.0 限制** -> USB 2.0 实测 30-40 MB/s，20MB 文件 < 1s，远快于 WiFi 下载
- **[风险] Worker 同时下载 + push 多文件时 CPU 占用** -> 串行下载 push 即可（附件通常 2-5 个），不影响 Airtest 并发
- **[权衡] 违反原"不中转字节流"原则** -> 该原则前提（Worker 作为远程/网络中转节点）已不成立；USB push 不占网络带宽
- **[风险] 移除 APK 后设备状态采集能力下降** -> `adb shell` 可覆盖电量/存储/锁屏/型号等核心指标；Android 端无 App 意味着无法做 Foreground Service 保活，但 Worker 通过 ADB 常驻即可
- **[风险] `POST /devices/{id}/download-ack` 移除影响 Backend 逻辑** -> 需迁移 ack 中的 `attachment.local_path` 回写到新接口或 Worker 上报链路；`finished_at` 不再在下载阶段设置（语义纠正：改为在事务终态 `SUCCESS`/`FAIL` 时设置）

## Architecture Changes

### 移除的组件

| 组件 | 位置 | 行数 | 说明 |
|------|------|------|------|
| DeviceAgentService | `android/.../service/DeviceAgentService.kt` | 175 | Foreground Service + 状态机 |
| SocketClient | `android/.../net/SocketClient.kt` | 121 | TCP 通信 |
| Downloader | `android/.../download/Downloader.kt` | 110 | HTTP 下载 + MD5 |
| BackendApi | `android/.../net/BackendApi.kt` | 76 | REST 上报 |
| MainActivity | `android/.../MainActivity.kt` | 96 | 配置 UI + 权限 |
| Config | `android/.../data/Config.kt` | 53 | SharedPreferences |
| SandboxManager | `android/.../download/SandboxManager.kt` | 25 | /sdcard/3is/ 管理 |
| Models | `android/.../data/Models.kt` | 20 | 数据模型 |
| Application | `android/.../DeviceAgentApplication.kt` | 14 | 入口 |
| Logger | `android/.../util/Logger.kt` | 12 | 日志 |
| DeviceDispatcher | `worker/device_dispatcher.py` | 113 | Worker Socket 服务端 |
| download-ack 接口 | `backend/api/v1/devices.py:47-91` | ~45 | REST ack |

### 新增的组件

| 组件 | 位置 | 说明 | 估行 |
|------|------|------|------|
| FileDownloader | `worker/file_downloader.py` | HTTP 下载 + MD5 校验 + 临时文件管理 | ~80 |
| DevicePusher | `worker/device_pusher.py` | adb push + 沙箱路径管理 + 清理 | ~50 |
| DeviceStatusReporter | `worker/device_status_reporter.py` | adb shell 采集 + 调用 Backend ready/status | ~60 |

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| Worker.main | `worker/main.py` | 重写 `dispatch_to_device`：下载+push 替代 Socket；`run()` 中增加设备状态上报 |
| Worker.config | `worker/config.py` | 移除 `WORKER_LISTEN_HOST`/`PORT`；新增 `DEVICE_SANDBOX_ROOT` |
| DeviceController | `worker/device_controller.py` | 新增 `get_status()` 方法（电量/存储/锁屏） |
| Backend devices.py | `backend/api/v1/devices.py` | 移除 `download-ack` 接口 |

### 新数据流（完整时序）

```
Worker.run() 主循环
    │
    ├── 心跳周期 ──▶ send_heartbeat() + report_device_status()
    │                   (adb shell 采集 -> POST /devices/{id}/status)
    │
    └── poll_tasks() -> 拿到任务
            │
            ├── fetch_download_urls(txn_id)  -> POST /transactions/{id}/download-urls
            │       (拿到 signed_urls[])
            │
            ├── FileDownloader.download_all(signed_urls, txn_id)
            │       ├── requests.get(url) -> {WORKER_TMP_DIR}/{txn_id}/{att_id}.{ext}.part
            │       ├── hashlib.md5 校验 -> 原子重命名为 {att_id}.{ext}
            │       └── 失败(403/410) -> 续签 -> 重试
            │
            ├── DevicePusher.push_files(txn_id, local_files)
            │       ├── adb shell mkdir -p /sdcard/3is/{txn_id}/
            │       ├── device.push(local, /sdcard/3is/{txn_id}/{att_id}.{ext})
            │       └── 记录 local_path 列表
            │
            ├── POST /transactions/{id}/attachments-delivered  (回写 local_path)
            │
            ├── AirtestExecutor.execute_step(...)  x N
            │
            └── 清理:
                    ├── adb shell rm -rf {DEVICE_SANDBOX_ROOT}/{txn_id}/
                    └── rm -rf {WORKER_TMP_DIR}/{txn_id}/
```
