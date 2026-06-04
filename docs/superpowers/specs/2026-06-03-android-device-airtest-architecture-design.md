# Design: Android Device 端 Airtest 执行架构（参考材料）

| 字段 | 内容 |
|------|------|
| 设计主题 | 通过 Android Device 执行 Airtest 脚本的详细架构与实现方案 |
| 文档版本 | V1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | Draft（参考材料） |
| 文档定位 | **参考材料**：作为 Worker 端方案的对照/Plan B，不替代已批准的 Worker 端架构 |
| 技术选型 | **Chaquopy + Airtest**（已确认）；**OSS 动态下发**（已确认） |
| 关联 PRD | `docs/superpowers/specs/2026-06-02-prd-design.md` V1.1 |
| 关联设计 | `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` V1.0 |
| 作者 | brainstorming skill |

**修订记录**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-03 | 初稿（参考材料） | office-hours |

---

## 1. 设计定位

### 1.1 与主架构的关系

| 文档 | 角色 | 当前状态 |
|------|------|----------|
| `2026-06-02-prd-design.md` V1.1 | 主 PRD（已 Review） | 主架构基线 |
| `2026-06-03-rpa-worker-side-architecture-design.md` | **主架构（已 commit）** | **当前执行方案（Plan A）** |
| **本文档** | **参考材料（Plan B）** | 备用方案，对照参考 |

### 1.2 使用场景

- **场景 A：Plan A 失败回退**：Worker 端架构在生产遇到不可解决问题（如 ATT 超预期、ADB 检测被目标 APP 加强）时启用
- **场景 B：架构评审对照**：在 Plan A 落地前，作为架构对照材料
- **场景 C：培训/学习**：作为 Airtest 在 Android 端运行的技术参考
- **场景 D：混合架构基础**：若后续需要"高延迟操作在 Device 端"，可作为子模块参考

### 1.3 何时不应使用本设计

- 当前生产部署：应使用 Plan A（Worker 端 Airtest）
- 性能要求高且稳定的场景：Worker 端 ADB 通信延迟可控
- 无 Chaquopy 工程经验：实施风险高

---

## 2. 核心架构

### 2.1 三层架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                          云端 (Backend)                               │
│  - 事务接入/路由 (FR-SVR-001~003)                                      │
│  - 调度中心 (Redis Stream Consumer Group)                              │
│  - 状态机管理 (FR-SVR-008)                                            │
│  - OSS 签名 URL 生成与续签                                             │
│  - Flow 脚本包存储 (FR-SVR-016)                                        │
└─────────────────┬────────────────────────────────────────────────────┘
                  │ HTTPS REST + WSS (outbound from Worker)
                  │
┌─────────────────▼────────────────────────────────────────────────────┐
│                   Worker 桌面端 (Python 3.14 + UV)                     │
│  【本架构中 Worker 不含 Airtest runtime，仅做编排】                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  编排器 (FR-CLI-005 纯编排)                                    │    │
│  │  - 接收 TASK_DISPATCH                                         │    │
│  │  - 调 /oss-urls 拿签名 URL                                     │    │
│  │  - Socket 通知 Device 下载影像                                 │    │
│  │  - 等待 Device 下载完成                                       │    │
│  │  - Socket 通知 Device 执行 Step (具体 action + params)         │    │
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
│           Android Device + Device Agent (含 Airtest runtime)          │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Device Agent App (Java/Kotlin 主进程)                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │    │
│  │  │ SocketServer    │  │ OssDownloader   │  │ ResultUploader│  │    │
│  │  │ :8765 监听       │  │ (原生 OkHttp)    │  │ (原生 HTTP)   │  │    │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘  │    │
│  │  ┌─────────────────────────────────────────────────────────┐ │    │
│  │  │ Chaquopy Python Runtime (embedded)                       │ │    │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │ │    │
│  │  │  │ airtest       │  │ pocoui        │  │ opencv       │ │ │    │
│  │  │  │ (图像识别)     │  │ (UI 反射)      │  │ (headless)   │ │ │    │
│  │  │  └───────────────┘  └───────────────┘  └──────────────┘ │ │    │
│  │  │  ┌──────────────────────────────────────────────────┐   │ │    │
│  │  │  │ ScriptEngine (脚本执行引擎)                        │   │ │    │
│  │  │  │ - 加载 Flow 脚本 (.py)                              │   │ │    │
│  │  │  │ - 监听 Socket 命令 (EXECUTE_STEP)                  │   │ │    │
│  │  │  │ - 调用 Airtest API 执行                            │   │ │    │
│  │  │  │ - 截图 + 上报                                      │   │ │    │
│  │  │  └──────────────────────────────────────────────────┘   │ │    │
│  │  └─────────────────────────────────────────────────────────┘ │    │
│  │  ┌─────────────────────────────────────────────────────────┐ │    │
│  │  │ 沙箱存储                                                  │ │    │
│  │  │  - 输入影像: /sdcard/sandbox/{txn_id}/                   │ │    │
│  │  │  - 脚本: /data/data/com.iiil.auto/files/flows/.../      │ │    │
│  │  │  - 截图: /sdcard/Pictures/airtest/                       │ │    │
│  │  └─────────────────────────────────────────────────────────┘ │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  AccessibilityService (UI 自动化权限)                                   │
│  目标保险 APP (被 Airtest 控制)                                          │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 三端职责对照

