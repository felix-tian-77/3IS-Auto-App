# Design: RPA 执行架构调整 — Worker 端 Airtest + 极简 Device Agent

| 字段 | 内容 |
|------|------|
| 设计主题 | 3IS-Auto-App RPA 执行架构从 Device 端调整为 Worker 端 |
| 文档版本 | V1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | Draft（待评审） |
| 关联 PRD | `docs/superpowers/specs/2026-06-02-prd-design.md` V1.1 |
| 关联评审 | `docs/superpowers/specs/2026-06-02-prd-review.md` |
| 作者 | brainstorming skill |

**修订记录**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-03 | 初稿（基于 brainstorming 决策） | office-hours |

---

## 1. 设计背景

### 1.1 现状（V1.1 PRD）

V1.1 PRD 规定：

- **Airtest 引擎运行在 Android Device 端**（FR-MOB-003：唤醒 RPA 脚本执行环境）
- **Device Agent 是 RPA 实际执行点**（驱动保险 APP UI 自动化）
- **Worker 仅做指令中转 + 编排**（FR-CLI-005：编排 Flow → Steps）
- **脚本存储** OSS → Worker 缓存 → Device 加载

### 1.2 调整动机

经 2026-06-03 brainstorming 共识：

1. **脚本集中管理诉求**：所有 Flow 脚本只存于 Worker，避免下发到 Device 的复杂性与版本一致性风险
2. **调试便利诉求**：脚本在桌面 Python 进程执行，可直接用 PyCharm/VSCode 断点调试，降低 RPA 维护成本
3. **Device Agent 简化诉求**：将 Device 从"复杂执行器"降级为"下载器 + ADB 目标"，降低 Android 端开发与维护成本
4. **Airtest 原生模式契合**：Airtest 设计哲学即为"桌面 Python 控制手机"，本次调整为回归经典架构

### 1.3 前置约束（已 PoC 验证）

- ✅ **ADB 反检测已 PoC 验证安全**（目标保险 APP 对 ADB 注入无检测反应）
- ✅ **USB 物理连接作为 MVP 控制链路**
- ✅ **业务类型由用户提交时显式指定**（V1.1 决议，无需 OCR）

### 1.4 调整影响

本次调整为**架构级偏移**，触达 V1.1 PRD 13 处内容。详见第 6 章。

---

## 2. 新架构总览

### 2.1 架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                          云端 (Backend)                               │
│  - 事务接入/路由 (FR-SVR-001~003)                                      │
│  - 调度中心 (Redis Stream Consumer Group)                              │
│  - 状态机管理 (FR-SVR-008)                                            │
│  - OSS 签名 URL 生成与续签                                             │
└─────────────────┬────────────────────────────────────────────────────┘
                  │ HTTPS REST + WSS (outbound from Worker)
                  │
┌─────────────────▼────────────────────────────────────────────────────┐
│                   Worker 桌面端 (Python 3.14 + UV)                     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Airtest Runtime 进程池  (本机 CPU 跑 UI 自动化)               │    │
│  │  - 脚本存储: ~/.3is-auto/flows/{flow_id}/{version}/           │    │
│  │  - 图像识别: POCO / airtest.core                              │    │
│  │  - ADB Driver: airtest.core.android.adb                       │    │
│  │  - 截图存储: ~/.3is-auto/sandbox/{txn_id}/screenshots/        │    │
│  │  - 不缓存输入影像（Device 直连 OSS）                            │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  RPA 编排执行器 (FR-CLI-005 升级: 编排 + 执行)                │    │
│  │  - 接收 TASK_DISPATCH                                         │    │
│  │  - 调 /oss-urls 拿签名 URL                                     │    │
│  │  - Socket 通知 Device 下载（Device 直连 OSS）                  │    │
│  │  - 启动 Airtest 流程                                          │    │
│  │  - 按 Step 顺序执行 Airtest API                                │    │
│  │  - Retry Policy / Step 超时熔断                                │    │
│  │  - 上报结果到 Backend                                          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  USB 物理连接 (1 根线 = 1 Device, 单 Worker 限制 2-3 Device)           │
│  ┌──────┐  ┌──────┐  ┌──────┐                                        │
│  │Dev-A │  │Dev-B │  │Dev-N │  N ≤ 3                                │
│  └──────┘  └──────┘  └──────┘                                        │
└──────────────────────────────────────────────────────────────────────┘
                  ▲
                  │ ADB (USB)
                  │
┌─────────────────┴────────────────────────────────────────────────────┐
│           Android Device + Device Agent (极简化)                      │
│  - Socket 监听 :8765 (白名单 IP)                                      │
│  - HTTPS REST: ready / status / download-ack                          │
│  - 直连 OSS 签名 URL 下载影像到本地                                    │
│  - 通过 ADB 暴露给 Worker (无需 Agent App 处理 RPA)                    │
│  - 目标保险 APP 仍需安装 (被 Worker Airtest 控制)                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 三端职责对照

