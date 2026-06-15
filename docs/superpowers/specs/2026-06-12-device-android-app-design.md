# Design: Device 端 Android Agent APP

| 主题 | Device 端 Android Agent APP 设计 |
|------|----------------------------------|
| 日期 | 2026-06-12 |
| 状态 | 待实施 |
| 适用范围 | `android/` 全新工程,删除 `device/` Python 调试代码 |
| 依赖文档 | [`2026-06-03-rpa-worker-side-architecture-design.md`](2026-06-03-rpa-worker-side-architecture-design.md) §3 / §4 |

## 0. 背景与目标

`docs/user-manu.md` §5.1 让用户 `adb install device-app.apk`,但仓库里只有 `device/` 下的 Python 调试脚本,从未存在过 APK 工程。本 spec 定义这个缺口的填补方案:从零创建一个原生 Android Kotlin 工程,产出符合 PRD §3 描述的"极简下载器 + ADB 目标"形态的 Device Agent。

**单一目标:** Worker 通过 Socket 推下载指令时,Device APP 把签名 URL 指向的影像下载到 `/sdcard/3is/` 公共目录,供保险 APP 直接 `File(...)` 访问。

## 1. 架构概览

```
┌──────────────────────────────────────────────────────┐
│              Android Device (受控专用设备)           │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ 3IS Device Agent (com.threeis.deviceagent)     │  │
│  │  - MANAGE_EXTERNAL_STORAGE (公共目录写权限)    │  │
│  │  ┌──────────────┐    ┌────────────────────┐   │  │
│  │  │ MainActivity │───▶│  DeviceAgent       │   │  │
│  │  │ (启动+权限页)│    │  ForegroundService │   │  │
│  │  │              │    │  · onCreate: 擦 3is│   │  │
│  │  └──────────────┘    └─────────┬──────────┘   │  │
│  │           ┌────────────────────┴──────────┐   │  │
│  │           ▼                               ▼   │  │
│  │   ┌─────────────┐               ┌────────────┐│  │
│  │   │SocketClient │               │ Downloader ││  │
│  │   │ (TCP 8765)  │               │ (OkHttp)   ││  │
│  │   └──────┬──────┘               └─────┬──────┘│  │
│  │          │ DOWNLOAD_FILES              │       │  │
│  │          └─▶ [擦 /sdcard/3is/* ]───────┘       │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
              │ Socket                      │ HTTPS
              ▼                             ▼
       ┌────────────┐               ┌────────────┐
       │   Worker   │               │  Backend   │
       └────────────┘               └────────────┘

       /sdcard/3is/                      ← 公共可读, 保险 APP File(...) 直接访问
              ├ idcard.jpg
              ├ phone.jpg
              └ ...                       Device 端自维护(下载前+服务启动时清空)
```

### 1.1 技术选型

| 维度 | 选择 |
|------|------|
| 语言 | Kotlin |
| 构建 | Gradle (Kotlin DSL) + Gradle Wrapper |
| `minSdk` | 24 (Android 7.0) |
| `targetSdk` | 34 (Android 14) |
| `compileSdk` | 34 |
| HTTP | OkHttp 4.x |
| Socket | `java.net.Socket` 原生(不引 Netty/WebSocket) |
| JSON | `org.json.JSONObject`(不引 Moshi/Gson) |
| 异步 | Kotlin Coroutines |
| DI | 无(Service 内手动 new) |
| UI | View XML(无 Compose) |
| 测试 | 首版仅手动 ADB 验证(写到 §5.1) |

### 1.2 关键设计决定

1. **沙箱固定 `/sdcard/3is/`**,无 `{txn_id}` 子目录。下载前 + 服务启动时各清一次。
2. **跨 APP 可见性需要 `MANAGE_EXTERNAL_STORAGE`**:Android 11+ 强制此特殊权限才能在公共目录写文件。设备视为"受控专用设备",这是 PRD §11 多租户隔离原则的**显式例外**。
3. **沙箱清理职责从 Worker 转回 Device**:Worker 端原 `adb shell rm -rf /sdcard/sandbox/{txn_id}` 步骤删除。
4. **同设备同时间最多 1 笔事务**:由 PRD 既定的 "1 Worker ↔ 1 Device" 架构保证,Device 不做并发或排队。