| 维度 | Backend（云端） | Worker（桌面端） | **Device Agent（含 Airtest）** |
|------|----------------|----------------|-----------------------------|
| 角色 | 调度/编排中心 | **纯编排器**（不含 Airtest） | **Airtest 实际执行点** |
| 语言 | Python（隐含） | Python ≥ 3.14 | **Kotlin/Java（主壳）+ Python（Airtest 运行时）** |
| 核心框架 | FastAPI/Django | Socket/HTTP 客户端 | **Chaquopy + airtest + pocoui** |
| 持有 Flow 脚本 | ✅（OSS） | ⚠️（仅元数据，不执行） | ✅（OSS 下载 + 本地缓存 + 实际执行） |
| 持有输入影像 | ❌ | ❌（不中转字节流） | ✅（直连 OSS 下载） |
| UI 自动化 | ❌ | ❌ | ✅（Airtest 驱动） |
| 状态机管理 | ✅（强一致） | ⚠️（Step 状态聚合） | ❌ |
| Step 执行 | ❌ | ❌（仅下发指令） | ✅（Airtest API） |
| 网络方向 | 入站 443 | 出站 443 | **入站 Socket 8765 + 出站 443（OSS）** |

### 2.3 关键不变量（与 V1.1 PRD 一致）

- **OSS 直连下载**：Device Agent 直连 OSS 签名 URL，Worker 不中转文件字节流
- **CONFIRM 流程移除**：CONFIRM Step 退化为普通 Step
- **业务类型用户指定**：用户提交时显式指定
- **Redis Stream MVP 必需**：调度层不调整

---

## 3. Android Device Agent 详细架构

### 3.1 技术选型：Chaquopy

**Chaquopy** 是在 Android Studio 中集成 Python 解释器的官方方案。

| 维度 | 说明 |
|------|------|
| **集成方式** | Android Studio Gradle Plugin |
| **Python 版本** | Python 3.8 - 3.12（不同 Chaquopy 版本支持不同） |
| **包管理** | 标准 pip（通过 `chaquopy.requirements` 配置） |
| **Java ↔ Python 互调** | `Python.getInstance().getModule("...")` 双向调用 |
| **APK 体积影响** | +30-50MB（含 Python 解释器 + 依赖库） |
| **性能** | Python 调用 overhead 约 5-20ms/次；opencv 图像匹配 100-500ms/次 |
| **启动时间** | Python 运行时初始化 +1-3s |

### 3.2 Agent App 内部架构

```
com.iiil.auto/.agent/
├── MainActivity
├── service/
│   ├── AgentForegroundService
│   │   ├── 启动 Python 运行时（一次性）
│   │   ├── 加载 Airtest Runtime
│   │   ├── 监听 Socket 8765
│   │   └── 命令分发到 Python 引擎
│   ├── OssDownloadService
│   │   ├── HTTPS 下载 (OkHttp)
│   │   ├── 断点续传 (HTTP Range)
│   │   ├── MD5 校验
│   │   └── 续签请求
│   ├── ResultUploadService
│   │   ├── 截图上传（OSS 或 Backend）
│   │   ├── Step 结果上报
│   │   └── 心跳
│   └── AccessibilityService
│       ├── UI 元素反射
│       └── POCO Agent 支撑
├── python/  (Chaquopy 调用)
│   ├── runtime/
│   │   ├── airtest_runtime.py    # Airtest 初始化
│   │   ├── script_engine.py      # 脚本执行引擎
│   │   └── step_executor.py      # Step → Airtest API 映射
│   ├── protocol/
│   │   └── command_handler.py    # Socket 命令解析
│   └── api/
│       └── java_bridge.py        # 与 Kotlin/Java 互调
├── net/
│   ├── SocketServer (Kotlin)
│   ├── OssClient (Kotlin)
│   └── BackendApi (Kotlin)
└── ui/
    └── DeviceStateActivity
```

### 3.3 Chaquopy 集成配置

`app/build.gradle` 关键配置：

```gradle
android {
    defaultConfig {
        ndk {
            abiFilters 'armeabi-v7a', 'arm64-v8a', 'x86_64'
        }
    }
}

plugins {
    id 'com.chaquo.python' version '15.0.0'
}

chaquopy {
    version "3.10"
    pip {
        install "airtest==1.3.4"
        install "pocoui==1.0.94"
        install "opencv-python-headless==4.8.0.76"
        install "numpy==1.24.4"
        install "Pillow==10.0.1"
        install "requests==2.31.0"
    }
    pythonOptions {
        // 性能调优
        buildPython "3.10.12"
    }
}
```

**包大小估算**：

| 组件 | 大小 |
|------|------|
| Chaquopy Python 运行时 | ~15MB |
| airtest + 依赖 | ~5MB |
| opencv-python-headless | ~30MB（vs opencv-python 80MB） |
| pocoui | ~2MB |
| numpy | ~10MB |
| PIL | ~5MB |
| 其他 | ~5MB |
| **总计** | **~70MB**（APK 总包大小） |