| 维度 | Backend（云端） | Worker（桌面端） | **Device Agent（Android）** |
|------|----------------|----------------|-----------------------------|
| 角色 | 调度/编排中心 | **编排 + 实际执行** | **下载器 + ADB 目标** |
| 语言 | Python（隐含） | Python ≥ 3.14 | Android 原生（Kotlin/Java） |
| 核心框架 | FastAPI/Django | **Airtest + POCO** | 极简 HTTP/Socket 客户端 |
| 持有 Flow 脚本 | ✅（OSS） | ✅（本地缓存） | ❌（不持有） |
| 持有输入影像 | ❌（不中转字节流，V1.1 原则） | ❌（不缓存输入影像） | ✅（直连 OSS 下载到 `/sdcard/3is/<attachment_id>.<ext>`，事务后清理；R3 简化为平铺根目录） |
| 持有 Airtest 截图 | ❌ | ✅（`~/.3is-auto/sandbox/{txn_id}/screenshots/`，仅供审计） | ❌ |
| UI 自动化 | ❌ | ✅（Airtest 驱动） | ❌ |
| 状态机管理 | ✅（强一致） | ❌ | ❌ |
| Step 重试决策 | 事务级 | Step 级 | ❌ |
| 网络方向 | 入站 443 | 出站 443 | **入站 Socket 8765 + 出站 443（OSS）** |

### 2.3 关键不变量

- **OSS 直连下载原则不变**：Device Agent 仍直连 OSS 签名 URL，Worker 不中转文件字节流
- **CONFIRM 流程移除不变**：V1.1 决议仍生效，CONFIRM Step 退化为普通 Step
- **业务类型用户指定不变**：V1.1 决议仍生效
- **Redis Stream MVP 必需不变**：调度层不调整

---

## 3. Device Agent 改造

> **本章基线（实现状态,2026-06-15 同步）**：Device Agent 已实现为 **Android APK（`android/` 目录）**,运行 Foreground Service（`com.threeis.deviceagent.service.DeviceAgentService`,状态机含 `INITIALIZING` / `READY` / `DOWNLOADING` / `BUSY` / `OFFLINE` 等）。Device 直连 OSS 签名 URL,把附件落到 `/sdcard/3is/<attachment_id>.<ext>`,再通过同一 TCP Socket(`adb reverse tcp:8765 tcp:8765`)向 Worker 发 `DOWNLOAD_COMPLETE` 确认。`android/scripts/adb_install.sh` 完成构建 → 安装 → `MANAGE_EXTERNAL_STORAGE` 授权 → `adb reverse` → 拉起 MainActivity 的端到端引导。

### 3.1 移除的功能（V1.1 → 新架构）

| V1.1 中 Device 做的事 | 新架构 |
|----------------------|--------|
| 唤醒 Airtest 运行环境（FR-MOB-003） | ❌ 移除 |
| 接收 Step 指令并执行 | ❌ 移除（Worker 通过 ADB 直接执行） |
| 截图、UI 自动化 | ❌ 移除 |
| 上报 `step-result`（FR-MOB 执行结果） | ❌ 移除 |
| Android 沙箱 + FileProvider（FR-MOB-004） | ⚠️ 简化为 **`/sdcard/3is/<attachment_id>.<ext>`** 平铺沙箱,Device 直连 OSS 下载后存储（**不通过 Worker 中转**）。文件名以 `attachment_id` 为准,**不再**带事务级子目录与 `file_type` 前缀（R3 简化） |

### 3.2 保留的功能

| 功能 | 协议 | 说明 |
|------|------|------|
| Socket 监听 :8765（白名单 IP） | TCP | 接收 Worker 下载指令 |
| `POST /api/v1/devices/{id}/ready` | HTTPS REST | 启动就绪上报 |
| `POST /api/v1/devices/{id}/status` | HTTPS REST | 心跳：电量/存储/锁屏 |
| `POST /api/v1/devices/{id}/download-ack` | HTTPS REST | **新增**：下载完成通知 |
| `POST /api/v1/oss-urls/{id}/refresh` | HTTPS REST | OSS URL 续签 |
| 直连 OSS 签名 URL 下载 | HTTPS 443 出站 | 影像文件下载到 `/sdcard/3is/<attachment_id>.<ext>`(`attachment_id` 与 `ext` 取自 `DOWNLOAD_FILES.oss_urls[]` 元素,R3 简化) |

### 3.3 设备接口（PRD §6.2.3 重写）

```http
# 启动时上报
POST /api/v1/devices/{id}/ready
Content-Type: application/json
Authorization: Bearer {device_token}

{
  "battery_level": 85,
  "storage_free_mb": 12000,
  "screen_locked": false,
  "android_version": "13"
}
```

