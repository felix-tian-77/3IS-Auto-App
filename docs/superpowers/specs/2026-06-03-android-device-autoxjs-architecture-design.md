# Design: Android Device 端 AutoX.js 执行架构（Plan C）

| 字段 | 内容 |
|------|------|
| 设计主题 | 通过 Android Device + AutoX.js 执行 RPA 脚本的详细架构与实现方案 |
| 文档版本 | V1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | Draft（参考材料） |
| 文档定位 | **参考材料（Plan C）**：作为 Worker 端 Airtest（Plan A）和 Device 端 Airtest（Plan B）的第三选项 |
| 技术选型 | **AutoX.js v6+**（项目打包模式）+ Java/Kotlin 主壳 + 嵌入式 JS 引擎 |
| 关联 PRD | `docs/superpowers/specs/2026-06-02-prd-design.md` V1.1 |
| 关联设计 | `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md`（Plan A）<br>`docs/superpowers/specs/2026-06-03-android-device-airtest-architecture-design.md`（Plan B）<br>`docs/superpowers/specs/2026-06-03-airtest-vs-autoxjs-comparison.md`（对比） |
| 作者 | brainstorming skill |

**修订记录**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-03 | 初稿（参考材料） | office-hours |

---

## 1. 设计定位

### 1.1 架构选型矩阵

| 维度 | Plan A（Worker 端 Airtest） | Plan B（Device 端 Airtest） | **Plan C（Device 端 AutoX.js，本设计）** |
|------|--------------------------|--------------------------|--------------------------------------|
| Airtest 引擎位置 | Worker 桌面 | Android Device | **不适用**（AutoX.js） |
| 脚本语言 | Python | Python | **JavaScript** |
| 设备端包大小 | ~5MB | ~70MB | **~20MB** |
| 单事务 ATT | 5-8 min | 3-5 min | **3-5 min** |
| 团队上手成本 | 中 | 中 | **低** |
| License 风险 | 0 | 0 | **需法务确认**（Auto.js 商业使用历史） |
| 当前状态 | **主架构（已 commit）** | 参考材料 | **参考材料（本设计）** |

### 1.2 何时启用 Plan C

- **场景 A**：Plan A/B 在生产中遇到不可解决问题（如 UI 反射困难、Python 集成复杂）
- **场景 B**：团队以 JS 为主，转向 Python 学习成本过高
- **场景 C**：需要快速 POC 验证（AutoX.js 部署快，2-3 天即可出原型）
- **场景 D**：License 法务确认后，作为 Plan B 的替代品

### 1.3 何时不应启用

- 法务确认 AutoX.js License 不可商用
- 目标 APP 严重屏蔽 AccessibilityService（AutoX.js 主要依赖）
- 需要极高图像识别精度（AutoX.js 图像识别弱于 Airtest opencv）

---

## 2. 核心架构

### 2.1 三层架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                          云端 (Backend)                               │
│  - 事务接入/路由 (FR-SVR-001~003)                                      │
│  - 调度中心 (Redis Stream Consumer Group)                              │
│  - 状态机管理 (FR-SVR-008)                                            │
│  - OSS 签名 URL 生成与续签                                             │
│  - Flow 脚本包存储 (FR-SVR-016) — 现存储 .js 脚本                     │
└─────────────────┬────────────────────────────────────────────────────┘
                  │ HTTPS REST + WSS (outbound from Worker)
                  │
┌─────────────────▼────────────────────────────────────────────────────┐
│                   Worker 桌面端 (Python 3.14 + UV)                     │
│  【本架构中 Worker 仅做编排，不含 AutoX.js runtime】                     │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  编排器 (FR-CLI-005 纯编排)                                    │    │
│  │  - 接收 TASK_DISPATCH                                         │    │
│  │  - 调 /oss-urls 拿签名 URL                                     │    │
│  │  - Socket 通知 Device 下载影像                                 │    │
│  │  - 等待 Device 下载完成                                       │    │
│  │  - Socket 通知 Device 执行 Step (JSON)                         │    │
│  │  - 收集 step-result，处理 Retry Policy / 超时熔断              │    │
│  │  - 上报结果到 Backend                                          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  LAN Socket 通信 (8765, 白名单 IP)                                    │
│  ┌──────┐  ┌──────┐  ┌──────┐                                        │
│  │Dev-A │  │Dev-B │  │Dev-N │                                        │
│  └──────┘  └──────┘  └──────┘                                        │
└──────────────────────────────────────────────────────────────────────┘
                  ▲
                  │ TCP Socket 8765 (LAN)
                  │
┌─────────────────┴────────────────────────────────────────────────────┐
│           Android Device + Device Agent (AutoX.js embedded)          │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Device Agent APK (~20MB)                                      │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │    │
│  │  │ MainActivity    │  │ SocketServer    │  │ OssDownloader│  │    │
│  │  │ (Kotlin)        │  │ (Kotlin :8765)  │  │ (OkHttp)     │  │    │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘  │    │
│  │  ┌─────────────────────────────────────────────────────────┐ │    │
│  │  │ AutoX.js Runtime (embedded JS engine)                    │ │    │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │ │    │
│  │  │  │ Rhino JS      │  │ Accessibility │  │ OCR Module   │ │ │    │
│  │  │  │ Engine        │  │ Service       │  │ (内置)        │ │ │    │
│  │  │  └───────────────┘  └───────────────┘  └──────────────┘ │ │    │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │ │    │
│  │  │  │ UI Module     │  │ Image Module  │  │ Http Module  │ │ │    │
│  │  │  │ (控件反射)     │  │ (图像识别)     │  │ (HTTP 客户端) │ │ │    │
│  │  │  └───────────────┘  └───────────────┘  └──────────────┘ │ │    │
│  │  │  ┌──────────────────────────────────────────────────┐   │ │    │
│  │  │  │ ScriptEngine (脚本执行引擎)                        │   │ │    │
│  │  │  │ - 加载 Flow 脚本 (.js)                              │   │ │    │
│  │  │  │ - 监听 Socket 命令 (EXECUTE_STEP)                  │   │ │    │
│  │  │  │ - 调用 AutoX.js API 执行                            │   │ │    │
│  │  │  │ - 截图 + 上报                                      │   │ │    │
│  │  │  └──────────────────────────────────────────────────┘   │ │    │
│  │  └─────────────────────────────────────────────────────────┘ │    │
│  │  ┌─────────────────────────────────────────────────────────┐ │    │
│  │  │ 沙箱存储                                                  │ │    │
│  │  │  - 输入影像: /sdcard/sandbox/{txn_id}/                   │ │    │
│  │  │  - 脚本: /sdcard/autoxjs/scripts/{flow_id}/{version}/    │ │    │
│  │  │  - 截图: /sdcard/Pictures/autoxjs/                       │ │    │
│  │  └─────────────────────────────────────────────────────────┘ │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  AccessibilityService (UI 自动化核心)                                   │
│  目标保险 APP (被 AutoX.js 通过 a11y 控制)                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 三端职责对照