## 2. 模块/类划分

```
android/
├── settings.gradle.kts
├── build.gradle.kts                      # 根工程
├── gradle.properties
├── gradle/wrapper/gradle-wrapper.properties
├── gradlew / gradlew.bat
└── app/
    ├── build.gradle.kts                  # app module (单 module)
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── res/
        │   ├── layout/activity_main.xml
        │   ├── values/strings.xml
        │   ├── values/themes.xml
        │   ├── drawable/ic_notification.xml
        │   └── mipmap-*/ic_launcher.png
        └── java/com/threeis/deviceagent/
            ├── MainActivity.kt
            ├── DeviceAgentService.kt
            ├── SocketClient.kt
            ├── Downloader.kt
            ├── BackendApi.kt
            ├── SandboxManager.kt
            ├── Config.kt
            ├── Logger.kt
            └── model/
                ├── DownloadInstruction.kt
                ├── DownloadResult.kt
                └── DeviceStatus.kt
```

### 2.1 类职责矩阵

| 类 | 单一职责 | 依赖 | 并发模型 |
|----|----------|------|----------|
| `MainActivity` | UI 入口;首启检查 `MANAGE_EXTERNAL_STORAGE`、`POST_NOTIFICATIONS`;启动/停止 Service;显示 Service 状态 | `DeviceAgentService` | UI 线程 |
| `DeviceAgentService` | 编排:`onCreate` → 清沙箱 + 上报 ready;`onStartCommand` → Socket 监听循环;`onDestroy` → 关闭连接 | `SocketClient`、`SandboxManager`、`BackendApi`、`Downloader` | 单后台协程 Scope |
| `SocketClient` | TCP 连接、自动重连、按行读 JSON、回调 `onMessage` | 原生 `java.net.Socket` | 1 接收线程 |
| `Downloader` | 单文件 GET → 临时文件 → MD5 校验 → 重命名;批量下载顺序执行,失败短路 | OkHttp | 同 Service 协程 |
| `BackendApi` | `POST /devices/{id}/ready` + `POST /devices/{id}/download-ack` | OkHttp | 同上 |
| `SandboxManager` | `clear()`、`pathFor(fileType, ext)` → 返回 `/sdcard/3is/<fileType>.<ext>` | `java.io.File` | 任意线程(简单同步) |
| `Config` | 从 BuildConfig + SharedPreferences 读取 4 项配置 | Android Preferences | 任意线程 |
| `Logger` | 包 `android.util.Log`,统一 tag `3IS-Device` | — | 任意线程 |

### 2.2 关键接口

```kotlin
interface SocketClient.Listener {
    fun onDownloadInstruction(payload: DownloadInstruction)
    fun onConnected()
    fun onDisconnected(reason: String)
}

class Downloader {
    suspend fun download(urls: List<UrlInfo>): List<DownloadResult>
}

class BackendApi {
    suspend fun reportReady(): Boolean
    suspend fun reportDownloadAck(txnId: String, files: List<DownloadResult>): Boolean
}

class SandboxManager {
    fun clear()
    fun pathFor(fileType: String, ext: String): File
}
```

### 2.3 设计取舍(显式 YAGNI)

- 不引入 Hilt/Dagger:依赖少,Service 内手动 `new`
- 不引入 Retrofit:只 2 个 HTTP 调用,OkHttp 直接挂起
- 不写单元测试:首版手动 ADB 验证;后期需要再加 `androidTest/`

## 3. 消息协议 / 数据模型

### 3.1 Worker → Device(Socket,JSON over TCP)

每条消息一行 JSON,以换行符分隔。Device 按行读取后用 `JSONObject` 解析。

#### 3.1.1 下载指令

```json
{
  "cmd": "DOWNLOAD_FILES",
  "params": {
    "transaction_id": "TXN-20260612-abc12345",
    "download_urls": [
      {
        "file_type": "idcard",
        "url": "https://backend.example.com/api/v1/downloads/{att_id}?token=<jwt>",
        "md5": "9e107d9d372bb6826bd81d3542a419d6",
        "ext": "jpg"
      },
      {
        "file_type": "phone",
        "url": "https://backend.example.com/api/v1/downloads/{att_id}?token=<jwt>",
        "md5": "8a08c4d3f9ab12...",
        "ext": "pdf"
      }
    ]
  }
}
```