```http
# 30s 周期心跳
POST /api/v1/devices/{id}/status
Authorization: Bearer {device_token}

{
  "battery_level": 84,
  "storage_free_mb": 11800,
  "screen_locked": false,
  "current_transaction_id": "TXN-20260603-00001",
  "last_seen_at": "2026-06-03T10:00:30Z"
}
```

```http
# 新增：下载完成通知
POST /api/v1/devices/{id}/download-ack
Authorization: Bearer {device_token}

{
  "transaction_id": "TXN-20260603-00001",
  "files": [
    {
      "attachment_id": "att_a1b2c3d4e5f6",
      "md5": "a1b2c3d4e5f6...",
      "local_path": "/sdcard/3is/att_a1b2c3d4e5f6.jpg",
      "ext": "jpg",
      "size_bytes": 1024000
    }
  ],
  "completed_at": "2026-06-03T10:00:25Z"
}
```

**接口变化**：
- ❌ 移除 `GET /api/v1/devices/{id}/files`（不再由 Device 主动获取，改由 Worker 下发）
- ❌ 移除 `POST /api/v1/devices/{id}/step-result`（不再由 Device 执行 Step）
- ✅ 新增 `POST /api/v1/devices/{id}/download-ack`

### 3.4 Socket 协议简化（PRD §6.3）

```json
// Worker → Device (LAN Socket :8765,经 adb reverse 转发)
{
  "cmd": "DOWNLOAD_FILES",
  "params": {
    "transaction_id": "TXN-20260603-00001",
    "oss_urls": [
      {
        "attachment_id": "att_a1b2c3d4e5f6",
        "url": "https://oss.example.com/xxx?id=xxx&signature=xxx",
        "md5": "a1b2c3d4e5f6...",
        "ext": "jpg",
        "expires_at": "2026-06-03T10:05:00Z"
      },
      {
        "attachment_id": "att_b2c3d4e5f6a7",
        "url": "https://oss.example.com/yyy?id=yyy&signature=yyy",
        "md5": "b2c3d4e5f6a7...",
        "ext": "pdf",
        "expires_at": "2026-06-03T10:05:00Z"
      }
    ]
  }
}

// Device → Worker
{
  "event": "DOWNLOAD_COMPLETE",
  "transaction_id": "TXN-20260603-00001",
  "files": [
    {
      "attachment_id": "att_a1b2c3d4e5f6",
      "md5": "a1b2c3d4e5f6...",
      "local_path": "/sdcard/3is/att_a1b2c3d4e5f6.jpg",
      "ext": "jpg",
      "size_bytes": 1024000
    }
  ]
}

{
  "event": "OSS_URL_EXPIRED",
  "signed_url_id": "uuid-xxx"
}
```

**协议变化**：
- ❌ 移除 `EXECUTE_STEP` 指令（Device 不再执行 Step）
- ❌ 移除 `STEP_RESULT` 事件（Device 不再上报 Step 结果）
- ✅ `oss_urls[]` 元素新增 **`attachment_id`（string,Backend 下发的附件唯一 ID）** 与 **`ext`（string,取 `jpg` / `png` / `pdf` 之一）**;`DOWNLOAD_COMPLETE.files[]` 元素同样回带 `attachment_id` 与 `ext` 供 Worker 校验与日志关联
- ✅ 移除 `oss_urls[].file_type` 字段——文件类型信息已通过 `transaction.attachments_meta` 在事务级别携带,不需要在下载协议里重复（R3 简化）
- ✅ 仅保留 `DOWNLOAD_FILES` / `DOWNLOAD_COMPLETE` / `OSS_URL_EXPIRED`

### 3.5 设备实体变更（PRD §5.2）

| 字段 | 类型 | 说明 | 变更 |
|------|------|------|------|
| device_id | String PK | Device 唯一 ID | 不变 |
| sn | String(64) UK | 设备 SN/UDID | 不变 |
| worker_id | String FK | 挂载的 Worker | 不变 |
| adb_serial | String | ADB 序列号 | **新增**（Worker 通过此连接 ADB） |
| sandbox_path | String | 临时沙箱路径，默认 `/sdcard/3is/`（平铺目录,文件名规则 `<attachment_id>.<ext>`;R3 简化后**不再**有事务级子目录） | **新增** |
| model | String | 设备型号 | 不变 |
| android_version | String | Android 版本 | 不变 |
| battery_level | Int | 电量（0-100） | 不变 |
| storage_free_mb | Int | 剩余存储（MB） | 不变 |
| screen_locked | Boolean | 是否锁屏 | 不变 |
| status | Enum | ONLINE/OFFLINE/BUSY/DISABLED | 不变 |
| current_transaction_id | String | 当前占用事务 | 不变 |
| last_seen_at | DateTime | 最后一次状态上报时间 | 不变 |

### 3.6 安全与清理