### 3.4 Airtest Runtime 启动流程

```python
# airtest_runtime.py (Chaquopy 启动时执行)
from airtest.core.api import *
from airtest.core.android import Android
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
import logging

logger = logging.getLogger("airtest_runtime")

def initialize_airtest():
    """初始化 Airtest + POCO"""
    # 1. 初始化 Airtest 设备连接
    # 关键：在 Android 上，airtest 通过本地 ADB daemon 通信
    # 需提前启动 adbd (系统级)
    # 实际方案：使用 POCO + AndroidUiautomation 代替 ADB
    
    # 2. 初始化 POCO（无需 ADB）
    global poco
    poco = AndroidUiautomationPoco(
        use_airtest_input=True,
        screenshot_each_action=False
    )
    
    logger.info("Airtest Runtime initialized")

# 启动时调用
initialize_airtest()
```

**注意**：纯 Airtest 在 Android 上需要 ADB 通信，**实际更常见的方案是**：
- **POCO + AndroidUiautomation** 替代完整 Airtest
- 或者用 **AccessibilityService + UIAutomator2** 实现
- 详见 §3.6 关键技术挑战

### 3.5 Script Engine（脚本执行引擎）

```python
# script_engine.py
import os
import importlib.util
import time
import json
from typing import Dict, Any

class ScriptEngine:
    def __init__(self, sandbox_root: str = "/data/data/com.iiil.auto/files/flows"):
        self.sandbox_root = sandbox_root
        self.current_module = None
        self.current_step = None
        
    def load_script(self, flow_id: str, version: str) -> str:
        """从本地缓存加载 Flow 脚本"""
        script_path = f"{self.sandbox_root}/{flow_id}/{version}/script.py"
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # 动态加载 Python 模块
        spec = importlib.util.spec_from_file_location("flow_script", script_path)
        self.current_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.current_module)
        return script_path
    
    def execute_step(self, step_id: str, action_type: str, params: Dict[str, Any]) -> Dict:
        """执行单个 Step"""
        start = time.time()
        try:
            result = self._dispatch(action_type, params)
            return {
                "step_id": step_id,
                "status": "SUCCESS",
                "duration_ms": int((time.time() - start) * 1000),
                "result": result
            }
        except TimeoutError as e:
            return {"step_id": step_id, "status": "TIMEOUT", "error": str(e)}
        except Exception as e:
            return {"step_id": step_id, "status": "FAIL", "error": str(e)}
    
    def _dispatch(self, action_type: str, params: Dict) -> Any:
        """根据 action_type 调用 Airtest API"""
        if action_type == "OPEN_APP":
            from airtest.core.api import start_app
            return start_app(params["package_name"])
        elif action_type == "INPUT":
            from airtest.core.api import text
            return text(params["text"])
        elif action_type == "CLICK":
            from airtest.core.api import touch
            if "template" in params:
                return touch(Template(params["template"]), 
                            timeout=params.get("timeout", 10))
            else:
                return touch((params["x"], params["y"]))
        elif action_type == "UPLOAD":
            return self._handle_upload(params)
        elif action_type == "SCREENSHOT":
            from airtest.core.api import snapshot
            return snapshot(filename=params.get("filename", "step.png"))
        elif action_type == "WAIT":
            from airtest.core.api import wait
            if "template" in params:
                return wait(Template(params["template"]), 
                          timeout=params.get("timeout", 30))
            else:
                time.sleep(params.get("seconds", 1))
                return True
        else:
            raise ValueError(f"Unknown action_type: {action_type}")
    
    def _handle_upload(self, params: Dict) -> Any:
        """UPLOAD 步骤的复合操作：打开文件选择器 + 选择沙箱文件"""
        from airtest.core.api import touch, sleep, exists, Template
        
        file_name = params["file_name"]  # 例如 "idcard.jpg"
        sandbox_path = f"/sdcard/sandbox/{params['transaction_id']}/{file_name}"
        
        # Step 1: 点击上传按钮（可能已通过 CLICK Step 触发）
        # Step 2: 等待文件选择器弹出
        sleep(2)
        
        # Step 3: 切换到文件管理器（不同 APP 处理不同）
        # 这里需要根据具体目标 APP 的文件选择器 UI 调整
        if exists(Template(r"tpl/file_picker_browse.png")):
            touch(Template(r"tpl/file_picker_browse.png"))
            sleep(1)
        
        # Step 4: 导航到沙箱目录
        # 通常需要点击"显示内部存储"或类似按钮
        # 复杂场景需要多步 Airtest 操作
        
        # Step 5: 选择文件
        # ...
        
        # Step 6: 确认
        # ...
        
        return {"uploaded": file_name, "sandbox_path": sandbox_path}
```

### 3.6 关键技术挑战与解决方案

#### 挑战 1：Airtest 在 Android 上的 ADB 依赖

**问题**：Airtest 默认通过 ADB 控制设备，需要 ADB server 通信。在 Android 设备上启动 ADB server 不现实。

**解决方案**：