| 维度 | Backend（云端） | Worker（桌面端） | **Device Agent（含 AutoX.js）** |
|------|----------------|----------------|-----------------------------|
| 角色 | 调度/编排中心 | **纯编排器** | **AutoX.js 实际执行点** |
| 语言 | Python（隐含） | Python ≥ 3.14 | **Kotlin/Java（主壳）+ JavaScript（脚本）** |
| 核心框架 | FastAPI/Django | Socket/HTTP 客户端 | **AutoX.js 嵌入式 + Rhino 引擎** |
| 持有 Flow 脚本 | ✅（OSS） | ⚠️（仅元数据） | ✅（OSS 下载 + 本地缓存 + 实际执行） |
| 持有输入影像 | ❌ | ❌ | ✅（直连 OSS 下载） |
| UI 自动化 | ❌ | ❌ | ✅（AutoX.js + AccessibilityService） |
| 状态机管理 | ✅（强一致） | ⚠️（Step 状态聚合） | ❌ |
| 网络方向 | 入站 443 | 出站 443 | **入站 Socket 8765 + 出站 443（OSS）** |

### 2.3 关键不变量（与 V1.1 PRD / Plan A/B 一致）

- **OSS 直连下载**：Device 直连 OSS 签名 URL，Worker 不中转文件字节流
- **CONFIRM 流程移除**：CONFIRM Step 退化为普通 Step
- **业务类型用户指定**：用户提交时显式指定
- **Redis Stream MVP 必需**：调度层不调整
- **白名单 IP**：Device Socket 仅接受站点固定 IP 段

---

## 3. Android Device Agent 详细架构

### 3.1 技术选型：AutoX.js 项目打包

**AutoX.js v6+ 支持两种部署方式**：

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **直接安装 AutoX.js APP** | 从 GitHub/F-Droid 安装，设备端运行 | 单设备调试、个人使用 |
| **项目打包为独立 APK** | 用 `autox.js` CLI 工具 + build.gradle 打包自定义 APK | **生产部署（推荐）** |

**本设计采用项目打包方式**：
- 在我们的 Agent APK 中嵌入 AutoX.js 运行时
- 通过项目打包工具集成 JS 引擎 + AccessibilityService
- APK 签名 + 自有应用 ID（如 `com.iiil.auto.agent`）

### 3.2 Agent APK 内部架构

```
com.iiil.auto.agent/
├── ui/
│   ├── MainActivity (Kotlin)        # 启动页 + 状态展示
│   ├── DebugActivity                # 调试面板（开发期）
│   └── AccessibilityPromptActivity  # 引导开启无障碍服务
├── service/
│   ├── AgentForegroundService       # 主服务（保活）
│   ├── AirtestAccessibilityService  # 继承自 AutoX.js a11y 服务
│   │   ├── 启动 JS 引擎
│   │   ├── 加载 ScriptEngine
│   │   └── 提供 UI 反射能力
│   ├── SocketServerService          # 监听 8765
│   ├── OssDownloadService           # OSS 下载（OkHttp）
│   └── ScriptManagerService         # 脚本版本管理
├── js/                              # 嵌入式 JS 资源
│   ├── runtime/                     # AutoX.js 核心 JS
│   │   ├── api.js                   # 核心 API
│   │   ├── ui.js                    # UI 模块
│   │   ├── ocr.js                   # OCR 模块
│   │   └── ...
│   └── engine/                      # 自研 JS 代码
│       ├── step_executor.js         # Step → AutoX.js API 映射
│       ├── command_handler.js       # Socket 命令处理
│       └── script_loader.js         # 脚本动态加载
├── net/
│   ├── SocketServer (Kotlin)
│   ├── OssClient (Kotlin)
│   └── BackendApi (Kotlin)
├── storage/
│   ├── SandboxManager               # /sdcard/sandbox/ 管理
│   ├── ScriptCache                  # /sdcard/autoxjs/scripts/ 缓存
│   └── CleanupScheduler             # 自动清理
└── util/
    ├── WhitelistIP                  # IP 白名单
    ├── MD5Verifier                  # 文件 MD5
    └── Logger                       # 结构化日志
```

### 3.3 build.gradle 关键配置

```gradle
plugins {
    id 'com.android.application' version '8.1.0'
    id 'com.chaquo.python' version '15.0.0'  // 不需要
    id 'autoxjs' version '6.0.0'              // AutoX.js 打包插件
}

android {
    namespace 'com.iiil.auto.agent'
    compileSdk 34
    
    defaultConfig {
        applicationId "com.iiil.auto.agent"
        minSdk 26
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }
}

dependencies {
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
    implementation 'com.google.code.gson:gson:2.10.1'
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
}

autoxjs {
    // 嵌入的 JS 资源
    resources {
        srcDir 'src/main/js'
    }
    // 项目打包配置
    build {
        outputApkPath 'build/outputs/apk/release/agent-autoxjs-release.apk'
        obfuscate true  // JS 代码混淆
    }
}
```

**APK 包大小估算**：

| 组件 | 大小 |
|------|------|
| AutoX.js 运行时 + Rhino 引擎 | ~12MB |
| UI/OCR/Image 模块 | ~5MB |
| 自研 JS 代码 | ~1MB |
| Kotlin/Java 主壳 | ~2MB |
| OkHttp + 其他依赖 | ~2MB |
| **总计** | **~22MB** |