| 机制 | 说明 |
|------|------|
| **白名单 IP** | Socket :8765 仅接受站点固定 IP 段（不变） |
| **OSS 签名 URL 临时性** | TTL ≤ 5min，Bucket Policy 限制（不变） |
| **设备侧文件清理** | 事务终态后由 Worker 通过 ADB 触发 `adb shell rm -rf /sdcard/3is/` 清理 Device 端输入影像（R3 简化为平铺目录,直接清根目录即可） |
| **Worker 端截图清理** | 事务完成后清理 `~/.3is-auto/sandbox/{txn_id}/screenshots/`（Worker 本地 Airtest 截图，不含输入影像） |
| **设备端 App 包大小** | 从 ~50MB 降至 ~5MB（无 Airtest runtime） |
| **Device 端沙箱位置** | `/sdcard/3is/` 是**显式**的设备侧共享沙箱,跨 APP 可读是**为适配目标保险 APP 直读影像**而做出的**有意例外**——本工具的内部约定,**不是**通用隔离策略。其他模块应继续走 APP 私有目录（`context.filesDir`）做隔离;新增子模块若也想使用 `/sdcard/3is/` 模式需单独评审 |

---

## 4. Worker 改造

### 4.1 新增模块

| 模块 | 职责 | 关键依赖 |
|------|------|----------|
| **Airtest Engine Manager** | Airtest 进程池管理（每 Device 一个 runtime） | `airtest`, `pocoui` |
| **ADB Connection Manager** | USB ADB 连接池 + 重连机制 | `airtest.core.android.adb` |
| **Local Sandbox** | Airtest 截图本地存储（不缓存输入影像，遵循 V1.1"Worker 不中转字节流"原则） | 本地 FS |
| **Step Executor** | 解析 Step 定义，调用 Airtest API 执行 | 自研 Step → Airtest API 映射层 |
| **Result Reporter** | Step 结果 + 截图 + 耗时上报 Backend | `requests` |
| **Retry Policy Engine** | Step 级重试（默认 3 次，指数退避） | 自研 |

### 4.2 执行流程（重写）

```
[阶段 1-3 启动/心跳/脚本同步 与 V1.1 相同，省略]

阶段 4：任务接收与执行（重写）

4.1  WebSocket /ws/v1/dispatch 收到 TASK_DISPATCH
4.2  POST /api/v1/tasks/{id}/ack
4.3  POST /api/v1/transactions/{id}/oss-urls → 拿到 signed_urls[]
4.4  启动 Airtest Runtime: connect_device("android:///{adb_serial}")
4.5  解析 Flow 定义 (从 ~/.3is-auto/flows/{flow_id}/{version}/)
4.6  ── Socket:8765 ──► Device: DOWNLOAD_FILES {oss_urls: [{attachment_id, url, md5, ext, ...}]}
4.7  Device 直连 OSS 下载到 /sdcard/3is/<attachment_id>.<ext>（文件名取自协议,见 §3.4）
4.8  Device 完成 → POST /devices/{id}/download-ack（含 attachment_id 列表与 MD5）
4.9  Worker 收到下载完成 → 事务进入 RUNNING
4.10 ── 可选 ── Worker 校验 Device 沙箱（基于 download-ack 上报的 MD5 比对）
4.11 按 Step 顺序执行:
       Step1 OPEN_APP     → start_app(package_name)
       Step2 UPLOAD       → touch(template_image)  # 上传身份证
       Step3 INPUT        → text("13800001234")     # 输入手机号
       Step4 UPLOAD       → touch(template_image)  # 上传行驶证
       Step5 CLICK        → touch((x, y))           # 点击提交
       Step6 SCREENSHOT   → snapshot(filename=...)
4.12 每 Step 完成 → 截图本地 (~/.3is-auto/sandbox/{txn_id}/screenshots/) + 上报 Backend
4.13 Step 失败 → Retry Policy (3 次, 指数退避 1s/2s/4s)
4.14 Step 超时 (60s) → 熔断 → 失败截图推 Dashboard (FR-SVR-018)
4.15 全部 Step 完成 → POST /tasks/{id}/result
4.16 清理:
       - Worker: 清理 ~/.3is-auto/sandbox/{txn_id}/screenshots/（Airtest 截图）
       - Device: adb shell rm -rf /sdcard/3is/（输入影像,平铺目录直接清根）
       - disconnect_device()

阶段 5：结果回传（与 V1.1 相同，省略）

阶段 6：异常与恢复（重写）
- ADB 断开 → adb reconnect offline → 事务回退 PENDING
- Airtest 截图失败 → Step 失败 → Retry Policy
- 目标 APP 异常退出 → 启动 APP 重试
- USB 物理断开 → 运维告警 → 事务回退 PENDING
```

### 4.3 脚本管理（FR-CLI-007 简化）

**变化**：脚本不再下发到 Device