| 方案 | 实现 | 优缺点 |
|------|------|--------|
| **A. POCO + AndroidUiautomation** | 用 POCO 替代完整 Airtest；POCO 通过 AccessibilityService 反射 UI | ✅ 不需 ADB；⚠️ 需要目标 APP 不屏蔽 accessibility |
| **B. UIAutomator2 替代** | 设备原生 UIAutomator API（Java） | ✅ 最稳定；⚠️ 偏离 Airtest |
| **C. 启动本机 adbd** | 设备启动 ADB daemon 服务 | ⚠️ 需 root；不推荐生产 |

**推荐**：**方案 A**（POCO + AndroidUiautomation），保持与 Airtest 生态兼容。

#### 挑战 2：图像识别性能

**问题**：opencv 图像匹配在低性能 Android 设备上 200-1000ms/次，影响 ATT。

**解决方案**：

```python
# step_executor.py 中的优化
def execute_step_with_optimization(self, step):
    if step["action_type"] == "CLICK" and "template" in step["params"]:
        template_path = step["params"]["template"]
        
        # 1. 缩放模板（如果原图过大）
        # 2. 限定 ROI (region of interest) 减少匹配范围
        # 3. 缓存识别结果（短时间内相同模板不重识别）
        ...
```

| 优化手段 | 预期提升 |
|----------|----------|
| ROI 限定 | 2-3x |
| 模板缩放 | 1.5-2x |
| 识别缓存 | 5-10x（重复模板） |
| **综合** | **3-5x** |

#### 挑战 3：UPLOAD 步骤的复杂性

**问题**：不同保险 APP 的文件选择器 UI 差异大，难以通用化。

**解决方案**：

```python
# 方案 1: 通过系统 Intent（推荐）
def upload_via_intent(transaction_id, file_name, target_package):
    file_path = f"/sdcard/sandbox/{transaction_id}/{file_name}"
    # 构造 ACTION_SEND intent
    intent = Intent(Intent.ACTION_SEND)
    intent.setType("image/*")
    intent.putExtra(Intent.EXTRA_STREAM, FileProvider.getUriForFile(
        context, "com.iiil.auto.fileprovider", File(file_path)
    ))
    intent.setPackage(target_package)  # 直接发给目标 APP
    context.startActivity(intent)
    
# 方案 2: 通用文件选择器（保底）
def upload_via_file_picker(file_name, transaction_id):
    # 使用 airtest 自动化文件选择器
    # 需要为每个目标 APP 录制模板
    ...
```

**推荐**：**优先用 Intent 方案**（无需 UI 自动化），回退到文件选择器方案。

### 3.7 沙箱与文件管理

| 位置 | 路径 | 权限 | 清理时机 |
|------|------|------|----------|
| **输入影像** | `/sdcard/sandbox/{txn_id}/` | 700 + FileProvider 授权 | SUCCESS: 立即; FAIL: 24h; DLQ: 7d |
| **Flow 脚本** | `/data/data/com.iiil.auto/files/flows/{flow_id}/{version}/` | 700 | 永久保留（除非版本淘汰） |
| **Airtest 截图** | `/sdcard/Pictures/airtest/{txn_id}/` | 700 | 事务完成 |
| **沙箱 FileProvider** | `content://com.iiil.auto.fileprovider/sandbox/{txn_id}/{file}` | 700 | 短期授权 |

**FileProvider 授权清单**：
```xml
<!-- AndroidManifest.xml -->
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="com.iiil.auto.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>

<!-- res/xml/file_paths.xml -->
<paths>
    <external-path name="sandbox" path="sandbox/"/>
    <external-files-path name="flows" path="flows/"/>
</paths>
```

### 3.8 权限清单

```xml
<!-- AndroidManifest.xml 关键权限 -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" 
                 android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" 
                 android:maxSdkVersion="29" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.WAKE_LOCK" />

<!-- AccessibilityService 声明 -->
<service
    android:name=".service.AirtestAccessibilityService"
    android:label="3IS Airtest Service"
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
| ❌ airtest | 不在 Worker 端执行 Airtest |
| ❌ pocoui | 同上 |
| ❌ opencv | 同上 |
| ❌ Chaquopy | 同上 |
| ❌ ADB | 不通过 ADB 控制设备（仅 Socket） |

**Worker 包大小**：~50MB（仅 Python 解释器 + 标准库 + requests/websockets），远小于 Device Agent 的 ~70MB。

### 4.3 执行流程

```
[阶段 1-3：启动/心跳/脚本同步 与 Worker 端方案相同]

阶段 4：任务接收与执行（本架构特有）

4.1  WebSocket /ws/v1/dispatch 收到 TASK_DISPATCH
4.2  POST /api/v1/tasks/{id}/ack
4.3  POST /api/v1/transactions/{id}/oss-urls → 拿到 signed_urls[]
4.4  ── Socket:8765 ──► Device: DOWNLOAD_FILES {oss_urls}
4.5  Device 直连 OSS 下载到 /sdcard/sandbox/{txn_id}/
4.6  Device 完成 → 上报 download-complete (Socket)
4.7  Worker 收到下载完成 → 事务进入 RUNNING
4.8  ── Socket ──► Device: EXECUTE_STEP {step_id, action_type, params}
4.9  Device Airtest Runtime 执行 Step
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

**消息格式**：