对比 Airtest Plan B：~70MB（缩小 3x）

### 3.4 关键技术点：AutoX.js 嵌入式集成

```kotlin
// AccessibilityService 启动时初始化 JS 引擎
class AirtestAccessibilityService : AccessibilityService() {
    
    private val scriptEngine = ScriptEngine()
    private val socketServer = SocketServer(port = 8765)
    
    override fun onServiceConnected() {
        super.onServiceConnected()
        
        // 1. 启动 JS 运行时
        scriptEngine.start()
        
        // 2. 暴露 a11y 能力给 JS
        scriptEngine.expose("accessibilityService", this)
        
        // 3. 启动 Socket 服务
        socketServer.start { command -> 
            scriptEngine.executeCommand(command) 
        }
    }
    
    override fun onDestroy() {
        scriptEngine.stop()
        socketServer.stop()
        super.onDestroy()
    }
}
```

```javascript
// step_executor.js (自研 JS)
"ui";  // AutoX.js 启用 UI 模式
runtime.events.on("socket_command", function(cmd) {
    var result = handleCommand(cmd);
    runtime.events.emit("socket_response", result);
});

function handleCommand(cmd) {
    if (cmd.cmd === "EXECUTE_STEP") {
        return executeStep(cmd.params);
    } else if (cmd.cmd === "DOWNLOAD_FILES") {
        // 触发 Kotlin 侧下载
        return runtime.bridge.call("ossDownload", cmd.params);
    }
    // ...
}

function executeStep(params) {
    var start = Date.now();
    try {
        var result = dispatchAction(params);
        return {
            event: "STEP_RESULT",
            step_id: params.step_id,
            status: "SUCCESS",
            duration_ms: Date.now() - start,
            result: result
        };
    } catch (e) {
        return {
            event: "STEP_RESULT",
            step_id: params.step_id,
            status: "FAIL",
            error_message: e.message
        };
    }
}

function dispatchAction(params) {
    switch (params.action_type) {
        case "OPEN_APP":
            return launchApp(params.action_params.package_name);
        case "INPUT":
            return setText(params.action_params.text);  // 或 inputText()
        case "CLICK":
            if (params.action_params.selector) {
                return clickBySelector(params.action_params.selector);
            } else {
                return click(params.action_params.x, params.action_params.y);
            }
        case "UPLOAD":
            return handleUpload(params.action_params);
        case "SCREENSHOT":
            return captureScreen(params.action_params.filename);
        case "WAIT":
            return waitForSelector(params.action_params);
    }
}

function handleUpload(params) {
    // AutoX.js 方式：点击上传按钮 + 等待文件选择器
    var fileName = params.file_name;
    var txId = params.transaction_id;
    var sandboxPath = "/sdcard/sandbox/" + txId + "/" + fileName;
    
    // 方案 1: 通过系统 Intent 直接传递（推荐）
    if (params.use_intent) {
        runtime.bridge.call("uploadViaIntent", {
            filePath: sandboxPath,
            targetPackage: params.target_package
        });
        return { uploaded: fileName, method: "intent" };
    }
    
    // 方案 2: 通过文件选择器 UI 自动化
    click(params.action_params.upload_button_x, params.action_params.upload_button_y);
    sleep(2000);  // 等待文件选择器
    // 导航到沙箱目录
    // ...
    return { uploaded: fileName, method: "ui_automation" };
}
```

### 3.5 关键技术挑战与解决方案

#### 挑战 1：AccessibilityService 被目标 APP 屏蔽

**问题**：部分目标 APP 检测 accessibility 接入并隐藏 UI 树信息或拒绝服务。

**解决方案**：

| 方案 | 实现 | 优缺点 |
|------|------|--------|
| **A. 控件 + 图像混合** | 控件反射失败时降级到图像识别 | ✅ 鲁棒；⚠️ 实现复杂 |
| **B. 黑名单/白名单模式** | 维护一个"已知屏蔽"清单，特定 APP 走图像 | ✅ 可控；⚠️ 维护成本 |
| **C. 协调目标 APP 厂商** | 请求目标 APP 白名单我们的服务 | ✅ 最佳；⚠️ 需业务方协调 |
| **D. 多 AccessibilityService 切换** | 备用 a11y 服务 | 🟡 增加复杂度 |

**推荐**：**A + C** 组合

#### 挑战 2：图像识别精度

**问题**：AutoX.js 图像识别基于系统截图 + 模板匹配，精度低于 Airtest opencv。

**解决方案**：

```javascript
// 图像识别增强：多尺度 + ROI 限定
function robustImageClick(templatePath, options) {
    options = options || {};
    var timeout = options.timeout || 10;
    var startTime = Date.now();
    
    while (Date.now() - startTime < timeout * 1000) {
        // 1. 限定 ROI（减少匹配范围）
        var region = options.region;
        
        // 2. 多尺度匹配
        for (var scale of [1.0, 0.9, 1.1]) {
            var point = image.findImage(templatePath, {
                region: region,
                scale: scale,
                threshold: 0.85
            });
            if (point) {
                click(point.x, point.y);
                return true;
            }
        }
        sleep(500);
    }
    return false;
}
```

#### 挑战 3：UPLOAD 步骤

**问题**：不同保险 APP 的文件选择器 UI 差异大。

**解决方案**：

```javascript
// 推荐：Intent 直接传递
function uploadViaIntent(filePath, targetPackage) {
    // 通过 Kotlin 桥接调用 Intent
    return runtime.bridge.call("uploadViaIntent", {
        filePath: filePath,
        targetPackage: targetPackage
    });
}

// Kotlin 实现（MainActivity 中）
fun uploadViaIntent(filePath: String, targetPackage: String): Boolean {
    val file = File(filePath)
    if (!file.exists()) return false
    
    val uri = FileProvider.getUriForFile(
        this, "com.iiil.auto.agent.fileprovider", file
    )
    
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/*"
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_SUBJECT, "upload")
        setPackage(targetPackage)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    
    return try {
        startActivity(intent)
        true
    } catch (e: Exception) {
        false
    }
}
```