字段语义:

- `transaction_id`:仅用于 download-ack 回传(沙箱不再分目录,Device 不依赖它写文件)
- `file_type`:作为文件名前半段 → `/sdcard/3is/idcard.jpg`
- `ext`:文件扩展名;缺省时 fallback 为 `bin`
- `md5`:必填,校验失败视为下载失败

#### 3.1.2 心跳/控制消息

首版不实现。其他 `cmd` 静默忽略并 warn 日志。

### 3.2 Device → Backend(HTTPS)

#### 3.2.1 设备就绪

```http
POST /api/v1/devices/{device_id}/ready
Content-Type: application/json
Authorization: Bearer {DEVICE_TOKEN}

{ "status": "READY" }
```

- 调用时机:Service `onCreate` 完成沙箱清理后立即一次
- 失败处理:重试 3 次(指数退避 1/2/4s),仍失败仅日志

#### 3.2.2 下载完成

```http
POST /api/v1/devices/{device_id}/download-ack
Content-Type: application/json

{
  "transaction_id": "TXN-20260612-abc12345",
  "files": [
    { "file_type": "idcard", "local_path": "/sdcard/3is/idcard.jpg", "success": true },
    { "file_type": "phone",  "local_path": "/sdcard/3is/phone.pdf",  "success": true }
  ],
  "all_success": true,
  "completed_at": "2026-06-12T08:30:15.123Z"
}
```

- `all_success` 当且仅当所有附件下载且 MD5 通过
- 任一文件失败:停止后续下载,失败项 `success=false`,后续未尝试项 `errorReason="SKIPPED_PRIOR_FAIL"`
- `local_path` 始终为 `/sdcard/3is/<file_type>.<ext>`

### 3.3 Kotlin 数据类

```kotlin
data class UrlInfo(
    val fileType: String,
    val url: String,
    val md5: String,
    val ext: String = "bin"
)

data class DownloadInstruction(
    val transactionId: String,
    val urls: List<UrlInfo>
)

data class DownloadResult(
    val fileType: String,
    val localPath: String,
    val success: Boolean,
    val errorReason: String? = null
)
```

JSON 反序列化用 `org.json.JSONObject` 手写。

### 3.4 错误码

下载失败时 `errorReason` 取值:

- `MD5_MISMATCH` — 文件下载完成但 MD5 不匹配
- `NETWORK_ERROR` — HTTP 非 200 / 超时 / DNS 失败
- `IO_ERROR` — 写文件失败(磁盘满、权限丢失等)
- `URL_EXPIRED` — Backend 返回 403/410(签名 URL 过期);单独区分便于 Worker 重新签发
- `SKIPPED_PRIOR_FAIL` — 因前序失败导致未尝试的项

### 3.5 不变性 / 幂等性

- **重复下载指令**:Worker 重发同 `transaction_id` 指令,Device 仍执行完整 "清空+下载+ack" 流程,不去重(简化逻辑;Worker 不应重发,这是 Worker 的契约)
- **Service 重启**:`/sdcard/3is/` 内旧文件在 `onCreate` 被擦除,语义上等价于"重发指令"
- **进程被杀**:Foreground Service 大概率被系统重启(`START_STICKY`),但进行中的下载丢失;Worker 端通过 `download-ack` 超时检测此情况

### 3.6 与现有 Backend 的差异(必须改)

当前 backend `backend/api/router.py` 仅注册了 `transactions / workers / downloads / statistics / tasks`。本 spec 在范围内同步要求 Backend 端补两个端点,实施计划应作为单独任务列出:

- `POST /api/v1/devices/{device_id}/ready` — 更新 `devices` 表 `status=ONLINE, last_seen_at=now()`
- `POST /api/v1/devices/{device_id}/download-ack` — 触发事务状态机进入 `READY`(与 PRD §3.4 状态机对齐)

## 4. 生命周期 / 状态机