```json
// ============================================
// Worker → Device 指令
// ============================================

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
    "step_id": "step-003",
    "action_type": "CLICK",
    "action_params": {
      "template": "tpl/insurance_tab.png",
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

// ============================================
// Device → Worker 事件
// ============================================

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
  "status": "SUCCESS",  // SUCCESS | FAIL | TIMEOUT
  "duration_ms": 1234,
  "screenshot_path": "/sdcard/Pictures/airtest/TXN-.../step-003.png",
  "screenshot_uploaded_to": "https://oss.example.com/...?signature=...",
  "error_message": null
}

{
  "event": "OSS_URL_EXPIRED",
  "transaction_id": "TXN-20260603-00001",
  "signed_url_id": "uuid-xxx"
}
```

### 5.2 Device ↔ Backend REST（变更最小）

| Method | Path | 描述 | 变更 |
|--------|------|------|------|
| POST | /api/v1/devices/{id}/ready | 启动就绪 | **不变** |
| POST | /api/v1/devices/{id}/status | 30s 心跳 | **不变** |
| POST | /api/v1/devices/{id}/step-result | 上报 Step 结果 | **保留**（V1.1 FR-MOB 已定义） |
| POST | /api/v1/oss-urls/{id}/refresh | OSS URL 续签 | **不变** |

**关键变化**：相比 Worker 端方案，**保留**了 `/devices/{id}/step-result` 接口（V1.1 FR-MOB）。

---

## 6. 脚本动态下发机制

### 6.1 流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 管理员在 Backend 上传 Flow 脚本                            │
│     POST /api/v1/flows/{id}/versions (FR-SVR-016)           │
│     → 存储到 OSS: /flows/{flow_id}/{version}/script.py      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Device Agent 启动时检查脚本版本                            │
│     GET /api/v1/workers/scripts/versions (Worker Token)     │
│     Worker 代理 Device 拉取版本列表                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 比对本地缓存                                              │
│     Device 本地: /data/data/com.iiil.auto/files/flows/.../   │
│     若有新版本 → 调用脚本下载 API                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 下载脚本                                                  │
│     GET /api/v1/flows/{id}/versions/{version}/download      │
│     → 直接从 OSS 下载 script.py + 模板图片                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  5. 本地缓存与校验                                             │
│     存储到 /data/data/.../files/flows/{flow_id}/{version}/   │
│     旧版本备份为 .bak                                         │
│     校验: python -m py_compile script.py                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  6. 预加载（Lazy Loading）                                    │
│     Device Agent 不预加载所有脚本                               │
│     收到 EXECUTE_STEP 指令时按需加载对应 flow_id 的脚本          │
│     ScriptEngine.load_script(flow_id, version)               │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 缓存策略

| 策略 | 说明 |
|------|------|
| **预下载** | Agent 启动时拉取已发布 Flow 的最新版本（防运行时下载阻塞） |
| **Lazy Load** | 收到 Step 指令时按需 import Python 模块 |
| **版本保留** | 最近 3 个版本保留本地缓存（.bak + current） |
| **MD5 校验** | 下载完成后 MD5 校验，不匹配自动重试 |
| **空间管理** | LRU 淘汰，超 500MB 时清理旧版本 |

### 6.3 脚本热更新

| 场景 | 处理 |
|------|------|
| 脚本新增版本 | Agent 启动时检测 → 下载 → 切换当前版本 |
| 脚本 Bug 修复 | 同上，事务间热更新（当前事务完成后下次生效） |
| 紧急回滚 | Worker 检测到脚本执行失败率高 → 通知 Device 切回 .bak 版本 |
| 强制升级 | Backend 配置 `min_version`，Device 低于阈值拒绝执行 |

---

## 7. 关键实现代码示例

### 7.1 Chaquopy 启动（Kotlin 主进程）

```kotlin
// MainActivity.kt
class MainActivity : AppCompatActivity() {
    private lateinit var python: Python
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 启动 Python 运行时（一次性）
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        python = Python.getInstance()
        
        // 初始化 Airtest Runtime
        val airtestModule = python.getModule("airtest_runtime")
        airtestModule.callAttr("initialize_airtest")
        
        // 启动前台服务
        startForegroundService(Intent(this, AgentForegroundService::class.java))
    }
}
```

### 7.2 Socket 服务端（Kotlin）

```kotlin
// SocketServer.kt
class SocketServer(private val port: Int = 8765) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private var serverSocket: ServerSocket? = null
    
    fun start() {
        scope.launch {
            serverSocket = ServerSocket(port)
            while (isActive) {
                val client = serverSocket?.accept() ?: break
                
                // IP 白名单校验
                val clientIp = (client.remoteSocketAddress as InetSocketAddress).address.hostAddress
                if (!Whitelist.isAllowed(clientIp)) {
                    client.close()
                    Log.w("SocketServer", "Rejected non-whitelisted IP: $clientIp")
                    continue
                }
                
                launch { handleClient(client) }
            }
        }
    }
    
    private suspend fun handleClient(socket: Socket) {
        val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
        val writer = PrintWriter(socket.getOutputStream(), true)
        
        while (socket.isConnected) {
            val line = reader.readLine() ?: break
            val command = JSON.parse(line)
            
            // 转发到 Python 引擎
            val response = commandHandler.handle(command)
            writer.println(JSON.toJson(response))
        }
    }
}
```