### 3.6 沙箱与文件管理

| 位置 | 路径 | 权限 | 清理时机 |
|------|------|------|----------|
| **输入影像** | `/sdcard/sandbox/{txn_id}/` | 700 + FileProvider | SUCCESS: 立即; FAIL: 24h; DLQ: 7d |
| **Flow 脚本** | `/sdcard/autoxjs/scripts/{flow_id}/{version}/` | 700 | 永久保留（版本淘汰时清理） |
| **AutoX.js 截图** | `/sdcard/Pictures/autoxjs/{txn_id}/` | 700 | 事务完成 |

### 3.7 权限清单

```xml
<!-- AndroidManifest.xml 关键权限 -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" 
                 android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" 
                 android:maxSdkVersion="29" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" 
                 tools:ignore="QueryAllPackagesPermission" />

<!-- AccessibilityService 声明（AutoX.js 风格） -->
<service
    android:name=".service.AirtestAccessibilityService"
    android:label="3IS Auto Agent"
    android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
    <intent-filter>
        <action android:name="android.accessibilityservice.AccessibilityService" />
    </intent-filter>
    <meta-data
        android:name="android.accessibilityservice"
        android:resource="@xml/accessibility_service_config" />
</service>
```

---

## 4. Worker 侧（纯编排器）

### 4.1 模块清单

| 模块 | 职责 | 关键依赖 |
|------|------|----------|
| **Step Orchestrator** | 按 Step 顺序下发指令给 Device | 自研 |
| **Socket Client** | 与 Device Agent 通信 | `socket` / `aiohttp` |
| **Result Aggregator** | 收集 Step 结果，决策 Retry | 自研 |
| **Retry Policy** | Step 级重试（3 次，指数退避） | 自研 |
| **Timeout Watchdog** | Step 超时熔断（默认 60s） | `asyncio` |
| **Backend Reporter** | 上报事务结果 | `requests` |
| **WebSocket Listener** | 接收 Backend 任务推送 | `websockets` |

### 4.2 Worker 端不安装什么

| 不安装 | 原因 |
|--------|------|
| ❌ airtest | 不在 Worker 端执行 |
| ❌ pocoui | 同上 |
| ❌ opencv | 同上 |
| ❌ Chaquopy | 同上 |
| ❌ AutoX.js | 不在 Worker 端执行 |
| ❌ Node.js / Rhino JS 引擎 | 同上 |

**Worker 包大小**：~50MB（仅 Python 解释器 + 标准库 + requests/websockets）

### 4.3 执行流程

```
[阶段 1-3：启动/心跳/脚本同步 与 Plan A/B 相同]

阶段 4：任务接收与执行（本架构特有）

4.1  WebSocket /ws/v1/dispatch 收到 TASK_DISPATCH
4.2  POST /api/v1/tasks/{id}/ack
4.3  POST /api/v1/transactions/{id}/oss-urls → 拿到 signed_urls[]
4.4  ── Socket:8765 ──► Device: DOWNLOAD_FILES {oss_urls}
4.5  Device 直连 OSS 下载到 /sdcard/sandbox/{txn_id}/
4.6  Device 完成 → 上报 download-complete (Socket)
4.7  Worker 收到下载完成 → 事务进入 RUNNING
4.8  ── Socket ──► Device: EXECUTE_STEP {step_id, action_type, params}
4.9  Device AutoX.js 执行 Step
4.10 Device 上报 step-result (Socket)
4.11 Worker 聚合结果:
       - SUCCESS → 下发下一 Step
       - FAIL → Retry Policy (3 次)
       - TIMEOUT → Worker 端熔断
4.12 全部 Step 完成 → POST /tasks/{id}/result
4.13 Socket 通知 Device 清理沙箱
```

---

## 5. 通信协议详细设计

### 5.1 Worker ↔ Device Socket 协议

**传输层**：TCP Socket（LAN），JSON 消息

**Worker → Device 指令**：

```json
{
  "cmd": "DOWNLOAD_FILES",
  "request_id": "req-uuid-001",
  "params": {
    "transaction_id": "TXN-20260603-00001",
    "oss_urls": [
      {
        "file_type": "ID_CARD",
        "url": "https://oss.example.com/...?signature=...",
        "md5": "a1b2c3d4e5f6...",
        "expires_at": "2026-06-03T10:05:00Z"
      }
    ]
  }
}

{
  "cmd": "EXECUTE_STEP",
  "request_id": "req-uuid-002",
  "params": {
    "transaction_id": "TXN-20260603-00001",
    "flow_id": "FLOW-NEW-001",
    "flow_version": "1.0.0",
    "step_id": "step-003",
    "action_type": "CLICK",
    "action_params": {
      "selector": {
        "type": "text",
        "value": "新保单"
      },
      "timeout": 10
    },
    "timeout_ms": 60000
  }
}

{
  "cmd": "CLEANUP",
  "request_id": "req-uuid-003",
  "params": {
    "transaction_id": "TXN-20260603-00001"
  }
}
```

**Device → Worker 事件**：

```json
{
  "event": "DOWNLOAD_COMPLETE",
  "request_id": "req-uuid-001",
  "transaction_id": "TXN-20260603-00001",
  "files": [
    {
      "md5": "a1b2c3d4e5f6...",
      "local_path": "/sdcard/sandbox/TXN-.../idcard.jpg",
      "size_bytes": 1024000
    }
  ]
}

{
  "event": "STEP_RESULT",
  "request_id": "req-uuid-002",
  "transaction_id": "TXN-20260603-00001",
  "step_id": "step-003",
  "status": "SUCCESS",
  "duration_ms": 1234,
  "screenshot_path": "/sdcard/Pictures/autoxjs/TXN-.../step-003.png",
  "screenshot_uploaded_to": "https://oss.example.com/...?signature=...",
  "error_message": null
}

{
  "event": "OSS_URL_EXPIRED",
  "transaction_id": "TXN-20260603-00001",
  "signed_url_id": "uuid-xxx"
}
```

### 5.2 控件选择器（AutoX.js 风格）