### 4.1 Service 状态机

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │   START_PENDING                                                 │
   │      │ MainActivity 检查权限通过, startForegroundService()       │
   │      ▼                                                          │
   │   INITIALIZING                                                  │
   │      │ onCreate: 清沙箱 → reportReady → connect Socket          │
   │      │ ✗ 权限丢失 → STOPPED + 通知栏提示 + 拉起 MainActivity     │
   │      ▼                                                          │
   │   IDLE  ◀─────────────────┐                                     │
   │      │ Socket 收到指令     │ 下载完成(成功/失败均 ack 后)        │
   │      ▼                     │                                    │
   │   DOWNLOADING ─────────────┘                                    │
   │      │ 进程被杀 / 系统重启                                       │
   │      ▼                                                          │
   │  (START_STICKY 自动重启 → 回到 INITIALIZING)                    │
   │                                                                 │
   │   任意状态: 用户在 MainActivity 点 Stop → STOPPED                │
   └─────────────────────────────────────────────────────────────────┘
```

四状态在前台通知栏的文案:

- `INITIALIZING` → "正在连接 Worker..."
- `IDLE` → "已连接 · 待命中"
- `DOWNLOADING` → "下载中: idcard.jpg (1/3)"
- `STOPPED` → 通知栏移除(`stopForeground`)

状态变量是 `DeviceAgentService` 内 `@Volatile var state: ServiceState`,所有切换同步更新 `NotificationManager`。

### 4.2 启动序列

```
1.  用户点 launcher 图标 → MainActivity.onCreate
2.  检查 MANAGE_EXTERNAL_STORAGE
       未授权 → 显示"前往设置授权"按钮 → Intent 跳系统设置 → return
3.  检查 POST_NOTIFICATIONS (API 33+)
       未授权 → registerForActivityResult 弹窗 → 用户拒绝则降级仅日志提示
4.  ContextCompat.startForegroundService(Intent(this, DeviceAgentService::class))
5.  Service.onCreate:
    5.1  startForeground(NOTIF_ID, buildNotification(INITIALIZING))
    5.2  CoroutineScope.launch { initialize() }
6.  initialize():
    6.1  sandboxManager.clear()                          // 擦 /sdcard/3is/*
    6.2  backendApi.reportReady()                        // 重试 3 次
    6.3  socketClient.connect(WORKER_HOST, 8765)         // 阻塞直到连接
    6.4  state = IDLE; updateNotification()
    6.5  socketClient.startReadLoop()                    // 自己的线程
7.  MainActivity.onResume → bindService → 监听 state 变化 → 更新文本
```

### 4.3 下载序列

```
SocketClient 收到一行 JSON ── onDownloadInstruction(payload) ──▶ Service
                                           │
Service.onDownloadInstruction:             ▼
   state = DOWNLOADING; updateNotification()
   sandboxManager.clear()                          // 擦旧文件
   results = downloader.download(payload.urls)     // 顺序下载
   ack = mapToAckPayload(results, payload.txnId)
   backendApi.reportDownloadAck(ack)               // 失败也要 ack
   state = IDLE; updateNotification()
```

下载循环短路策略:

```kotlin
suspend fun download(urls: List<UrlInfo>): List<DownloadResult> {
    val results = mutableListOf<DownloadResult>()
    for ((index, info) in urls.withIndex()) {
        notifyProgress(index + 1, urls.size, info.fileType)
        val r = downloadOne(info)
        results += r
        if (!r.success) {
            urls.drop(index + 1).forEach {
                results += DownloadResult(it.fileType, "", false, "SKIPPED_PRIOR_FAIL")
            }
            return results
        }
    }
    return results
}
```

理由:Worker 拿到 `all_success=false` 会要求人工重试整笔,继续下也是浪费。

### 4.4 异常恢复路径

| 故障 | 检测点 | 处理 |
|------|--------|------|
| Worker Socket 中断 | `read()` 返回 -1 / IOException | 1s/2s/4s/8s/16s/30s 指数退避重连;超过 5min 告警通知栏 |
| 下载 HTTP 超时 (30s) | OkHttp 抛 `SocketTimeoutException` | 单文件重试 1 次;仍失败 → `errorReason=NETWORK_ERROR` |
| MD5 不匹配 | `downloadOne()` 校验 | 不重试;`errorReason=MD5_MISMATCH` |
| URL 403/410 | OkHttp 返回码 | `errorReason=URL_EXPIRED` |
| 写文件 IOException | `FileOutputStream` | `errorReason=IO_ERROR`;短路后续 |
| `MANAGE_EXTERNAL_STORAGE` 运行时被吊销 | `sandboxManager.clear()` 抛 SecurityException | 状态切 STOPPED;通知栏点击拉起 MainActivity 重新引导 |
| Service 被系统杀 | — | `START_STICKY` 自动重启;进行中事务丢失,Worker 通过 ack 超时检测 |

### 4.5 停止序列

```
1.  MainActivity 点 Stop 按钮 → stopService(intent)
2.  Service.onDestroy:
    2.1  socketClient.close()
    2.2  下载协程 cancel(JobCancellationException)
    2.3  stopForeground(STOP_FOREGROUND_REMOVE)
    2.4  CoroutineScope.cancel()