### 7.3 命令处理器（Python）

```python
# command_handler.py
from airtest_runtime import *
from script_engine import ScriptEngine
import json
import logging

logger = logging.getLogger("command_handler")
engine = ScriptEngine()

def handle_command(cmd_json: str) -> str:
    cmd = json.loads(cmd_json)
    cmd_type = cmd.get("cmd")
    
    if cmd_type == "DOWNLOAD_FILES":
        # 触发 OSS 下载（Kotlin 侧执行）
        return trigger_oss_download(cmd["params"])
    
    elif cmd_type == "EXECUTE_STEP":
        step = cmd["params"]
        try:
            # 1. 加载 Flow 脚本（首次执行某 flow 时）
            engine.load_script(step["flow_id"], step["version"])
            
            # 2. 执行 Step
            result = engine.execute_step(
                step["step_id"],
                step["action_type"],
                step["action_params"]
            )
            
            return json.dumps({
                "event": "STEP_RESULT",
                "request_id": cmd["request_id"],
                "step_id": step["step_id"],
                **result
            })
        except Exception as e:
            logger.exception("Step execution failed")
            return json.dumps({
                "event": "STEP_RESULT",
                "step_id": step["step_id"],
                "status": "FAIL",
                "error_message": str(e)
            })
    
    elif cmd_type == "CLEANUP":
        cleanup_sandbox(cmd["params"]["transaction_id"])
        return json.dumps({"event": "CLEANUP_COMPLETE"})
    
    else:
        return json.dumps({"error": f"Unknown command: {cmd_type}"})
```

### 7.4 Step 定义示例（Flow 脚本）

```python
# /data/data/.../files/flows/FLOW-NEW-001/1.0.0/script.py
# 由 ScriptEngine 动态加载

from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
import time

# 脚本上下文由 ScriptEngine 注入
poco = AndroidUiautomationPoco()

def main(context):
    """
    主流程（context 含 transaction_id, attachments 等）
    注：本架构中 Worker 不会调用此函数；
       Worker 改为单步下发 EXECUTE_STEP。
       此函数仅供开发期调试用。
    """
    # 启动 APP
    start_app("com.example.insurance")
    
    # 等待主页加载
    wait(Template(r"tpl/main_page.png"), timeout=30)
    
    # 点击"新保单"
    touch(Template(r"tpl/new_insurance_tab.png"))
    
    # 输入手机号
    text("13800001234")
    
    # 上传身份证
    upload_image("idcard.jpg")
    
    # 提交
    touch(Template(r"tpl/submit_button.png"))
    
    # 等待成功页面
    assert_exists(Template(r"tpl/success_page.png"), timeout=30)


# 单步执行入口（ScriptEngine 调用）
def step_handler(step_id, action_type, params):
    """与 ScriptEngine.execute_step 对应"""
    # 可以基于 step_id 实现更细粒度逻辑
    ...
```

**注意**：本架构中 Worker 不调用 `main(context)`，而是逐 Step 下发 `EXECUTE_STEP` 指令。脚本可以是"完整流程"或"单步函数"，取决于设计选择。

---

## 8. 性能与限制

### 8.1 APK 包大小

| 组件 | 大小 |
|------|------|
| Kotlin/Java 主进程 | ~5MB |
| Chaquopy Python 运行时 | ~15MB |
| airtest + pocoui | ~7MB |
| opencv-python-headless | ~30MB |
| numpy | ~10MB |
| Pillow + 其他 | ~5MB |
| **总计** | **~70MB** |

对比 Worker 端方案的 Device Agent：**~5MB**（无 Airtest runtime）

### 8.2 运行时性能

| 指标 | Worker 端方案 (ADB) | **Device 端方案 (本架构)** | 差异 |
|------|--------------------|-----------------------|------|
| 单 Step 图像识别 | 200-800ms (USB ADB) | **50-300ms (本地 opencv)** | ✅ 2-3x 更快 |
| 文本输入 | 50-100ms (adb input) | **20-50ms (POCO)** | ✅ 2x 更快 |
| 单事务 ATT | 5-8 min | **3-5 min** | ✅ 30-40% 更快 |
| Step 重试延迟 | 1-3s (USB 通信) | **<500ms (本地)** | ✅ 显著更快 |
| 启动时间 | <2s | **5-8s (Python 启动)** | ⚠️ 慢 3-4s |

### 8.3 内存与 CPU

| 指标 | Device 端方案 | 备注 |
|------|--------------|------|
| 空闲内存 | ~80MB | Chaquopy + Airtest 运行时常驻 |
| Step 执行峰值 | ~250MB | opencv 图像匹配峰值 |
| CPU 占用 | 5-15% (空闲) | - |
| 启动 CPU 峰值 | 30% (5s) | Python 解释器初始化 |

**要求**：Android 设备 ≥ 4GB RAM（中高端机型）

### 8.4 已知限制