**Step CLICK 操作的 selector 设计**（AutoX.js 风格）：

```json
// 文本选择器
{ "type": "text", "value": "新保单" }

// ID 选择器（resource-id）
{ "type": "id", "value": "com.example.insurance:id/submit_btn" }

// 描述选择器（content-desc）
{ "type": "desc", "value": "提交" }

// 类名 + 索引
{ "type": "class", "value": "android.widget.Button", "index": 2 }

// 文本模糊匹配
{ "type": "textContains", "value": "保单" }

// 坐标
{ "type": "coords", "x": 540, "y": 1200 }

// 图像模板
{ "type": "image", "value": "tpl/insurance_tab.png" }
```

**AutoX.js 内部映射**：

```javascript
function clickBySelector(selector) {
    var node = null;
    switch (selector.type) {
        case "text":
            node = text(selector.value);
            break;
        case "id":
            node = id(selector.value);
            break;
        case "desc":
            node = desc(selector.value);
            break;
        case "class":
            node = className(selector.value).findOnce();
            if (selector.index) {
                // 按索引取
            }
            break;
        case "textContains":
            node = textContains(selector.value).findOnce();
            break;
        case "coords":
            click(selector.x, selector.y);
            return true;
        case "image":
            return robustImageClick(selector.value, selector);
    }
    
    if (node) {
        var bounds = node.bounds();
        click(bounds.centerX(), bounds.centerY());
        return true;
    }
    return false;
}
```

---

## 6. 脚本动态下发机制

### 6.1 流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 管理员在 Backend 上传 Flow 脚本（.js）                    │
│     POST /api/v1/flows/{id}/versions (FR-SVR-016)           │
│     → 存储到 OSS: /flows/{flow_id}/{version}/script.js      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Device Agent 启动时检查脚本版本                            │
│     GET /api/v1/workers/scripts/versions (Worker 代理)       │
│     → 列出本地已缓存的 flow_id + version                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 比对并下载新版本                                          │
│     GET /api/v1/flows/{id}/versions/{version}/download      │
│     → 直接从 OSS 下载 .js 脚本 + 模板图片                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 本地缓存                                                  │
│     存储到 /sdcard/autoxjs/scripts/{flow_id}/{version}/      │
│     旧版本备份为 .bak                                         │
│     校验: Node.js 风格的 syntax check                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  5. Lazy Loading                                              │
│     Agent 启动时不预加载所有脚本                               │
│     收到 EXECUTE_STEP 指令时按需加载对应 flow_id 的脚本        │
│     使用 require() 或 eval() 动态加载                         │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 脚本示例（Flow 脚本）

```javascript
// /sdcard/autoxjs/scripts/FLOW-NEW-001/1.0.0/script.js
// 由 ScriptEngine 动态加载

"auto";

/**
 * 单步执行入口（ScriptEngine 调用）
 * @param {Object} step Step 定义
 * @returns {Object} 执行结果
 */
function executeStep(step) {
    switch (step.action_type) {
        case "OPEN_APP":
            return stepOpenApp(step);
        case "INPUT":
            return stepInput(step);
        case "CLICK":
            return stepClick(step);
        case "UPLOAD":
            return stepUpload(step);
        case "SCREENSHOT":
            return stepScreenshot(step);
        case "WAIT":
            return stepWait(step);
    }
}

function stepOpenApp(step) {
    launchApp(step.params.package_name);
    return { launched: step.params.package_name };
}

function stepClick(step) {
    var selector = step.params.selector;
    var timeout = step.params.timeout || 10;
    
    if (selector.type === "coords") {
        click(selector.x, selector.y);
        return { clicked: "coords" };
    } else if (selector.type === "image") {
        var success = robustImageClick(selector.value, timeout);
        return { clicked: "image", success: success };
    } else {
        var node = findBySelector(selector);
        if (node) {
            var bounds = node.bounds();
            click(bounds.centerX(), bounds.centerY());
            return { clicked: "selector", text: node.text() };
        }
        throw new Error("Element not found: " + JSON.stringify(selector));
    }
}

function stepInput(step) {
    // AutoX.js 的 setText 直接设置文本
    setText(step.params.text);
    return { input: step.params.text };
}

function stepUpload(step) {
    var fileName = step.params.file_name;
    var txId = step.params.transaction_id;
    var sandboxPath = "/sdcard/sandbox/" + txId + "/" + fileName;
    
    // 优先用 Intent 方式
    if (step.params.use_intent) {
        runtime.bridge.call("uploadViaIntent", {
            filePath: sandboxPath,
            targetPackage: step.params.target_package
        });
        return { uploaded: fileName, method: "intent" };
    }
    
    // 回退到 UI 自动化
    click(step.params.upload_button.x, step.params.upload_button.y);
    sleep(2000);
    // 导航文件选择器
    // ...
    return { uploaded: fileName, method: "ui_automation" };
}

// 辅助函数
function findBySelector(selector) {
    switch (selector.type) {
        case "text": return text(selector.value).findOnce();
        case "id": return id(selector.value).findOnce();
        case "desc": return desc(selector.value).findOnce();
        case "class": return className(selector.value).findOnce();
        case "textContains": return textContains(selector.value).findOnce();
        default: return null;
    }
}

function robustImageClick(templatePath, timeout) {
    var start = Date.now();
    while (Date.now() - start < timeout * 1000) {
        var point = image.findImage(templatePath, { threshold: 0.85 });
        if (point) {
            click(point.x, point.y);
            return true;
        }
        sleep(500);
    }
    return false;
}

// 导出（AutoX.js 风格）
module.exports = { executeStep: executeStep };
```

### 6.3 缓存策略

| 策略 | 说明 |
|------|------|
| **预下载** | Agent 启动时拉取已发布 Flow 的最新版本 |
| **Lazy Load** | 收到 Step 指令时按需 `module.exports` |
| **版本保留** | 最近 3 个版本保留本地缓存 |
| **MD5 校验** | 下载完成后 MD5 校验 |
| **空间管理** | LRU 淘汰，超 200MB 时清理旧版本 |

---

## 7. 关键实现代码示例

### 7.1 Socket 服务端（Kotlin）