3.  最后一次 backendApi 调用?  否 — Device 不主动上报 OFFLINE
                                Backend 通过心跳超时识别离线
                                (与 Worker 的 OFFLINE 判定语义一致)
```

### 4.6 边界情形

- **首启无网络**:`reportReady` 失败 3 次后仍进 IDLE 等 Socket 连接;Socket 也连不上则进入"重连退避"循环
- **下载到一半 Service 被杀重启**:重启后 `onCreate` 擦沙箱,等 Worker 重发指令(超时检测在 Worker 侧)
- **沙箱目录不存在**:`SandboxManager.clear()` 内 `mkdirs()` 兜底创建
- **下载完成但 ack 失败**:文件已写入沙箱,Worker 通过 ADB 看得到文件;ack 失败仅记日志

### 4.7 不做的事(YAGNI)

- 不做断点续传(单文件 <2MB,重下成本可接受)
- 不做并发下载(顺序简单可靠;PRD 未要求)
- 不做日志上传(首版日志仅 logcat;后期需要再加)
- 不做版本自更新(企业内分发,手动 `adb install -r` 升级)

## 5. 测试与发布

### 5.1 测试策略 — 首版仅手动 ADB 验证(YAGNI)

不引入 JUnit / Espresso / Robolectric。理由:

- APP 是 4 个核心类、约 500 行代码,Service+Socket 的集成测试比单测更有价值
- Mock Worker 用一个 30 行 Python TCP server 即可
- 后期回归压力大时再加 `androidTest/`(写到本节"未来工作")

#### 手动验证清单(写进 spec 作为验收标准)

| # | 场景 | 步骤 | 预期 |
|---|------|------|------|
| 1 | 首次安装 | `adb install app-debug.apk` → 点图标 | 弹"前往设置授权"页;授权后 Service 启动,通知栏显示 INITIALIZING |
| 2 | Worker 离线启动 | Worker 未启动 → 启动 APP | 通知栏显示"无法连接 Worker · 重试中";logcat 见指数退避 |
| 3 | Worker 上线连接 | 启动 Worker → APP 已运行 | ≤16s 内通知栏切到"已连接 · 待命中" |
| 4 | 正常下载 | Worker 推 `DOWNLOAD_FILES`(2 文件) | `/sdcard/3is/` 出现 idcard.jpg+phone.jpg;Backend 收到 `download-ack` 且 `all_success=true` |
| 5 | MD5 校验失败 | mock backend 返回错内容 | `download-ack` 中该项 `success=false errorReason=MD5_MISMATCH`;后续项 `SKIPPED_PRIOR_FAIL` |
| 6 | 沙箱清理(下载前) | 跑 1 次下载 → 再跑 1 次下载 | 第二次下载开始前 `/sdcard/3is/` 仅有第二次的文件 |
| 7 | 沙箱清理(服务重启) | 跑下载留下文件 → 强杀 APP → 重启 | `onCreate` 擦掉旧文件后再连接 |
| 8 | 进程被杀恢复 | `adb shell am force-stop com.threeis.deviceagent` | `START_STICKY` 几秒内自动拉起;通知栏恢复 |
| 9 | 跨 APP 可见 | 任意第三方文件管理器 APP | 能看到 `/sdcard/3is/` 中文件 |
| 10 | 权限被吊销 | 系统设置取消 `MANAGE_EXTERNAL_STORAGE` | Service 在下次清沙箱时检测到,切 STOPPED 通知栏提示 |

#### Mock Worker 脚本(放 `android/scripts/mock_worker.py`)

```python
import socket, json, sys
s = socket.socket(); s.bind(("0.0.0.0", 8765)); s.listen(1)
print("Mock Worker listening on :8765")
conn, addr = s.accept(); print(f"Device connected: {addr}")
msg = {
    "cmd": "DOWNLOAD_FILES",
    "params": {
        "transaction_id": "TXN-MOCK-0001",
        "download_urls": [
            {"file_type": "idcard", "url": sys.argv[1], "md5": sys.argv[2], "ext": "jpg"}
        ]
    }
}
conn.sendall((json.dumps(msg) + "\n").encode())
input("Press Enter to close...")
```

### 5.2 构建与发布

#### 本地构建(首版唯一交付方式)

```bash
cd android
./gradlew assembleDebug
# 产出:android/app/build/outputs/apk/debug/app-debug.apk
```

#### 首次环境准备(开发者一次性)

```bash
# 必备:JDK 17+、Android SDK Platform 34、Build-Tools 34.0.0
sdkmanager "platforms;android-34" "build-tools;34.0.0"
echo "sdk.dir=$ANDROID_HOME" > android/local.properties
```

#### 部署到设备

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.threeis.deviceagent/.MainActivity
```