| 限制 | 影响 | 缓解 |
|------|------|------|
| **AccessibilityService 被禁用** | POCO 无法反射 UI | 引导用户在首次启动时授权 |
| **目标 APP 屏蔽 accessibility** | UI 自动化失效 | 改用图像识别（更慢） |
| **Chaquopy 启动慢** | 冷启动 +5s | 常驻后台服务（已设计） |
| **opencv APK 体积** | 包大 30MB | 用 headless 版本 |
| **Python GIL** | 多 Step 并发受限 | Worker 端单 Step 串行下发（已设计） |
| **目标 APP UI 大改** | 模板失效 | L4 录屏回归 + 快速更新脚本 |

---

## 9. 部署与硬件

### 9.1 Device 硬件要求

| 资源 | 最低 | 推荐 | 备注 |
|------|------|------|------|
| Android 版本 | **10** | **12+** | Chaquopy 兼容性 |
| RAM | **4GB** | **6GB+** | opencv 内存峰值 |
| 存储 | 8GB 可用 | 16GB+ | APK + 沙箱 + 脚本 |
| CPU | 中端 | 高端 | 图像识别性能 |
| USB 接口 | 数据 + 充电 | - | - |
| 网络 | WiFi (LAN) | - | Socket 通信 |

### 9.2 Worker 硬件要求（极简）

| 资源 | 规格 | 备注 |
|------|------|------|
| CPU | 2 核 | 仅做编排，无需高算力 |
| 内存 | 4GB | Python 进程 + 队列 |
| 存储 | 50GB SSD | 日志 |
| 网络 | LAN 出站 | Socket 到 Device |

**单 Worker 支持 Device 数**：理论上无上限（仅做 Socket 转发）；实际受 LAN Socket 数限制，建议 ≤ 10 Device/Worker。

### 9.3 网络要求

| 通道 | 协议 | 端口 | 方向 |
|------|------|------|------|
| Worker → Backend | HTTPS + WSS | 443 | 出站 |
| Device → Backend | HTTPS | 443 | 出站 |
| Device → OSS | HTTPS | 443 | 出站 |
| Worker ↔ Device | TCP Socket | 8765 | 双向（LAN） |

---

## 10. 与 Worker 端方案对比

| 维度 | Worker 端方案（Plan A） | **Device 端方案（本设计）** |
|------|----------------------|--------------------------|
| **Airtest 引擎位置** | Worker 桌面 | **Device Android** |
| **Device Agent 包大小** | ~5MB | **~70MB** |
| **Worker 硬件成本** | ¥600/月（8C 16GB） | **¥150/月**（2C 4GB） |
| **单 Worker Device 数** | 2-3（CPU 瓶颈） | **8-10**（仅 Socket 转发） |
| **单事务 ATT** | 5-8 min | **3-5 min** |
| **ADB 反检测风险** | 需 PoC 验证 | **无**（本地调用） |
| **脚本调试便利** | 桌面 IDE 调试 | **需 adb logcat + PyCharm 远程** |
| **脚本更新延迟** | Worker 重启即生效 | **Device Agent 启动时检测** |
| **实施复杂度** | 中（Airtest + ADB） | **高（Chaquopy + Python 集成）** |
| **Android 端维护成本** | 低 | **高（Python 运行时维护）** |
| **跨设备一致性** | 强（脚本集中） | **弱（每设备独立缓存）** |
| **冷启动延迟** | <2s | **5-8s（Python 启动）** |
| **OCR/POCO 支持** | 需额外 ADB 桥 | **原生支持** |
| **生产稳定性预期** | 中（ADB 依赖） | **中（Chaquopy 依赖）** |

**互补性**：两个方案各有优劣，可作为 **A/B Plan**：
- **Plan A**（Worker 端）：默认方案，硬件成本可控，调试方便
- **Plan B**（Device 端）：ADB 检测风险高、ATT 要求高、单 Worker 多 Device 场景下启用

---

## 11. 实施步骤（参考）

### 11.1 阶段划分

**阶段 0：技术验证（1 周）**
- Chaquopy POC（Hello World）
- Airtest + POCO 集成测试
- 目标 APP 兼容性测试（accessibility 权限）
- 性能基准测试

**阶段 1：Device Agent 基础（3 周）**
- Kotlin 主进程 + Chaquopy 集成
- Socket 服务端 + 白名单
- OSS 下载器
- 沙箱 + FileProvider
- 基础 Airtest Runtime

**阶段 2：脚本执行引擎（2 周）**
- ScriptEngine 实现
- Step → Airtest API 映射
- 错误处理 + 重试
- 截图与上报

**阶段 3：脚本动态下发（1 周）**
- OSS 版本拉取
- 本地缓存策略
- Lazy Load 优化
- 热更新机制

**阶段 4：Worker 编排（1 周）**
- 纯编排器实现
- Step 串行下发
- Retry Policy
- 超时熔断

**阶段 5：测试与优化（2 周）**
- L4 录屏回归
- ATT 压测
- APK 体积优化
- 内存/CPU 优化

**总工作量：约 10 周 / 2 人**（vs Worker 端方案 5 周 / 1 人）