- **存储路径**：`~/.3is-auto/flows/{flow_id}/{version}/script.py`（不变）
- **设备缓存**：无（Device 不持有脚本）
- **设备 Agent App 包大小**：减小 50%+
- **脚本热更新**：改完直接重启 Airtest 进程，Device 无需操作
- **版本校验**：仍通过 `GET /api/v1/workers/scripts/versions` 校验

### 4.4 ADB 连接管理

| 关注点 | 设计 |
|--------|------|
| 连接方式 | USB ADB 物理连接（`adb devices` 自动发现） |
| 多 Device | **单 Worker 限制 2-3 Device**（CPU 瓶颈） |
| 断开重连 | 心跳检测 + `adb reconnect offline` + 事务回退 PENDING |
| 设备授权 | USB 调试首次需人工确认（运维一次性操作） |
| Airtest 连接 | `connect_device("android:///{adb_serial}")` |
| 截图路径 | `/sdcard/Pictures/airtest/` 临时，事务完成清理 |

### 4.5 沙箱机制

| 位置 | 路径 | 用途 | 数据流向 |
|------|------|------|----------|
| Worker 本地 | `~/.3is-auto/sandbox/{txn_id}/screenshots/` | Airtest 截图取证 | **Worker → 本地**（adb pull 或本地 snapshot） |
| Device 临时 | `/sdcard/3is/<attachment_id>.<ext>` | 保险 APP 读取输入影像 | **OSS → Device**（Device 直连下载，**不经 Worker**） |

**设计原则**：
- **输入影像**：Device Agent 直连 OSS 签名 URL 下载到 Device 沙箱，**Worker 不缓存、不中转**（延续 V1.1 原则）。R3 简化后沙箱改为平铺的 `/sdcard/3is/` 根目录,文件名 `<attachment_id>.<ext>`——去除了事务级子目录与 `file_type` 前缀,降低目录与协议复杂度
- **Airtest 截图**：Worker 端 Airtest runtime 通过 `snapshot()` / `adb pull` 存到本地沙箱，仅供审计与失败回溯
- **清理触发**：事务终态后由 Worker 统一触发两侧清理（Worker 本地 rm + adb shell `rm -rf /sdcard/3is/`）

**隔离边界（重要,R3 例外）**：

`/sdcard/3is/` 位于 Android 外部存储共享区,**默认对其它 APP 可见**——这是**本工具明确选择的例外**(目标保险 APP 需要直接读取该目录下的影像文件,继续走 FileProvider 中转会引入额外的 content URI 解析开销与权限握手),**不是**通用隔离策略。新增子模块若想使用同样的共享目录模式,需要单独评审;默认应继续走 APP 私有目录(`context.filesDir`)。Worker ↔ Device 的网络边界由白名单 IP + `adb reverse` 共同保证（见 §3.6）。

### 4.6 Step → Airtest API 映射

| Step.action_type | Airtest API | 说明 |
|------------------|-------------|------|
| OPEN_APP | `start_app(package_name)` | 启动目标保险 APP |
| INPUT | `text("13800001234")` | 文本输入 |
| UPLOAD | `touch(template_image)` + 系统文件选择 | 上传影像（坐标点击） |
| CLICK | `touch((x, y))` 或 `touch(template_image)` | 坐标/图像点击 |
| SCREENSHOT | `snapshot(filename=...)` | 截图取证 |
| WAIT | `sleep(seconds)` 或 `wait(template, timeout=...)` | 等待元素 |
| ~~CONFIRM~~ | ~~无对应~~ | **V1.1 起移除，CONFIRM Step 退化为普通 Step** |

---

## 5. 技术栈变更

### 5.1 Worker 端技术栈

| 组件 | V1.1 PRD | **新架构** | 备注 |
|------|----------|-----------|------|
| **核心语言** | Python ≥ 3.14 + UV | Python ≥ 3.14 + UV | 不变 |
| **RPA 引擎** | 无（仅编排） | **Airtest（执行）** | **新增** |
| **POCO 库** | 无 | **pocoui** | **新增**（图像识别 + 控件操作） |
| **ADB 库** | 无（用 Android SDK） | **airtest.core.android.adb** | **新增**（封装 ADB） |
| **HTTP 客户端** | requests | requests | 不变 |
| **WebSocket 客户端** | websockets | websockets | 不变 |
| **Socket 服务端（接收 Device 上报）** | - | socket | **新增**（或与现有 Socket 共用） |

### 5.2 Device Agent 端技术栈

| 组件 | V1.1 PRD | **新架构** | 备注 |
|------|----------|-----------|------|
| **Android 系统** | ≥ 10 | ≥ 10 | 不变 |
| **Device Agent App** | Android 原生 + Airtest Android Runtime | **Android 原生（极简）** | 移除 Airtest runtime |
| **HTTP 客户端** | OkHttp/Retrofit | OkHttp/Retrofit | 不变 |
| **Socket 客户端/服务端** | Socket :8765 | Socket :8765 | 不变 |
| **OSS 下载** | HTTPS 客户端 | HTTPS 客户端 | 不变 |
| **目标保险 APP** | 第三方 | 第三方 | 不变（被 Worker Airtest 控制） |