```kotlin
// SocketServerService.kt
class SocketServerService : Service() {
    private val port = 8765
    private val whitelist = setOf("192.168.1.0/24", "10.0.0.0/8")
    private val scriptEngine = ScriptEngine.getInstance()
    
    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIFICATION_ID, createNotification())
        startSocketServer()
    }
    
    private fun startSocketServer() {
        Thread {
            val serverSocket = ServerSocket(port)
            while (!Thread.interrupted()) {
                val client = serverSocket.accept()
                val ip = (client.remoteSocketAddress as InetSocketAddress).address.hostAddress
                
                if (!isWhitelisted(ip)) {
                    Log.w(TAG, "Rejected IP: $ip")
                    client.close()
                    continue
                }
                
                handleClient(client)
            }
        }.start()
    }
    
    private fun handleClient(socket: Socket) {
        val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
        val writer = PrintWriter(socket.getOutputStream(), true)
        
        while (socket.isConnected) {
            val line = reader.readLine() ?: break
            val command = Gson().fromJson(line, JsonObject::class.java)
            
            // 转发到 JS 引擎
            val response = scriptEngine.executeCommand(command.toString())
            writer.println(response)
        }
    }
    
    private fun isWhitelisted(ip: String): Boolean {
        return whitelist.any { IpMatcher(it).match(ip) }
    }
}
```

### 7.2 ScriptEngine（Kotlin + JS 桥接）

```kotlin
// ScriptEngine.kt
class ScriptEngine private constructor() {
    private val rhino: Context
    private var scope: Scriptable
    
    init {
        rhino = Context.enter()
        rhino.optimizationLevel = -1  // 兼容模式
        scope = rhino.initStandardObjects()
        
        // 暴露 Java 类给 JS
        val bridge = Context.toObject(JavaBridge(this@ScriptEngine), scope)
        ScriptableObject.putProperty(scope, "runtime", bridge)
    }
    
    fun executeCommand(commandJson: String): String {
        return try {
            val js = """
                var cmd = $commandJson;
                var result = handleCommand(cmd);
                JSON.stringify(result);
            """.trimIndent()
            
            rhino.evaluateString(scope, js, "executeCommand", 1, null)
        } catch (e: Exception) {
            """{"event":"ERROR","error":"${e.message}"}"""
        }
    }
    
    fun executeStep(params: JsonObject): JsonObject {
        // 加载脚本（首次或缓存）
        val flowId = params.get("flow_id").asString
        val version = params.get("flow_version").asString
        loadScript(flowId, version)
        
        // 调用 JS
        val stepJson = Gson().toJson(params)
        val result = rhino.evaluateString(
            scope,
            "executeStep($stepJson);",
            "executeStep", 1, null
        )
        
        return Gson().fromJson(result.toString(), JsonObject::class.java)
    }
    
    private fun loadScript(flowId: String, version: String) {
        val scriptPath = "/sdcard/autoxjs/scripts/$flowId/$version/script.js"
        if (scope.has("executeStep", scope)) {
            return  // 已加载
        }
        
        val code = File(scriptPath).readText()
        rhino.evaluateString(scope, code, "loadScript", 1, null)
    }
    
    companion object {
        @Volatile private var instance: ScriptEngine? = null
        
        fun getInstance(): ScriptEngine {
            return instance ?: synchronized(this) {
                instance ?: ScriptEngine().also { instance = it }
            }
        }
    }
}
```

### 7.3 JavaBridge（Kotlin 提供给 JS 调用）

```kotlin
// JavaBridge.kt
class JavaBridge(private val engine: ScriptEngine) {
    
    @JavascriptInterface
    fun uploadViaIntent(filePath: String, targetPackage: String): Boolean {
        return try {
            val file = File(filePath)
            if (!file.exists()) return false
            
            val uri = FileProvider.getUriForFile(
                MainActivity.context, 
                "com.iiil.auto.agent.fileprovider", 
                file
            )
            
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "image/*"
                putExtra(Intent.EXTRA_STREAM, uri)
                setPackage(targetPackage)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            
            MainActivity.context.startActivity(intent)
            true
        } catch (e: Exception) {
            Log.e(TAG, "uploadViaIntent failed", e)
            false
        }
    }
    
    @JavascriptInterface
    fun captureScreen(filename: String): String {
        val path = "/sdcard/Pictures/autoxjs/$filename"
        val file = File(path)
        file.parentFile?.mkdirs()
        
        // 通过 AccessibilityService 截图
        val bitmap = AccessibilityService.takeScreenshot()
        FileOutputStream(file).use { 
            bitmap.compress(Bitmap.CompressFormat.JPEG, 70, it) 
        }
        return path
    }
}
```

---

## 8. 性能与限制

### 8.1 APK 包大小

| 组件 | 大小 |
|------|------|
| AutoX.js 运行时 + Rhino 引擎 | ~12MB |
| UI/OCR/Image 模块 | ~5MB |
| 自研 JS 代码 | ~1MB |
| Kotlin/Java 主壳 | ~2MB |
| OkHttp + 其他依赖 | ~2MB |
| **总计** | **~22MB** |

对比：
- Plan A Worker 端 Device Agent: ~5MB
- Plan B Airtest Device Agent: **~70MB**
- **Plan C AutoX.js Device Agent: ~22MB**（3x 小于 Plan B）

### 8.2 运行时性能

| 指标 | Plan B (Airtest) | **Plan C (AutoX.js)** | 差异 |
|------|------------------|---------------------|------|
| 冷启动时间 | 5-8s | **<1s** | ✅ 5-8x 更快 |
| 单 Step 控件操作 | 200-500ms (POCO) | **50-150ms (a11y)** | ✅ 2-3x 更快 |
| 单 Step 图像识别 | 50-300ms (opencv) | 200-500ms (内置) | 🟡 慢 1.5-2x |
| 单事务 ATT | 3-5 min | **3-5 min** | 🟡 相当 |
| OCR 文字识别 | 需第三方库 | **内置（速度中）** | ✅ 开箱即用 |
| 内存空闲占用 | ~80MB | **~30MB** | ✅ 2.5x 更小 |
| 内存峰值 | ~250MB | **~80MB** | ✅ 3x 更小 |