### 11.2 关键技术风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| Chaquopy 在某些 Android 版本上崩溃 | 中 | 充分测试；准备 PyQt/Kivy 替代 |
| 目标 APP 屏蔽 accessibility | 中 | 回退到纯图像识别；或协调目标 APP 厂商 |
| opencv APK 过大 | 中 | 使用 headless 版本；动态下载 |
| 多设备脚本版本一致性 | 高 | 强版本校验；版本回滚机制 |
| Python 内存泄漏（长时间运行） | 中 | 定期重启 Agent；资源监控 |

---

## 12. 风险与缓解（专属）

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| **Chaquopy 不兼容某些 Android 厂商定制** | Agent 启动失败 | 中 | 充分真机测试；保留 Plan A 兜底 |
| **AccessibilityService 被用户误关** | UI 自动化失效 | 高 | 启动时强提示；检测到关闭时告警 |
| **目标 APP 升级 UI 大改** | 脚本批量失效 | 高 | L4 录屏回归；模板版本化管理 |
| **opencv 图像识别误识别** | Step 失败/误操作 | 中 | 多模板融合；超时熔断 |
| **Python GIL 限制并发** | 多事务并发能力差 | 低 | Worker 端串行下发（已设计） |
| **Chaquopy 升级维护** | 长期维护成本 | 中 | 锁定版本；定期升级窗口 |

---

## 13. 验收标准

### 13.1 功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| AC-D-001 | Device Agent 启动 | Chaquopy + Airtest Runtime 5-8s 内启动完成 |
| AC-D-002 | APK 体积 | 编译后 APK ≤ 80MB |
| AC-D-003 | Socket 通信 | 100 条 EXECUTE_STEP 指令全部成功响应 |
| AC-D-004 | OSS 下载 | 100MB 影像文件直连下载，MD5 校验通过 |
| AC-D-005 | 脚本下发 | 新版本 Flow 脚本 30s 内完成下载并可用 |
| AC-D-006 | Step 执行 | 所有 6 种 action_type（OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/WAIT）100% 可用 |
| AC-D-007 | POCO 反射 | 目标保险 APP 主要 UI 元素可被 POCO 识别 |
| AC-D-008 | 沙箱隔离 | 其他 APP 无法访问 `/sdcard/sandbox/`（除 FileProvider 授权） |
| AC-D-009 | 文件清理 | SUCCESS 立即清理；FAIL 24h 后清理；DLQ 7d 后清理 |
| AC-D-010 | 重试机制 | Step 失败按 Retry Policy（3 次，指数退避 1s/2s/4s）重试 |
| AC-D-011 | 超时熔断 | Step 超 60s 强制终止，事务 FAIL |
| AC-D-012 | 截图证据 | 每个 Step 完成自动截图保存并上传 Backend |
| AC-D-013 | 状态上报 | Step 结果实时通过 Socket 上报 Worker |
| AC-D-014 | 白名单 IP | 非白名单 IP Socket 连接 403 |
| AC-D-015 | 热更新 | Flow 脚本新版本 Agent 重启后立即可用 |

### 13.2 非功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| NAC-D-001 | 单事务 ATT | **3-5 min**（仅 RUNNING 阶段） |
| NAC-D-002 | 单 Worker 并发 | **8-10 Device/Worker** |
| NAC-D-003 | 设备占用内存 | 空闲 < 100MB；峰值 < 300MB |
| NAC-D-004 | 设备 CPU | 空闲 < 15%；执行峰值 < 50% |
| NAC-D-005 | 冷启动时间 | < 8s |
| NAC-D-006 | Worker 硬件 | 2C 4GB 可支撑 8 Device |
| NAC-D-007 | 脚本调试 | 可通过 adb logcat 看到 Airtest 执行日志 |

---

## 14. 决策记录

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| Airtest 路径 | Chaquopy / 原生 uiautomator2 / Buildozer / Termux | **Chaquopy** | 复用 Python 生态，PRD 原始意图 |
| 脚本发布 | APK 内置 / OSS 动态下发 / Socket 推送 | **OSS 动态下发** | 支持热更新，运维成本低 |
| UI 反射 | 完整 Airtest / POCO + AndroidUiautomation | **POCO + AndroidUiautomation** | 解决 ADB 依赖问题 |
| UPLOAD 实现 | 通用文件选择器 / Intent 直传 | **Intent 直传优先 + 文件选择器回退** | 降低模板维护成本 |
| Worker 端 Airtest | 安装 / 不安装 | **不安装** | 保持 Worker 极简 |
| APK 体积优化 | 完整 opencv / headless | **opencv-python-headless** | -50MB |
| Worker 单机 Device 数 | 2-3 / 8-10 | **8-10** | 仅 Socket 转发，无 CPU 瓶颈 |
| 文档定位 | 主架构 / 参考材料 | **参考材料** | Plan A（Worker 端）为主，本设计为 Plan B |

---

## 15. 关联文档

- 主 PRD：`docs/superpowers/specs/2026-06-02-prd-design.md` V1.1
- 主架构设计（Plan A）：`docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` V1.0
- PRD 评审：`docs/superpowers/specs/2026-06-02-prd-review.md`
- 共识会纪要：2026-06-03 brainstorming

---

**文档状态推进路径**：

`Draft`（参考材料）→ 不进入 Review/Approved 流程，作为长期参考