### 5.3 硬件要求调整

| 资源 | V1.1 PRD | **新架构 MVP** | 理由 |
|------|----------|----------------|------|
| **Worker CPU** | 4 核 | **8 核** | 多 Device 并发跑 Airtest |
| **Worker 内存** | 8 GB | **16 GB** | Airtest 进程 + 图像处理 |
| **Worker 存储** | 100 GB SSD | 100 GB SSD | 脚本 + 沙箱 + 日志 |
| **Worker 单价** | ¥300/月 | **¥600/月** | 配置翻倍 |
| **单 Worker Device 数** | 4-6 | **2-3** | CPU 瓶颈（已验证） |
| **Device Android 版本** | ≥ 10 | ≥ 10 | 不变 |
| **Device 硬件** | 中高端 | 中低端可（无 Airtest runtime） | 简化 |
| **USB 接口** | 1/Device | 1/Device | 不变 |
| **带宽** | ≥ 20 Mbps 上行 | ≥ 20 Mbps 上行 | 不变 |

### 5.4 容量规划（受限调整）

| 维度 | V1.1 MVP | **新架构 MVP** | 中期 |
|------|----------|----------------|------|
| 单站点 Worker 数 | 1 | **2-3**（每 Worker 限 2-3 Device） | 4-6 |
| 单站点 Device 数 | 2-6 | **4-9**（2-3 Worker × 2-3 Device） | 8-18 |
| 日处理事务量 | 500 | **300-500**（ATT 延长 50%） | 2000 |
| 单事务 ATT | 3-5 min | **5-8 min** | 同 MVP |
| 单 Worker 并发事务 | 4-6 | **2-3** | 同 MVP |
| API 限流 | 销售 60/min | **销售 40/min**（ATT 延长） | 提升 |

---

## 6. PRD V1.1 修改清单

### 6.1 必须修改的 13 处

| 序号 | 章节 | 改动内容 | 工作量估算 |
|------|------|----------|------------|
| 1 | §3.1 主流程图 | 重画为 Worker 通过 ADB 控制 Device | 1h |
| 2 | §3.4 状态机 | 新增子状态 `ADB_CONNECTING` | 1h |
| 3 | §3.5 异常分支 | 新增：ADB 断开重连、Airtest 失败、USB 物理断开 | 1h |
| 4 | §4.2 FR-CLI-005 | 升级为"编排+执行"角色描述 | 2h |
| 5 | §4.3 FR-MOB-001~006 | **重写 6 个移动端需求**（移除 Airtest 执行相关） | 4h |
| 6 | §5.2 Device 实体 | 新增 `adb_serial`、`sandbox_path` 字段 | 0.5h |
| 7 | §6.2.3 设备接口 | 从 4 个简化为 3 个 + 1 个新增（download-ack） | 1h |
| 8 | §6.3 Socket 通道 | 移除 Step 相关指令，保留下载控制 | 0.5h |
| 9 | §7.2/7.5 部署/硬件 | Worker 规格上调（8C 16GB）；Device 规格下调 | 1h |
| 10 | §8.1 性能 | ATT 调整为 5-8min；并发 2-3 Device/Worker | 1h |
| 11 | §9 技术约束 | 新增 `airtest` `pocoui` `airtest.core.android.adb` | 0.5h |
| 12 | §10.3 测试策略 | L4 录屏回归更关键（脚本在 Worker） | 1h |
| 13 | §11.1 风险 | 移除"ADB 反检测"风险（已 PoC 验证）；新增"Worker CPU 瓶颈" | 1h |
| **总工作量** | | | **~16h** |

### 6.2 文档结构变化

| 章节 | V1.1 | 新架构 |
|------|------|--------|
| §1.3 价值主张 | 3-5 分钟（RUNNING） | **5-8 分钟**（RUNNING） |
| §1.4 范围边界 | - | 新增限制：单 Worker 2-3 Device |
| §3.0 主流程图 | Device 端执行 | Worker 端通过 ADB 执行 |
| §3.6 业务连续性 | 增加"USB 断开 → 事务回退 PENDING" | 增加"Worker 进程崩溃 → 所有 Device 事务回退" |

---

## 7. 状态机扩展

### 7.1 状态机图

```
PENDING → DISPATCHED → ADB_CONNECTING → DOWNLOADING → READY → RUNNING → SUCCESS
                                            │                          → FAIL
                                            │                              → RETRY → RUNNING
                                            │                              → DLQ
                                            ↓
                                       (download fail)
                                            → FAIL
```

### 7.2 状态变更说明