### 8.3 设备要求

| 指标 | Plan B (Airtest) | **Plan C (AutoX.js)** |
|------|------------------|---------------------|
| Android 版本 | ≥ 10 | **≥ 8.0** |
| RAM 最低 | 4GB | **3GB** |
| 存储可用 | 8GB | **5GB** |
| CPU | 中高端 | **中端即可** |
| 设备成本 | ¥1500-2500 | **¥800-1500** |

### 8.4 已知限制

| 限制 | 影响 | 缓解 |
|------|------|------|
| **AccessibilityService 被禁用** | UI 自动化失效 | 启动时强提示；运营引导开启 |
| **目标 APP 屏蔽 accessibility** | 控件反射失效 | 回退图像识别（精度低） |
| **AutoX.js 图像识别精度弱** | UI 变化时易失败 | ROI 限定 + 多尺度 + 阈值调优 |
| **Rhino 引擎性能** | 复杂脚本慢 | 简化脚本逻辑；避免大循环 |
| **JS 调试能力弱** | 故障定位难 | 详细日志 + 设备端 IDE |
| **License 风险** | 商业使用争议 | **法务确认**（启用前必须） |

---

## 9. 部署与硬件

### 9.1 Device 硬件要求

| 资源 | 最低 | 推荐 | 备注 |
|------|------|------|------|
| Android 版本 | **8.0** | **10+** | AutoX.js 兼容性 |
| RAM | **3GB** | **4GB+** | 内存峰值 80MB |
| 存储 | 5GB 可用 | 8GB+ | APK + 沙箱 + 脚本 |
| CPU | 中低端 | 中端 | 控件操作轻量 |
| USB 接口 | 数据 + 充电 | - | - |
| 网络 | WiFi (LAN) | - | Socket 通信 |

### 9.2 Worker 硬件要求（极简）

| 资源 | 规格 | 备注 |
|------|------|------|
| CPU | 2 核 | 仅做编排 |
| 内存 | 4GB | Python 进程 |
| 存储 | 50GB SSD | 日志 |
| 网络 | LAN 出站 | Socket 到 Device |

**单 Worker 支持 Device 数**：8-10 Device（仅 Socket 转发）

### 9.3 网络要求

| 通道 | 协议 | 端口 | 方向 |
|------|------|------|------|
| Worker → Backend | HTTPS + WSS | 443 | 出站 |
| Device → Backend | HTTPS | 443 | 出站 |
| Device → OSS | HTTPS | 443 | 出站 |
| Worker ↔ Device | TCP Socket | 8765 | 双向（LAN） |

---

## 10. 与 Plan A / Plan B 对比

| 维度 | Plan A（Worker 端 Airtest） | Plan B（Device 端 Airtest） | **Plan C（Device 端 AutoX.js）** |
|------|--------------------------|--------------------------|--------------------------------|
| **Airtest/AutoX.js 引擎位置** | Worker 桌面 | Android Device | **Android Device** |
| **Device Agent 包大小** | ~5MB | ~70MB | **~22MB** |
| **Worker 硬件成本** | ¥600/月（8C 16GB） | ¥150/月（2C 4GB） | **¥150/月** |
| **单 Worker Device 数** | 2-3（CPU 瓶颈） | 8-10 | **8-10** |
| **单事务 ATT** | 5-8 min | 3-5 min | **3-5 min** |
| **冷启动时间** | <2s | 5-8s | **<1s** |
| **设备 RAM 要求** | 任意 | ≥4GB | **≥3GB** |
| **设备采购成本** | 任意 | ¥1500-2500 | **¥800-1500** |
| **脚本语言** | Python | Python | **JavaScript** |
| **UI 反射原理** | ADB (Worker) | POCO + a11y (Device) | **AccessibilityService** |
| **图像识别能力** | opencv (强) | opencv (强) | **内置（弱）** |
| **OCR** | 需集成 | 需集成 | **内置** |
| **远程调试** | 桌面 IDE 强 | 桌面 IDE 强 | **设备端日志（弱）** |
| **代码可审计** | Python（强） | Python（强） | **JS（中等）** |
| **License 风险** | 0 | 0 | **🔴 需法务确认** |
| **实施工作量** | 5 周 1 人 | 10 周 2 人 | **7 周 2 人** |
| **维护成本** | 中 | 中高（Python 运行时） | **中（Java 进程稳定）** |

**互补性**：
- Plan A：默认主架构（已 commit）
- Plan B：Python 团队、目标 APP UI 频繁变动
- **Plan C**：JS 团队、设备成本敏感、运维依赖现场

---

## 11. 实施步骤

### 11.1 阶段划分

**阶段 0：License 确认（1 周，必做）**
- 法务审查 AutoX.js License
- 评估 Auto.js Pro 历史商业争议对 AutoX.js 分叉的影响
- 输出合规报告

**阶段 1：技术 PoC（1 周）**
- AutoX.js 项目打包 Hello World
- AccessibilityService 集成
- Socket 通信 PoC
- 目标 APP 兼容性测试

**阶段 2：Device Agent 基础（2 周）**
- Kotlin 主进程 + Rhino 引擎集成
- Socket 服务端 + 白名单
- OSS 下载器
- 沙箱 + FileProvider
- JavaBridge 实现

**阶段 3：脚本执行引擎（2 周）**
- ScriptEngine 实现（Kotlin + JS 桥接）
- Step → AutoX.js API 映射
- 错误处理 + 重试
- 截图与上报

**阶段 4：脚本动态下发（1 周）**
- OSS 版本拉取
- 本地缓存策略
- Lazy Load 优化
- 热更新机制

**阶段 5：Worker 编排（1 周）**
- 纯编排器实现
- Step 串行下发
- Retry Policy
- 超时熔断

**阶段 6：测试与优化（1 周）**
- L4 录屏回归
- ATT 压测
- APK 体积优化
- 内存/CPU 优化

**总工作量：约 7 周 / 2 人**（比 Plan B 少 3 周，因为无 Chaquopy 集成）