#### 版本号

`versionCode=1 versionName="0.1.0"`,与 `worker/pyproject.toml` 一致;后续手动维护。

### 5.3 配置注入

无需打多个 APK。所有可变配置通过 `BuildConfig` + `SharedPreferences` 双层(读取优先级:**SharedPreferences > BuildConfig**;若 SharedPreferences 中无该键,则回落 BuildConfig 的默认值):

| 字段 | 默认值 | 来源 |
|------|--------|------|
| `WORKER_HOST` | `192.168.1.100` | `BuildConfig`(可被 SharedPreferences 覆盖) |
| `WORKER_PORT` | `8765` | 同上 |
| `BACKEND_URL` | `http://localhost:8000` | 同上 |
| `DEVICE_ID` | `device-001` | 仅 SharedPreferences;首启自动写入,可在 MainActivity 编辑 |

`MainActivity` 内置一组 4 个 `EditText` 作为配置编辑入口,点"保存"写入 SharedPreferences 并重启 Service。

### 5.4 文档更新点(实施时同步修订)

| 文件 | 修订 |
|------|------|
| `docs/user-manu.md` §5.1 | APK 来源改为"运行 `cd android && ./gradlew assembleDebug` 自助构建" |
| `docs/user-manu.md` §5.3 | `am start` 命令包名改为 `com.threeis.deviceagent/.MainActivity` |
| `docs/user-manu.md` §5.6 | 目录结构换为 Android 工程结构;Python 调试工具段删除(因为 device/ 被删) |
| `docs/user-manu.md` §6.3 | Device 环境变量表 → 改为 BuildConfig/SharedPreferences 字段表;补 `MANAGE_EXTERNAL_STORAGE` 授权步骤 |
| `docs/user-manu.md` §7.5 | Step 4 启动流程更新:权限授权后才能进 Service |
| `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` §3.1 / §3.4 | 沙箱路径 `/sdcard/sandbox/{txn_id}/` → `/sdcard/3is/`;Worker 端 ADB rm 步骤删除 |
| `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` §11.x | 加"受控专用设备"前提;`/sdcard/3is/` 全局可读为隔离原则的显式例外 |
| `device/` 整个目录 | **删除**(Python 调试代码不再保留) |

### 5.5 实施完成的退出条件(Definition of Done)

1. `cd android && ./gradlew assembleDebug` 在干净开发机上 ≤5 分钟内成功(从 git clone 起算)
2. §5.1 的 10 个手动验证场景全部通过(Android 7 / Android 13 设备各跑一遍)
3. Backend 端补完 `POST /devices/{id}/ready` 和 `POST /devices/{id}/download-ack`(调用真实端点,不是 mock)
4. `device/` 目录从 git 中删除
5. §5.4 的全部文档更新点落地
6. 一笔完整事务跑通:Frontend 提交申请 → Backend 派发 → Worker 推 Socket → Device 下载 → `/sdcard/3is/` 看到文件 → Backend 收到 ack