| 状态 | 触发条件 | 说明 |
|------|----------|------|
| PENDING | 事务创建，校验通过 | 等待调度 |
| DISPATCHED | 调度中心分配 Worker+Device | 任务已下发 |
| **ADB_CONNECTING** | **Worker 启动 Airtest runtime 连接 ADB** | **新增**：ADB 握手阶段 |
| DOWNLOADING | Device 开始下载影像 | 资料传输中 |
| READY | Device 下载完成，Worker 准备执行 | **新增**（可选） |
| RUNNING | Worker Airtest 开始执行 | 自动化操作中 |
| SUCCESS | RPA 执行完成 | 正常终态 |
| FAIL | 执行异常 | 可重试 |
| DLQ | 连续失败或超时 | 死信队列 |

---

## 8. 风险与缓解

### 8.1 移除的风险（V1.1 → 新架构）

| 原风险 | 移除原因 |
|--------|----------|
| ADB 反检测导致事务 FAIL | **已 PoC 验证，目标保险 APP 对 ADB 注入无检测** |

### 8.2 新增的风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| **Worker CPU 瓶颈** | 并发能力下降，单 Worker 仅 2-3 Device | 高 | 接受限制；扩容 Worker 数量；监控 CPU 阈值 |
| **单事务 ATT 延长 50%** | 从 3-5min 到 5-8min | 高 | 业务方接受；优化 Airtest 脚本；ADB 性能调优 |
| **Worker 故障域扩大** | 1 Worker 故障 = 2-3 Device 事务中断 | 中 | 限制单 Worker 负载；快速故障检测（心跳 30s） |
| **USB 物理连接不稳定** | 接触不良导致 ADB 断开 | 中 | 优质 USB 线材；ADB 自动重连；事务回退 PENDING |
| **Airtest 截图/图像识别失败** | UI 变化导致 Step 失败 | 中 | L4 录屏回归测试；Step 重试机制；快速脚本更新 |
| **Device Agent 与 Airtest 版本不匹配** | 兼容性问题 | 低 | Device Agent 简化（无 Airtest runtime），风险降低 |

### 8.3 保留的风险（与 V1.1 相同）

- 保险 APP UI 变更导致脚本失效（L4 录屏回归缓解）
- Android 系统升级导致兼容问题（Device Controller 抽象层缓解）
- 大量并发导致 Redis Stream 阻塞（监控告警）
- 业务类型误选（用户提交时强制二次确认）
- 影像文件体积过大（文件压缩 + 超时熔断）

---

## 9. 性能与成本影响

| 维度 | V1.1 | **新架构** | 评估 |
|------|------|-----------|------|
| 单事务 ATT | 3-5 min | **5-8 min** | 🟡 -50% |
| 单 Worker 并发 Device | 4-6 | **2-3** | 🟡 -50% |
| Worker 单价 | ¥300/月 | **¥600/月** | 🟡 +100% |
| 单站点 Worker 数 | 1 | **2-3** | 🟡 +200% |
| 单站点月成本 | ¥300 | **¥1200-1800** | 🟡 +300-500% |
| Device 端 App 包大小 | ~50MB | **~5MB** | ✅ -90% |
| 调试便利性 | 复杂（Device 端） | **简单（桌面 IDE）** | ✅ 显著提升 |
| 脚本更新延迟 | 需下发到 Device | **Worker 重启即生效** | ✅ 显著提升 |
| 维护成本 | Device 端 SDK 升级频繁 | **Worker 端统一升级** | ✅ 显著降低 |
| 单事务 ROI | 高 | **中**（成本上升 3-5x） | 🟡 需业务方接受 |

### 9.1 业务影响总结

- **优点**：脚本集中、调试方便、Device 简化、维护成本降低
- **缺点**：硬件成本上升 3-5x，单事务耗时延长 50%
- **业务可接受性**：需业务方签字接受"5-8 分钟 ATT + 单 Worker 2-3 Device"

---

## 10. 验收标准

### 10.1 功能验收（新增）

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| AC-NEW-001 | Worker 端 Airtest 执行 | Step 100% 在 Worker 端 Airtest runtime 中执行，Device 不再执行 RPA |
| AC-NEW-002 | Device Agent 极简化 | Device Agent App 包大小 ≤ 5MB（不含 Airtest runtime） |
| AC-NEW-003 | USB ADB 连接 | Worker 通过 `adb devices` 自动发现并连接 USB Device |
| AC-NEW-004 | ADB 握手状态 | 状态机新增 `ADB_CONNECTING` 子状态可见 |
| AC-NEW-005 | 沙箱数据流 | 输入影像：OSS → Device（直连，不经 Worker）；Airtest 截图：Worker Airtest → Worker 本地沙箱 |
| AC-NEW-006 | Device 下载通知 | Device 通过 `POST /devices/{id}/download-ack` 通知 Worker |
| AC-NEW-007 | Step 执行 | Worker Airtest 按 Step.action_type 映射到 Airtest API（OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/WAIT） |
| AC-NEW-008 | 单 Worker 负载 | 单 Worker 同时跑 ≤ 3 Device，CPU 使用率 ≤ 80% |
| AC-NEW-009 | 沙箱清理 | 事务完成后 Worker + Device 两侧沙箱均清理 |
| AC-NEW-010 | Step 重试 | Step 失败重试 3 次（指数退避）由 Worker 端控制 |

