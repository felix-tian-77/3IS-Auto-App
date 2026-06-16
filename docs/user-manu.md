# 3IS-Auto-App 用户操作手册

**版本:** V1.2 (MVP)
**更新日期:** 2026-06-11
**适用范围:** Backend / Frontend / Worker / Device 四端安装与操作

---

## 目录

1. [系统架构](#1-系统架构)
2. [Backend 安装](#2-backend-安装)
3. [Frontend 安装](#3-frontend-安装)
4. [Worker 安装](#4-worker-安装)
5. [Device 安装](#5-device-安装)
6. [配置指南](#6-配置指南)
7. [快速启动](#7-快速启动)
8. [故障排查](#8-故障排查)
9. [文件结构参考](#9-文件结构参考)
10. [下一步](#10-下一步)

---

## 1. 系统架构
### 1.1 组件拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ PostgreSQL  │  │   Redis     │  │  FastAPI    │          │
│  │   (RDS)     │  │  (Stream)   │  │   :8000     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└──────────────────────────┬──────────────────────────────────┘
                           │
              HTTP :8000 (开发)  /  HTTPS :443 (生产反代)
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐   ┌────────────────────────────────────────┐
│   Frontend   │   │              Worker #1..N              │
│  (Vite:5173) │   │             (Desktop PC)               │
│  React+AntD  │   │  ┌───────────────┐  ┌───────────────┐  │
└──────────────┘   │  │    Airtest    │  │ Socket Client │  │
                   │  │    Runtime    │  │   (LAN/USB)   │  │
                   │  └───────────────┘  └───────────────┘  │
                   └────────────────────┬───────────────────┘
                                        │ USB ADB
                                        ▼
                           ┌─────────────────────┐
                           │      Device #N      │
                           │     (Android)       │
                           └─────────────────────┘
```

### 1.2 端口映射

| 组件 | 端口 | 协议 | 用途 |
|------|------|------|------|
| Backend API | 8000 | HTTP (开发) / HTTPS via 反代 (生产) | REST API + WebSocket |
| Frontend Dev Server | 5173 | HTTP | Vite 开发服务器(含 `/api` → 8000 代理) |
| PostgreSQL | 5432 | TCP | 数据库 |
| Redis | 6379 | TCP | Stream 队列 |
| Worker Socket | 8765/8766/8767 | TCP (局域网) | Worker ↔ Device 通信 |
| ADB | USB (无端口) / TCP 5555 (`adb tcpip` 模式) | — | Worker ↔ Device ADB 连接 |

### 1.3 前置条件

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 0.5+(Python 依赖与虚拟环境管理,替代 pip + venv)
- Node.js 18+ 和 npm(用于 Frontend)
- Docker + Docker Compose v2(命令是 `docker compose`,不是连字符的 `docker-compose`)
- Android SDK Platform-Tools(含 `adb`)
- USB 数据线(Device 连接 Worker)
- 网络:Worker → Backend(开发环境 8000;生产经反向代理时 443)

> **关于 uv:** 本项目 Backend / Worker / Device 三端 Python 依赖统一改用 [uv](https://docs.astral.sh/uv/) 管理(基于 `pyproject.toml` + `uv.lock`)。安装方式:
> ```bash
> # macOS / Linux
> curl -LsSf https://astral.sh/uv/install.sh | sh
>
> # 或通过 pipx / pip
> pipx install uv
> # pip install uv
>
> # Windows (PowerShell)
> # powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
>
> uv --version  # 验证安装
> ```

## 2. Backend 安装

### 2.1 Docker Compose 方式 (推荐)

```bash
cd /data/workspaces/3IS-Auto-App
docker compose -f scripts/docker-compose.yaml up -d
```

**启动服务:**
- `postgres`(容器 `scripts-postgres-1`):PostgreSQL 16,启动时通过 `POSTGRES_DB=3is_auto` 建库,自动运行 `scripts/init_db.sql` 建表
- `redis`(容器 `scripts-redis-1`):Redis 7 Stream 队列
- `backend`(容器 `scripts-backend-1`):FastAPI 应用

**验证服务:**
```bash
curl http://localhost:8000/health
# 预期返回: {"status":"healthy"}

# 或访问 Swagger UI 浏览全部接口
# http://localhost:8000/docs
```

### 2.2 手动 Python 安装 (开发环境,使用 uv)

```bash
# 1) 先用 Docker 起依赖 (postgres + redis)
docker compose -f scripts/docker-compose.yaml up -d postgres redis

# 2) 在仓库根目录使用 uv 同步 backend 依赖
#    (首次运行 uv sync 会自动创建 .venv/ 并根据 backend/pyproject.toml + uv.lock 解析安装)
cd /data/workspaces/3IS-Auto-App
uv sync --project backend

# 3) 在仓库根启动服务
#    (注意:必须在仓库根目录,不是 backend/ 子目录;
#     backend 代码使用绝对导入 `from backend.xxx import ...`)
uv run --project backend uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**说明:**
- `uv sync` 等价于"创建 venv + 安装锁定版本依赖",无需手动 `python -m venv` 与 `pip install`。
- `uv run` 会自动激活 `backend/.venv` 并执行命令,避免忘记 `source .venv/bin/activate`。
- 添加 / 升级依赖:`uv add --project backend <package>` / `uv lock --upgrade --project backend`。
- 如需用传统方式手动激活:`source backend/.venv/bin/activate`。

### 2.3 环境变量配置

仓库提供 `scripts/.env.example` 模板,可基于此复制到 `backend/.env`:

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/3is_auto

# Redis
REDIS_URL=redis://localhost:6379/0

# 存储
STORAGE_LOCAL_PATH=/data/attachments
STORAGE_BACKEND=local

# 安全
JWT_SECRET=your-production-secret-here-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# URL 签名
HMAC_SECRET_KEY=your-hmac-secret-here-change-me

# 超时配置
DOWNLOAD_URL_TTL_SECONDS=300
PENDING_TIMEOUT_SECONDS=600
TRANSACTION_TIMEOUT_SECONDS=1800

# 应用
APP_NAME=3IS-Auto-App
```

### 2.4 Docker Compose 配置文件说明

`scripts/docker-compose.yaml` 实际结构(摘要):

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: 3is_auto
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ../scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/3is_auto
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - attachments_data:/data/attachments

volumes:
  postgres_data:
  attachments_data:
```

> **注:** 文件中不需要顶部的 `version:` 字段;Docker Compose v2 已忽略它,留着会触发 deprecation 警告。

### 2.5 数据库初始化

PostgreSQL 容器启动时:

1. 通过 `POSTGRES_DB=3is_auto` 环境变量创建数据库
2. 自动执行 `/docker-entrypoint-initdb.d/init.sql`(挂载自 `scripts/init_db.sql`),在 `3is_auto` 库内建表

建表清单:
- `workers` — Worker 节点注册
- `devices` — Android 设备管理
- `transactions` — 事务记录
- `attachments` — 附件元数据
- `download_urls` — 下载 URL 管理
- `flows` — RPA 流程定义

注:`init_db.sql` 中不再有 `CREATE DATABASE`(数据库由 entrypoint 处理),只有 `CREATE TABLE` / `CREATE INDEX`。

---

## 3. Frontend 安装

Frontend 是面向运营和管理员的 Web 控制台,基于 React + Vite 构建。

### 3.1 技术栈

- React 19 + TypeScript
- Vite 8(开发服务器 + 构建)
- Ant Design 6(UI 组件库)
- `@ant-design/charts` 2.x(图表)
- axios 1.x(HTTP 客户端)
- react-router-dom 7(路由)

### 3.2 安装依赖

```bash
cd frontend
npm install
# 或 pnpm install
```

### 3.3 启动开发服务器

```bash
cd frontend
npm run dev
# 默认监听 http://localhost:5173
```

### 3.4 Vite 代理配置

`frontend/vite.config.ts` 已配置:

```
/api/*  →  http://localhost:8000
```

前端代码调用 `axios.get('/api/v1/workers')` 会自动转发到 Backend,**无需 CORS 配置**。

**前提条件:** Backend 必须先在 8000 端口启动(见 §2)。

### 3.5 构建生产版本

```bash
cd frontend
npm run build       # 产物输出至 frontend/dist/
npm run preview     # 本地预览生产构建
```

### 3.6 代码检查

```bash
cd frontend
npm run lint        # ESLint 检查
```

### 3.7 Frontend 目录结构

```
frontend/
├── src/
│   ├── api/                        # API 客户端
│   │   ├── client.ts               # axios 实例
│   │   ├── workers.ts              # Worker 接口
│   │   └── transactions.ts         # Transaction 接口
│   ├── components/                 # 共享组件
│   │   ├── AppLayout.tsx
│   │   ├── FileUpload.tsx
│   │   └── StatusBadge.tsx
│   ├── pages/
│   │   ├── admin/
│   │   │   ├── Dashboard.tsx       # 管理员仪表盘
│   │   │   └── WorkerMonitor.tsx   # Worker 监控
│   │   └── staff/
│   │       ├── SubmitApplication.tsx
│   │       ├── TrackApplications.tsx
│   │       └── ApplicationDetail.tsx
│   ├── types/                      # TS 类型定义
│   ├── utils/                      # 工具函数
│   ├── assets/                     # 静态资源
│   ├── App.tsx                     # 路由根组件
│   └── main.tsx                    # 应用入口
├── public/                         # 静态文件(favicon, icons)
├── index.html                      # HTML 模板
├── vite.config.ts                  # Vite 配置(含 /api 代理)
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── eslint.config.js
└── package.json
```

---

## 4. Worker 安装

Worker 是桌面端客户端,负责通过 Airtest 驱动 Android 设备执行 RPA 流程。

### 4.1 Python 环境配置 (使用 uv)

```bash
cd worker

# 同步依赖 (首次运行 uv sync 会自动创建 worker/.venv 并按 pyproject.toml + uv.lock 安装)
uv sync
```

**说明:**
- 无需手动 `python -m venv` 或 `pip install`,`uv sync` 一步完成。
- 如要手动激活虚拟环境:`source .venv/bin/activate`(Windows: `.venv\Scripts\activate`)。
- 推荐使用 `uv run <cmd>` 替代激活 + 执行(详见 §4.5)。

**依赖说明(`worker/pyproject.toml` 当前内容):**
- `airtest==1.4.3` — UI 自动化框架
- `pocoui==1.0.94` — 跨平台控件识别库
- `requests==2.34.2` — HTTP 客户端
- `pyyaml==6.0.3` — 配置文件解析

> **注:** `websocket-client` 被 `pocoui` 上游钉死在 `0.48.0`,由 uv 自动解析拉取,**不要在 pyproject.toml 里显式覆盖版本**,否则会触发依赖冲突。

### 4.2 Android SDK 与 ADB 配置

```bash
# 安装 Android SDK Platform Tools
# 下载地址: https://developer.android.com/studio/releases/platform-tools

# 验证 ADB 安装
adb version
# 预期输出: Android Debug Bridge version 1.0.41

# 在 Android 设备上启用 USB 调试
# 设置 → 开发者选项 → USB 调试 → 开启
```

### 4.3 配置 Worker

仓库提供 `scripts/.env.example` 模板,可基于此复制到 `worker/.env`:

```env
# Backend 连接
BACKEND_URL=http://localhost:8000

# Worker 身份标识 (注册后自动获取)
WORKER_ID=
WORKER_TOKEN=

# 设备绑定 (1:1 绑定)
ADB_SERIAL=<your-device-serial>

# Worker 监听端口 (默认 8765)
WORKER_PORT=8765

# 心跳间隔 (秒)
HEARTBEAT_INTERVAL=30
```

### 4.4 获取设备序列号

```bash
# 连接 Android 设备后执行
adb devices
# 输出示例:
# List of devices attached
# RF8N1234567A    device

# 使用序列号启动 Worker
export ADB_SERIAL=RF8N1234567A
```

### 4.5 启动 Worker

```bash
cd worker
export ADB_SERIAL=<device-serial>
export BACKEND_URL=http://localhost:8000

# 注意:worker/main.py 使用相对导入 (from device_controller import ...),
# 必须在 worker/ 目录内运行,不要用 `python -m worker.main`。
# 使用 uv run,无需手动激活虚拟环境
uv run python main.py
```

**预期输出:**
```
INFO: Worker starting with ADB serial: RF8N1234567A
INFO: Worker registered: WKR-20260608-a1b2c3d4
INFO: Worker started successfully
```

### 4.6 多 Worker 同机配置

同一台电脑可启动多个 Worker 进程 (端口递增):

```bash
# Terminal 1 - Worker 1
cd worker
export ADB_SERIAL=DEVICE1_SERIAL
export WORKER_PORT=8765
uv run python main.py

# Terminal 2 - Worker 2
cd worker
export ADB_SERIAL=DEVICE2_SERIAL
export WORKER_PORT=8766
uv run python main.py

# Terminal 3 - Worker 3
cd worker
export ADB_SERIAL=DEVICE3_SERIAL
export WORKER_PORT=8767
uv run python main.py
```

### 4.7 Worker 目录结构

```
worker/
├── __init__.py
├── main.py              # Worker 入口程序
├── config.py            # 配置管理
├── device_controller.py # ADB 设备控制
├── airtest_executor.py  # Airtest 运行时
├── pyproject.toml       # uv 项目定义 (依赖、Python 版本)
└── uv.lock              # uv 锁文件 (确保跨机器一致版本)
```

> **注:** `.env` 文件由用户根据 4.3 节自行创建,未包含在项目仓库中。

---

## 5. Device 安装

Device 是简化的 Android Agent，负责:
- 通过 Socket 接收 Worker 的下载指令
- 从 Backend 下载影像文件
- 向 Backend 报告状态

### 5.1 APK 安装

Device Agent 由 `android/` 目录的 Android 工程构建产出。APK 路径:

```
android/app/build/outputs/apk/debug/app-debug.apk
```

**方式 1: 一键脚本(推荐)**

```bash
bash android/scripts/adb_install.sh
```

脚本会自动完成四件事(之后需在设备屏幕上手动点一次通知权限弹窗,见下方 ⑤):① `./gradlew :app:assembleDebug` 构建 APK;② `adb install -r app-debug.apk` 安装/覆盖安装;③ `adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow` 授予全盘存储权限;④ `adb reverse tcp:8765 tcp:8765` 把设备的 localhost:8765 反向到桌面 Worker,并 `am start` 拉起 `MainActivity`。

⑤ **Android 13+ 设备:首次启动后,系统会弹出通知权限请求框,请在设备屏幕点「允许」**。该权限授权后,通知栏才会显示 Foreground Service 的 "3IS Device Agent" 常驻通知;若拒绝,可到 `设置 → 应用 → 3IS Device Agent → 通知` 手动开启。

**方式 2: 手工分步执行**

```bash
# 连接 Android 设备
adb devices

# 构建并安装 APK
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 授予存储权限(Android 11+ 必走 AppOps 通道)
adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow

# 反向 Worker 端口(否则设备侧的 localhost:8765 无法触达 Worker)
adb reverse tcp:8765 tcp:8765

# 拉起主界面
adb shell am start -n com.threeis.deviceagent/.MainActivity

# Android 13+ 设备:首次启动后,系统会弹通知权限框,需在设备屏幕点「允许」。
```

### 5.2 配置 Device

Device 端不再使用 `.env` / Python 环境变量。所有 Device 端配置(Worker 主机/端口、Backend URL、设备 ID)通过 **`MainActivity` 界面** 编辑并点击「保存」,写入 `SharedPreferences`(`3is_device_agent`);默认值来自 `BuildConfig`(`android/app/build.gradle.kts` 的 `buildConfigField`),例如:

| 字段 | BuildConfig 默认值 | 含义 |
|------|------------------|------|
| `WORKER_HOST` | `192.168.1.100` | Worker 主机 IP |
| `WORKER_PORT` | `8765` | Worker Socket 端口 |
| `BACKEND_URL` | `http://192.168.1.100:8000` | Backend REST 地址 |
| `DEVICE_ID` | 启动时随机生成(`device-xxxx-NNNN`) | 设备唯一标识 |

如需修改默认值(例如指向生产环境),编辑 `android/app/build.gradle.kts` 的 `defaultConfig.buildConfigField` 后重新 `./gradlew :app:assembleDebug`。

### 5.3 启动 Device Agent

**方式 1: 通过 ADB 启动(由 `adb_install.sh` 自动完成)**
```bash
adb shell am start -n com.threeis.deviceagent/.MainActivity
```

**方式 2: 通过设备屏幕点击启动**
- 找到「3IS Device Agent」图标
- 点击启动应用,首次启动会提示授予 `MANAGE_EXTERNAL_STORAGE`

**方式 3: 设备端命令行**
```bash
# 在设备上执行
am start -n com.threeis.deviceagent/.MainActivity
```

### 5.4 验证 Device 在线

```bash
# 检查 Backend 注册的 Worker 列表(返回结构里包含每个 Worker 绑定的设备信息)
curl http://localhost:8000/api/v1/workers

# 预期: 返回 worker 列表,每项含 bound_device_id 等字段
# 注:当前后端没有单独的 /api/v1/devices 端点;设备信息嵌在 worker 返回中。
```

### 5.5 Device Socket 连接说明

Device 与 Worker 之间是 **TCP Socket 双向通信**,链路为 `adb reverse` 反向通道:

```
┌──────────────────────────┐                  ┌────────────────────────┐
│  Worker (Desktop) :8765  │                  │  Device (Android)      │
│                          │  ──DOWNLOAD_FILES (JSON)──►              │
│                          │ ◄──DOWNLOAD_COMPLETE (JSON)──            │
│                          │                  │  127.0.0.1:8765        │
└──────────────────────────┘                  └────────────────────────┘
              ▲                                          ▲
              └────────── adb reverse 反向通道 ──────────┘

提示:Device 的 SocketClient 实际连 `127.0.0.1:8765`,通过 `adb reverse` 抵达 Worker。
```

- **Worker → Device**:任务到达时推 `DOWNLOAD_FILES` 指令(每行一条 JSON,以 `\n` 结束)
- **Device → Worker**:下载完成 + 上报 Backend `download-ack` 之后,Device 回送 `DOWNLOAD_COMPLETE` 事件(同样以 `\n` 结束)
- Worker 在 `worker/device_dispatcher.py:send_and_await_ack` 处阻塞等 ack,默认 120 秒(`worker/config.py:DISPATCH_TIMEOUT`)
- **超时分支**:Socket 在 timeout 内未收到 `DOWNLOAD_COMPLETE`,Worker 记 `No ack from device for txn ...` 并 `return False`(post-MVP 计划:回写 Backend 标 `FAILED`,详见 `worker/main.py` 旁注 TODO)
- **失败 ack 分支**:Device 收到指令并下载,但部分文件 MD5 / 网络错误等导致 `all_success=false`(或 `sandbox_clear_failed=true`),Backend 在 `download-ack` 端点把 `Transaction.status` 标为 `RETRY_REQUIRED`(`backend/api/v1/devices.py:68`)

> **排错提示:** 若 mock worker 看到 `No ack from device`,先确认 `adb reverse tcp:8765 tcp:8765` 是否仍有效(USB 断开重连后会失效),再确认 Device 的 `MainActivity` 是否在运行。

**前提条件:**
- Device 与 Worker 通过 USB 物理连接(adb 已建立)
- `adb reverse tcp:8765 tcp:8765` 已执行(由 `android/scripts/adb_install.sh` 自动维护,USB 重连后需重做)
- Worker 已启动并监听 8765 端口(见 §4.5)
- Device 端 `WORKER_HOST` (默认 `192.168.1.100`)与 `WORKER_PORT` (默认 `8765`) 已在 `MainActivity` 配置好;**实际 Socket 连的是设备自身的 `127.0.0.1:8765`**,`WORKER_HOST` 仅用于 Worker 侧的握手与日志标注

### 5.5.1 停止 Device Agent

在 `MainActivity` 点「停止」按钮:

1. 按钮发送 `ACTION_STOP` intent 给 `DeviceAgentService`
2. `Service.onStartCommand` 收到 action,调用 `stopSelf()` 触发 `onDestroy`
3. `Service.onDestroy` 依次:
   - `socket?.stop()` 关闭 Socket 客户端
   - `scope.cancel()` 取消所有协程
   - `stopForeground(STOP_FOREGROUND_REMOVE)` 移除通知栏的常驻通知
4. 通知栏 "3IS Device Agent" 通知消失

**重新启动:** 在设备桌面点应用图标,或执行 `am start -n com.threeis.deviceagent/.MainActivity`。`Application.onCreate` 会自动拉起新的 `Service`。

### 5.6 Device 目录结构与设备端沙箱

**Android 工程目录(`android/`):**

```
android/
├── app/
│   ├── build.gradle.kts        # 含 BuildConfig 默认值 (WORKER_HOST/PORT/BACKEND_URL)
│   ├── proguard-rules.pro
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml   # 申请 INTERNET / FOREGROUND_SERVICE / MANAGE_EXTERNAL_STORAGE
│           ├── java/com/threeis/deviceagent/
│           │   ├── MainActivity.kt           # 配置 UI (Worker host/port/Backend URL/Device ID)
│           │   ├── DeviceAgentApplication.kt
│           │   ├── data/
│           │   │   ├── Config.kt             # SharedPreferences + BuildConfig 读取
│           │   │   └── Models.kt             # 协议模型 (含 attachment_id / ext)
│           │   ├── download/
│           │   │   ├── SandboxManager.kt     # 沙箱根目录 /sdcard/3is/
│           │   │   └── Downloader.kt         # 直连 OSS 签名 URL
│           │   ├── net/
│           │   │   ├── SocketClient.kt       # 与 Worker 的 TCP 8765 通信
│           │   │   └── BackendApi.kt         # ready / status / download-ack
│           │   └── service/
│           │       └── DeviceAgentService.kt # Foreground Service,状态机 (INITIALIZING/READY/...)
│           └── res/                          # UI 布局 / strings / themes
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
└── scripts/
    ├── adb_install.sh     # 一键:build + install + MANAGE_EXTERNAL_STORAGE + adb reverse + 启动
    └── mock_worker.py     # 桌面端 Python mock,用于在无 Worker 机器上联调 Device Agent
```

**设备端沙箱(Android 设备 `/sdcard/3is/`):**

- 根目录:`/sdcard/3is/`(Device 内部约定,**不再**使用事务级 `/sdcard/sandbox/{txn_id}/`)
- 文件命名规则:`<attachment_id>.<ext>`,例如 `att_a1b2c3d4.jpg` / `att_e5f6g7h8.pdf`
- `attachment_id` 由 Backend 在 `POST /api/v1/transactions` 响应中下发,通过 `DOWNLOAD_FILES` 指令传给 Device
- `ext` 取 `jpg|png|pdf` 三者之一(在 `download_urls[]` 元素中显式携带,见 §7.6 协议)
- 写入路径:由 `SandboxManager.pathFor(attachmentId, ext)` 拼装,先写 `<attachment_id>.<ext>.part` 再原子 rename
- 事务终态后由 Worker 触发 `adb shell rm -rf /sdcard/3is/` 清理(`download-ack` 上报完成后)

> **关于跨 APP 可读:** `/sdcard/3is/` 位于外部存储共享区,默认对其它 APP 可见,这是**本工具明确选择的例外**(目标保险 APP 需直接读取该目录下的影像文件),**不是**通用沙箱策略。其他模块应继续使用 APP 私有目录(`context.filesDir`)做隔离。

---

## 6. 配置指南

### 6.1 Backend 环境变量详解

| 变量名 | 默认值 | 必填 | 说明 |
|--------|--------|------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | 是 | PostgreSQL 连接字符串 |
| `REDIS_URL` | `redis://localhost:6379/0` | 是 | Redis 连接字符串 |
| `STORAGE_LOCAL_PATH` | `/data/attachments` | 是 | 本地存储路径 |
| `STORAGE_BACKEND` | `local` | 是 | 存储后端类型 (local/oss/minio) |
| `JWT_SECRET` | - | 是 | JWT 签名密钥 (生产环境必改) |
| `JWT_ALGORITHM` | `HS256` | 否 | JWT 算法 |
| `JWT_EXPIRE_HOURS` | `24` | 否 | Token 过期时间 (小时) |
| `HMAC_SECRET_KEY` | - | 是 | URL 签名密钥 (生产环境必改) |
| `DOWNLOAD_URL_TTL_SECONDS` | `300` | 否 | 下载 URL 有效期 (5分钟) |
| `PENDING_TIMEOUT_SECONDS` | `600` | 否 | PENDING 超时 (10分钟) |
| `TRANSACTION_TIMEOUT_SECONDS` | `1800` | 否 | 事务超时 (30分钟) |
| `APP_NAME` | `3IS-Auto-App` | 否 | 应用名称 |

### 6.2 Worker 环境变量详解

| 变量名 | 默认值 | 必填 | 说明 |
|--------|--------|------|------|
| `BACKEND_URL` | `http://localhost:8000` | 是 | Backend 服务地址 |
| `WORKER_ID` | - | 否 | Worker ID (自动注册后获取) |
| `WORKER_TOKEN` | - | 否 | Worker 认证 Token (自动获取) |
| `ADB_SERIAL` | - | 是 | 绑定的 Android 设备序列号 |
| `WORKER_PORT` | `8765` | 否 | Socket 监听端口 |
| `HEARTBEAT_INTERVAL` | `30` | 否 | 心跳间隔 (秒) |

### 6.3 Device 端配置(取代原 Python `DEVICE_*` 环境变量)

Device 端不再使用 `WORKER_HOST` / `WORKER_PORT` / `BACKEND_URL` / `DEVICE_ID` 等 Python 环境变量;改由 Android `MainActivity` 写入 `SharedPreferences`,默认值来自 `BuildConfig`。

| 字段 | BuildConfig 默认值 | 含义 | 运行时修改方式 |
|------|------------------|------|---------------|
| `WORKER_HOST` | `192.168.1.100` | Worker 主机 IP | `MainActivity` 编辑 + 保存;或改 `app/build.gradle.kts` 后重新构建 |
| `WORKER_PORT` | `8765` | Worker Socket 端口 | 同上 |
| `BACKEND_URL` | `http://192.168.1.100:8000` | Backend REST 地址 | 同上 |
| `DEVICE_ID` | 启动时随机生成(`device-xxxx-NNNN`) | 设备唯一标识 | `MainActivity` 可手动覆写 |

> 历史兼容:如发现遗留的 `device/.env` 文件(`WORKER_HOST` / `WORKER_PORT` / `BACKEND_URL` / `DEVICE_ID`)可安全删除,新版 Android Agent 不再读取。

### 6.4 生产环境安全配置

**重要: 生产环境必须修改以下密钥**

```bash
# Backend 生产环境
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export HMAC_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Worker 生产环境
export WORKER_TOKEN=<get-from-backend-registration>
```

### 6.5 网络拓扑配置

**USB 反向网络 (默认)**

Device 通过 USB ADB 反向网络访问 Backend:

```
Device → USB → Worker → Backend
```

**Device → Worker 链路(关键,常被忽略)**

Device Agent APP 通过 `adb reverse tcp:8765 tcp:8765` 把设备自身的 `localhost:8765` 反向到桌面的 Worker:

```
Device (Android)  ──adb reverse──►  Worker (Desktop) :8765
       SocketClient 连 127.0.0.1:8765 即等于连 Worker
```

> **`adb reverse` 必须每次设备重连 USB 后重做一次**。`android/scripts/adb_install.sh` 会在 install 时自动执行;若手动 install,务必自行补 `adb reverse tcp:8765 tcp:8765`。可用 `adb reverse --list` 验证当前反向映射。

**站点 VPN (备选)**

如 USB 反向网络不可用,切换站点 VPN:

```
Device → VPN → Backend
```

---

## 7. 快速启动

### 7.1 启动顺序

```
1. Backend (Docker Compose)
2. Frontend (Vite 开发服务器)
3. Worker (Desktop)
4. Device (Android)
5. 提交测试事务
```

### 7.2 Step 1: 启动 Backend

```bash
# 启动所有服务
docker compose -f scripts/docker-compose.yaml up -d

# 验证服务
curl http://localhost:8000/health
# {"status":"healthy"}

# 查看日志(三个容器:scripts-backend-1, scripts-postgres-1, scripts-redis-1)
docker logs -f scripts-backend-1
```

### 7.3 Step 2: 启动 Frontend

```bash
cd frontend
npm install      # 首次运行
npm run dev
# 浏览器访问 http://localhost:5173
# Vite 已配置 /api → http://localhost:8000 代理,无需 CORS
```

### 7.4 Step 3: 启动 Worker

```bash
# Terminal
cd worker

export ADB_SERIAL=RF8N1234567A
export BACKEND_URL=http://localhost:8000

uv run python main.py
```

### 7.5 Step 4: 启动 Device

Device Agent 在第 5.1 节执行 `bash android/scripts/adb_install.sh` 时已经被 `am start` 拉起。若需手动重启:

```bash
adb shell am start -n com.threeis.deviceagent/.MainActivity
```

启动后 `MainActivity` 会显示 4 个配置输入框(Worker host/port/Backend URL/Device ID),按需修改后点击「保存」即可。`Foreground Service` 由 `Application.onCreate` 自动拉起(应用并无独立的「启动」按钮),通知栏出现 "3IS Device Agent" 常驻通知即表示已就绪。

### 7.6 Step 5: 提交测试事务

接口为 **multipart/form-data**:`transaction` 字段是 JSON 字符串,`files` 是多个文件上传(顺序对应 `attachments_meta`)。

```bash
# 单笔新保提交(完整字段定义见 http://localhost:8000/docs)
curl -X POST http://localhost:8000/api/v1/transactions \
  -F 'transaction={
    "business_type": "NEW",
    "customer_phone": "13812345678",
    "attachments_meta": [
      {"file_type": "ID_CARD", "file_format": "JPG"},
      {"file_type": "DRIVING_LICENSE", "file_format": "JPG"}
    ]
  };type=application/json' \
  -F 'files=@id_card.jpg' \
  -F 'files=@driving_license.jpg'

# 响应示例:
# {
#   "transaction_id": "TXN-20260608-abc12345",
#   "status": "PENDING",
#   "submitted_at": "2026-06-08T10:00:00Z",
#   "attachments": [...]
# }
```

### 7.7 监控状态

```bash
# 查看事务状态
curl http://localhost:8000/api/v1/transactions/<transaction_id>

# 查看 Worker 列表(返回结构里包含每个 Worker 绑定的设备信息)
curl http://localhost:8000/api/v1/workers

# 申请下载 URL
curl -X POST http://localhost:8000/api/v1/transactions/<transaction_id>/download-urls
```

---

## 8. 故障排查

### 8.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: airtest` | 依赖未安装 | `cd worker && uv sync` |
| `ADB connection failed` | USB 调试未开启 | 在 Android 设置中启用 USB 调试 |
| `Worker registration failed` | Backend 不可达 | 检查 `BACKEND_URL` 和防火墙 |
| `Device socket connection refused` | 端口不匹配 | 确认 Worker 和 Device 的 `WORKER_PORT` 一致 |
| `401 Unauthorized` on downloads | Token 过期或缺失 | 重启 Worker 重新注册 |
| `curl: (7) Failed to connect` | Backend 未启动 | `docker compose -f scripts/docker-compose.yaml up -d` |
| `psql: connection refused` | PostgreSQL 未启动 | `docker compose -f scripts/docker-compose.yaml ps` 检查容器状态 |
| `docker-compose: command not found` | 系统只有 Compose v2 | 使用 `docker compose`(无连字符) |
| `failed to solve: python:3.x-slim` | Docker 镜像源 403 | 见 README 关于镜像源的说明,或换 `docker.m.daocloud.io` 镜像 |
| `uv: command not found` | uv 未安装 | 见 §1.3,执行 `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `uv sync` 解析失败 | `uv.lock` 与 `pyproject.toml` 不一致 | 重新生成锁文件:`uv lock` 后再 `uv sync` |
| Device Service 通知卡在 `INITIALIZING`(设备无 `READY` 上报) | 设备的 localhost:8765 反向不通 / Worker 未监听 | ① `adb reverse --list` 确认有 `tcp:8765 tcp:8765`;无则 `adb reverse tcp:8765 tcp:8765` 补做。② 确认 Worker 进程在跑且监听 8765(在 Worker 主机 `ss -tlnp \| grep 8765` 验证)。③ 检查 `MANAGE_EXTERNAL_STORAGE` 是否已授权:`adb shell appops get --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE` |

### 8.2 网络检查清单

- [ ] Worker 可访问 `BACKEND_URL:8000`(生产经反代到 443)
- [ ] Worker 与 Device 在同一局域网(Socket 通信)
- [ ] Device 可通过 USB 反向网络访问 Backend
- [ ] Frontend(`http://localhost:5173`)能通过 `/api` 代理调到 Backend

### 8.3 日志位置

| 组件 | 日志位置 |
|------|----------|
| Backend | `docker logs -f scripts-backend-1` |
| PostgreSQL | `docker logs -f scripts-postgres-1` |
| Redis | `docker logs -f scripts-redis-1` |
| Frontend (dev) | Vite 输出到启动它的终端(stdout) |
| Worker | 标准输出(终端) |
| Device | Android Logcat:`adb logcat` |

### 8.4 网络诊断命令

```bash
# 检查 Backend 健康
curl -v http://localhost:8000/health

# 检查 ADB 设备连接
adb devices

# 检查端口占用
ss -tlnp | grep -E ':8000|:5173|:8765'
# 或
netstat -an | grep -E '8000|5173|8765'

# 检查所有 Docker 容器状态
docker compose -f scripts/docker-compose.yaml ps
docker ps
docker logs scripts-backend-1
```

---

## 9. 文件结构参考

```
3is-auto-app/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口 (含 /health 和启动建表逻辑)
│   ├── config.py            # 配置管理
│   ├── Dockerfile
│   ├── pyproject.toml       # uv 项目定义 (依赖、Python 版本)
│   ├── uv.lock              # uv 锁文件
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py        # 聚合所有 v1 路由
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── transactions.py  # 事务接口 (multipart 上传)
│   │       ├── workers.py       # Worker 注册/心跳/列表(含绑定设备)
│   │       ├── downloads.py     # 下载 URL 签发
│   │       └── statistics.py    # 统计接口
│   ├── db/                  # 数据库会话/引擎
│   ├── models/              # SQLAlchemy 模型
│   │   ├── attachment.py
│   │   ├── device.py
│   │   ├── download_url.py
│   │   ├── flow.py
│   │   ├── transaction.py
│   │   └── worker.py
│   ├── schemas/             # Pydantic 请求/响应 schema
│   ├── services/            # 业务逻辑
│   │   ├── transaction_service.py
│   │   ├── dispatcher_service.py
│   │   ├── dashboard_service.py
│   │   └── url_signature_service.py
│   └── storage/             # 存储后端
│       ├── base.py          # 存储抽象接口
│       └── local.py         # 本地存储实现
│
├── frontend/
│   ├── src/
│   │   ├── api/             # axios 客户端 (client/workers/transactions)
│   │   ├── components/      # AppLayout / FileUpload / StatusBadge
│   │   ├── pages/
│   │   │   ├── admin/       # Dashboard / WorkerMonitor
│   │   │   └── staff/       # SubmitApplication / TrackApplications / ApplicationDetail
│   │   ├── types/
│   │   ├── utils/
│   │   ├── assets/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/              # favicon, icons
│   ├── index.html
│   ├── vite.config.ts       # 含 /api → :8000 代理
│   ├── tsconfig*.json
│   ├── eslint.config.js
│   └── package.json
│
├── worker/
│   ├── __init__.py
│   ├── main.py              # Worker 入口 (相对导入,需在 worker/ 内运行)
│   ├── config.py
│   ├── device_controller.py # ADB 设备控制
│   ├── airtest_executor.py  # Airtest 执行器
│   ├── pyproject.toml       # uv 项目定义
│   └── uv.lock              # uv 锁文件
│
├── android/                 # Android Device Agent 工程
│   ├── app/
│   │   ├── build.gradle.kts        # BuildConfig 默认值
│   │   └── src/main/
│   │       ├── AndroidManifest.xml # 含 MANAGE_EXTERNAL_STORAGE 申请
│   │       ├── java/com/threeis/deviceagent/
│   │       │   ├── MainActivity.kt
│   │       │   ├── data/         # Config (SharedPreferences) / Models
│   │       │   ├── download/     # SandboxManager / Downloader
│   │       │   ├── net/          # SocketClient / BackendApi
│   │       │   └── service/      # DeviceAgentService (Foreground)
│   │       └── res/
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   └── scripts/
│       ├── adb_install.sh        # build + install + 授权 + adb reverse
│       └── mock_worker.py        # 桌面 Python mock Worker,联调用
│
├── scripts/
│   ├── docker-compose.yaml  # Docker 编排
│   ├── init_db.sql          # 数据库建表 (entrypoint 自动运行)
│   ├── test_integration.py  # 集成测试
│   └── .env.example         # 环境变量模板 (供 backend/worker 复制;Device 端不再使用 .env)
│
├── tests/
│   ├── conftest.py
│   └── backend/
│       ├── test_transactions.py
│       ├── test_transactions_list.py
│       ├── test_workers.py
│       ├── test_workers_list.py
│       └── test_statistics.py
│
├── docs/
│   ├── user-manu.md         # 本文档
│   └── superpowers/         # 设计/规划/规格 (specs/plans)
│
├── openspec/                # OpenSpec 规格存放
├── .opencode/               # OpenSpec 技能定义 (opencode/copilot)
├── .superpowers/            # superpowers 框架配置
│
├── conftest.py              # pytest 根配置
├── pytest.ini
└── README.md
```

## 10. 下一步

### 10.1 生产环境配置

- [ ] 配置生产环境 JWT_SECRET 和 HMAC_SECRET_KEY
- [ ] 配置 SSL/TLS 证书
- [ ] 设置监控 (Prometheus/Grafana)
- [ ] 配置日志收集 (Loki/ELK)

### 10.2 运行测试

```bash
# 集成测试 (使用 uv run,自动使用 backend 虚拟环境)
uv run --project backend python scripts/test_integration.py

# 预期输出:
# ==================================================
# 3IS-Auto-App MVP Integration Test
# ==================================================
#
# --- Testing: Backend Health ---
# ✓ Backend health check passed
#
# --- Testing: Worker Registration ---
# ✓ Worker registered: WKR-20260608-xxxxxxx
#
# --- Testing: Transaction Creation ---
# ✓ Transaction created: TXN-20260608-xxxxxxx
#
# ==================================================
# Summary:
#   Backend Health: PASS
#   Worker Registration: PASS
#   Transaction Creation: PASS
# ==================================================
```

### 10.3 相关文档

- [PRD 设计文档](./superpowers/specs/2026-06-05-prd-design.md) - 产品需求说明书
- [架构设计](./superpowers/specs/) - 详细架构文档

### 10.4 端到端测试(mock_worker)

在没有真实 Backend 业务事务的情况下,可以使用 `android/scripts/mock_worker.py` 验证 Device Agent 的下载/校验/回送 ack 链路。

#### 适用场景

- 调试 Device Agent 而不想拉起整个 Backend/Worker 链路
- 验证下载后文件落在 `/sdcard/3is/` 的正确位置
- 验证 MD5 校验失败、URL 404 等错误路径

#### 步骤

1. **准备一个测试文件**(本机或局域网可达即可):
   ```bash
   printf 'hello-3is' > /tmp/sample.jpg
   python3 -m http.server 9000 --directory /tmp &
   # 在另一台机器访问,IP 替换为 http server 所在机器
   ```

2. **计算 MD5**:
   ```bash
   MD5=$(md5sum /tmp/sample.jpg | awk '{print $1}')
   echo "MD5=$MD5"
   ```

3. **运行 mock worker**(监听 :8765,接受一个 Device 连接,推一条 `DOWNLOAD_FILES`,等 Device 回 ack):
   ```bash
   python3 android/scripts/mock_worker.py "http://<host>:9000/sample.jpg" "$MD5"
   ```
   mock worker 会在 stdout 打印:
   ```
   Mock worker listening on :8765
   device connected: ('127.0.0.1', <port>)
   ack: {"event": "DOWNLOAD_COMPLETE", "transaction_id": "TXN-MOCK-0001", "all_success": true, "files": [...]}
   ```

4. **设备端验证**(在连接的 Android 设备 / 模拟器):
   ```bash
   adb shell ls -la /sdcard/3is/
   # 预期: att_mock0001.jpg,大小 9 字节("hello-3is")
   ```

#### 错误路径注入

- **MD5 不匹配**:把 mock_worker 的第二个参数改成错误的 MD5(任意 32 位 hex),Device 会返回 `success=false, error_reason=MD5_MISMATCH`,**不会**回写文件
- **URL 404**:把 URL 改成不存在的路径,Device 返回 `error_reason=NETWORK_ERROR`(403/410 则是 `URL_EXPIRED`)
- **Sandbox clear 失败**:在 mock_worker 跑前,先 `adb push foo.bin /sdcard/3is/` 塞一个 Device Agent 创建不了的文件,触发 `clear()` 抛 SecurityException,Device **仍继续覆盖式下载**(不会终止 Service)并在 `download-ack` HTTP body 中带 `sandbox_clear_failed=true`

---

## Changelog

**V1.3 (2026-06-15)**
- §5.1 APK 安装改用 `android/scripts/adb_install.sh` 一键脚本(自动 build + install + MANAGE_EXTERNAL_STORAGE 授权 + `adb reverse` + 拉起 MainActivity);包名从占位 `com.example.deviceagent` 更新为真实 `com.threeis.deviceagent`
- §5.2 配置 Device:删除 Python `device/.env` 工作流,改为 MainActivity 写入 SharedPreferences,默认值取自 BuildConfig
- §5.3 启动 Device Agent:更新启动命令中的包名
- §5.6 Device 目录结构:替换 Python `device/` 树为 Android `android/` 工程树;新增设备端沙箱 `/sdcard/3is/<attachment_id>.<ext>` 命名规则说明
- §6.3 Device 端配置:表格替换为 SharedPreferences + BuildConfig 字段
- §6.5 网络拓扑配置:新增「Device → Worker 链路」小节,说明 `adb reverse tcp:8765 tcp:8765` 由 `adb_install.sh` 自动维护
- §7.5 Step 4:补充 MainActivity 4 个配置输入框与 Foreground Service 通知的就绪判据
- §8.1 故障排查表:新增「Device Service 卡在 `INITIALIZING`」条目,关联 `adb reverse` 校验命令
- §9 文件结构:删除 Python `device/` 子树,新增 `android/` 子树(含 `scripts/adb_install.sh` 与 `mock_worker.py`)

**V1.2 (2026-06-11)**
- Python 依赖管理全面迁移至 [uv](https://docs.astral.sh/uv/) 框架(基于 `pyproject.toml` + `uv.lock`)
- §1.3 前置条件新增 uv 安装说明
- §2.2 Backend 手动安装改用 `uv sync --project backend` + `uv run uvicorn ...`
- §4.1 Worker 安装改用 `uv sync`,删除原 `python -m venv` + `pip install` 流程
- §4.5 / §4.6 / §7.4 Worker 启动命令统一为 `uv run python main.py`
- §5.1 增加 Device 端 Python 辅助脚本的 uv 用法说明
- §4.7 / §5.6 / §9 文件结构由 `requirements.txt` 替换为 `pyproject.toml` + `uv.lock`
- §8.1 故障排查表新增 uv 相关条目(`uv: command not found` / `uv sync` 解析失败)
- §10.2 集成测试命令改为 `uv run --project backend python scripts/test_integration.py`

**V1.1 (2026-06-11)**
- 新增 §3 Frontend 安装章节(React 19 + Vite 8 + Ant Design 6)
- 全文 `docker-compose`(v1) 替换为 `docker compose`(v2)
- 修正 §7.6 提交事务接口为 multipart/form-data(原 application/json 示例错误)
- 删除/替换不存在的 `/api/v1/devices` 端点(改为 `/api/v1/workers`,内含设备信息)
- §4 Worker 依赖说明同步到当前 requirements.txt 版本(airtest 1.4.3 / pocoui 1.0.94 / requests 2.34.2 / pyyaml 6.0.3)
- §2.5 数据库初始化说明更新:`POSTGRES_DB` 创建库,`init_db.sql` 仅建表
- §2.4 Compose 示例 `context` 路径修正(`./backend` → `../backend`,因 compose 文件位于 `scripts/`),补全 `environment:` 块
- §9 文件结构补全 frontend/、backend/db/、backend/schemas/、router.py、statistics.py、dashboard_service.py、tests/backend/* 等
- §1.3 前置条件增加 Node.js 18+;说明 Docker Compose v2
- §8 故障排查表/日志位置/诊断命令统一用真实容器名 `scripts-{backend,postgres,redis}-1`
- §4.5/§7.4 Worker 启动命令改为在 `worker/` 目录内 `python main.py`(避免相对导入失败)

**V1.0 (2026-06-08)** - 初版

---

**文档结束**