### 11.2 关键技术风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| AutoX.js License 不可商用 | 中 | **必做：阶段 0 法务确认** |
| 目标 APP 屏蔽 accessibility | 中 | 控件 + 图像 fallback；协调目标 APP 厂商 |
| Rhino 引擎性能问题 | 低 | 简化脚本；可换 QuickJS |
| 图像识别精度不足 | 中 | ROI 限定 + 多尺度 + OCR 辅助 |
| JS 调试能力弱 | 中 | 详细日志 + 设备端 IDE；远程 logcat 推送 |

---

## 12. 风险与缓解（专属）

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| **License 商业使用风险** | 无法商用 | 🔴 高 | 阶段 0 必做法务确认；不可用则退回 Plan A |
| AccessibilityService 被用户误关 | UI 自动化失效 | 高 | 启动时强提示；检测到关闭时告警 |
| 目标 APP 升级 UI 大改 | 脚本批量失效 | 高 | L4 录屏回归；模板版本化管理 |
| AutoX.js 图像识别误识别 | Step 失败 | 中 | 多模板融合；超时熔断 |
| JS 引擎性能瓶颈 | 复杂脚本慢 | 低 | Rhino 可换 QuickJS；简化脚本逻辑 |
| 长期维护可持续性 | 社区驱动 | 中 | 锁定 AutoX.js v6+ 版本；内部 fork 备份 |

---

## 13. 验收标准

### 13.1 功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| AC-C-001 | Device Agent 启动 | AutoX.js + Rhino 引擎 < 1s 启动完成 |
| AC-C-002 | APK 体积 | 编译后 APK ≤ 25MB |
| AC-C-003 | Socket 通信 | 100 条 EXECUTE_STEP 指令全部成功响应 |
| AC-C-004 | OSS 下载 | 100MB 影像文件直连下载，MD5 校验通过 |
| AC-C-005 | 脚本下发 | 新版本 Flow 脚本 30s 内完成下载并可用 |
| AC-C-006 | Step 执行 | 6 种 action_type（OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/WAIT）100% 可用 |
| AC-C-007 | 控件反射 | 目标保险 APP 主要 UI 元素可被 a11y 识别 |
| AC-C-008 | OCR 识别 | 内置 OCR 准确率 ≥ 85%（针对行驶证/合格证字段） |
| AC-C-009 | 沙箱隔离 | 其他 APP 无法访问 `/sdcard/sandbox/` |
| AC-C-010 | 文件清理 | SUCCESS 立即清理；FAIL 24h 后清理；DLQ 7d 后清理 |
| AC-C-011 | 重试机制 | Step 失败按 Retry Policy（3 次，指数退避）重试 |
| AC-C-012 | 超时熔断 | Step 超 60s 强制终止，事务 FAIL |
| AC-C-013 | 截图证据 | 每个 Step 完成自动截图保存并上传 Backend |
| AC-C-014 | 状态上报 | Step 结果实时通过 Socket 上报 Worker |
| AC-C-015 | 白名单 IP | 非白名单 IP Socket 连接 403 |
| AC-C-016 | 热更新 | Flow 脚本新版本 Agent 重启后立即可用 |
| AC-C-017 | Intent 上传 | UPLOAD 步骤优先用 Intent 直传（无需 UI 自动化） |

### 13.2 非功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| NAC-C-001 | 单事务 ATT | **3-5 min**（仅 RUNNING 阶段） |
| NAC-C-002 | 单 Worker 并发 | **8-10 Device/Worker** |
| NAC-C-003 | 设备占用内存 | 空闲 < 50MB；峰值 < 100MB |
| NAC-C-004 | 设备 CPU | 空闲 < 10%；执行峰值 < 40% |
| NAC-C-005 | 冷启动时间 | **< 1s** |
| NAC-C-006 | Worker 硬件 | 2C 4GB 可支撑 10 Device |
| NAC-C-007 | 设备最低要求 | Android ≥ 8.0，RAM ≥ 3GB |
| NAC-C-008 | 设备采购成本 | ¥800-1500 即可（无需中高端） |
| NAC-C-009 | License 合规 | 法务出具 AutoX.js 商用许可确认函 |

---

## 14. 决策记录

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| 文档定位 | 主架构 / Plan B / Plan C | **Plan C（参考材料）** | 与 Plan A/B 互补的第三选项 |
| Airtest/AutoX.js 选择 | Airtest / AutoX.js / 混合 | **AutoX.js** | 业务匹配度更高，团队上手成本低 |
| AutoX.js 部署方式 | 直接安装 / 项目打包 | **项目打包** | 生产部署可控，企业签名 |
| JS 引擎 | Rhino / QuickJS / V8 | **Rhino** | AutoX.js 默认，兼容性好 |
| UPLOAD 实现 | UI 自动化 / Intent 直传 | **Intent 直传优先 + UI 回退** | 降低模板维护成本 |
| Worker 端 AutoX.js | 安装 / 不安装 | **不安装** | 保持 Worker 极简 |
| APK 体积优化 | 完整功能 / 精简 | **精简**（仅必要模块） | 目标 ≤ 25MB |
| Worker 单机 Device 数 | 2-3 / 8-10 | **8-10** | 仅 Socket 转发，无 CPU 瓶颈 |
| License 风险处置 | 接受 / 法务确认 | **法务确认（前置条件）** | 商业使用必须合规 |
| 实施工作量 | 5 周 / 7 周 / 10 周 | **7 周 / 2 人** | 比 Plan B 少 3 周 |

---

## 15. 关联文档

- 主 PRD：`docs/superpowers/specs/2026-06-02-prd-design.md` V1.1
- 主架构 Plan A（Worker 端）：`docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` V1.0
- Plan B（Device 端 Airtest）：`docs/superpowers/specs/2026-06-03-android-device-airtest-architecture-design.md` V1.0
- **对比文档（本文档引用）**：`docs/superpowers/specs/2026-06-03-airtest-vs-autoxjs-comparison.md` V1.0
- PRD 评审：`docs/superpowers/specs/2026-06-02-prd-review.md`

---

**文档状态推进路径**：

`Draft`（参考材料）→ 不进入 Review/Approved 流程，作为长期技术决策参考