### 10.2 非功能验收（更新）

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| NAC-NEW-001 | 单事务 ATT | **5-8 分钟**（仅 RUNNING 阶段） |
| NAC-NEW-002 | 单 Worker 并发 | **2-3 Device/Worker** |
| NAC-NEW-003 | 站点容量 | 2-3 Worker × 2-3 Device = **4-9 Device/站点** |
| NAC-NEW-004 | 调试便利 | Worker 端脚本可用 PyCharm/VSCode 断点调试 |
| NAC-NEW-005 | 脚本更新 | Worker 重启 → Device 立即可用新脚本（无需下发） |

---

## 11. 实施计划

### 11.1 阶段划分

**阶段 1：基础改造（2 周）**
- Worker 新增 Airtest 依赖与运行时
- ADB Connection Manager 实现
- Local Sandbox 实现
- Step → Airtest API 映射层
- 单元测试与 L4 录屏回归测试

**阶段 2：Device Agent 极简化（1 周）**
- 移除 Airtest Android Runtime
- 新增 `POST /devices/{id}/download-ack` 接口
- 简化 Socket 协议（移除 Step 相关）
- Device 端沙箱简化为临时目录

**阶段 3：状态机与异常处理（1 周）**
- 新增 `ADB_CONNECTING` 状态
- ADB 断开重连机制
- Worker 进程崩溃事务回退
- USB 物理断开检测

**阶段 4：性能调优与验收（1 周）**
- 压测单 Worker 2-3 Device 负载
- ATT 调优至 5-8 分钟
- L4 录屏回归测试 100 条样本
- 业务方签字验收

**总工作量：5 周 / 1 人**

### 11.2 落地步骤

1. **Week 1**：Worker 端 Airtest 集成 + 沙箱 + ADB 管理
2. **Week 2**：Step 执行器 + Retry Policy + Result Reporter
3. **Week 3**：Device Agent 极简化改造 + 协议精简
4. **Week 4**：状态机扩展 + 异常处理 + 监控告警
5. **Week 5**：性能压测 + L4 录屏回归 + 业务方验收

### 11.3 回滚方案

若新架构 PoC 失败（ADB 性能不达标 / 业务方不接受成本）：
- 保留 V1.1 设备端 Airtest 架构作为 Plan B
- 关键设计资产（Airtest 框架、Step 映射层）可复用
- 回滚成本：~8h（恢复 V1.1 接口与协议）

---

## 12. 开放问题

待 V1.0 进入 Review 前与业务方确认：

- **Q1.** 业务方是否接受"5-8 分钟 ATT + 单 Worker 2-3 Device"？（决定 MVP 范围）
- **Q2.** 单站点月成本从 ¥300 升至 ¥1200-1800 是否在预算内？（影响 §9 成本上限）
- **Q3.** 多站点推广时，是否有运维能力支撑每站点 2-3 Worker 的维护？（影响 SLA）
- **Q4.** Airtest 脚本编写规范是否需要统一？（影响 FR-SVR-016 流程脚本上传）
- **Q5.** 是否需要 WiFi ADB 支持（除 USB 外）作为扩展能力？（影响 §6 接口）

---

## 13. 决策记录

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| RPA 引擎位置 | Device 端 / Worker 端 | **Worker 端** | 脚本集中、调试便利、Device 简化 |
| 控制链路 | USB / WiFi ADB | **USB**（MVP） | 稳定、低延迟、MVP 推荐 |
| ADB 反检测风险 | 接受 / 不接受 | **已 PoC 验证接受** | 目标保险 APP 无检测反应 |
| 单 Worker 负载 | 高 / 中 / 低 | **低（2-3 Device）** | CPU 瓶颈 + 业务方接受 |
| 交付物 | 设计文档 / 直接改 PRD | **设计文档** | 先评审后落地 |
| Device 端 Airtest runtime | 保留 / 移除 | **移除** | 极简 Device Agent |
| 沙箱位置 | Device 端 / Worker 端 | **Device 端（输入影像）+ Worker 端（Airtest 截图），分离存储** | 输入影像不经 Worker 中转 |

---

## 14. 关联文档

- 原始 PRD：`docs/superpowers/specs/2026-06-02-prd-design.md` V1.1
- PRD 评审：`docs/superpowers/specs/2026-06-02-prd-review.md`
- 共识会纪要：2026-06-03 brainstorming（V1.1 7 项决议 + 本次架构调整）
- 待补充：实施计划（writing-plans skill 输出）

---

**文档状态推进路径**：

`Draft`（当前）→ `Review`（业务方/合规方/运维方签字）→ `Approved` → `Frozen`
