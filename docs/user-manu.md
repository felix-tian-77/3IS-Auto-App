# 3IS-Auto-App 用户操作手册

**版本:** V1.0 (MVP)
**更新日期:** 2026-06-08
**适用范围:** Backend / Worker / Device 三端安装与操作

---

## 目录

1. [系统架构](#1-系统架构)
2. [Backend 安装](#2-backend-安装)
3. [Worker 安装](#3-worker-安装)
4. [Device 安装](#4-device-安装)
5. [配置指南](#5-配置指南)
6. [快速启动](#6-快速启动)
7. [故障排查](#7-故障排查)
8. [文件结构参考](#8-文件结构参考)
9. [下一步](#9-下一步)

---

## 1. 系统架构
### 1.1 组件拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PostgreSQL  │  │   Redis     │  │  FastAPI    │        │
│  │   (RDS)     │  │  (Stream)   │  │   :8000     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            │
              HTTPS / WSS (443)
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────┐
│      Worker #1      │         │      Worker #N      │
│    (Desktop PC)     │         │    (Desktop PC)     │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │    Airtest    │  │         │  │    Airtest    │  │
│  │    Runtime    │  │         │  │    Runtime    │  │
│  └───────────────┘  │         │  └───────────────┘  │
│  ┌───────────────┐  │         │  ┌───────────────┐  │
│  │ Socket Client │  │         │  │ Socket Client │  │
│  └───────────────┘  │         │  └───────────────┘  │
└──────────┬──────────┘         └──────────┬──────────┘
           │ USB ADB (:5555)                   │ USB ADB
           ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────┐
│      Device #1      │         │      Device #N      │
│     (Android)       │         │     (Android)      │
└─────────────────────┘         └─────────────────────┘
```

### 1.2 端口映射

| 组件 | 端口 | 协议 | 用途 |
|------|------|------|------|
| Backend API | 8000 | HTTPS | REST API + WebSocket |
| PostgreSQL | 5432 | TCP | 数据库 |
| Redis | 6379 | TCP | Stream 队列 |
| Worker Socket | 8765/8766/8767 | TCP | Worker ↔ Device 局域网通信 |
| ADB | 5555 | USB | Worker ↔ Device USB 连接 |

### 1.3 前置条件

- Python 3.14+
- Docker + Docker Compose
- Android SDK (含 ADB)
- USB 数据线 (Device 连接 Worker)
- 网络: Worker → Backend 出方向 443

## 2. Backend 安装

### 2.1 Docker Compose 方式 (推荐)

```bash
cd /data/workspaces/3IS-Auto-App
docker-compose -f scripts/docker-compose.yaml up -d
```

**启动服务:**
- `postgres`: PostgreSQL 16 + init_db.sql 初始化
- `redis`: Redis 7 Stream 队列
- `backend`: FastAPI 应用

**验证服务:**
```bash
curl http://localhost:8000/health
# 预期返回: {"status":"healthy"}
```

### 2.2 手动 Python 安装 (开发环境)

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2.3 环境变量配置

创建 `backend/.env` 文件:

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

`services/docker-compose.yaml` 结构:

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - attachments_data:/data/attachments
```

### 2.5 数据库初始化

PostgreSQL 启动时自动执行 `scripts/init_db.sql`:
- `workers` 表 - Worker 节点注册
- `devices` 表 - Android 设备管理
- `transactions` 表 - 事务记录
- `attachments` 表 - 附件元数据
- `download_urls` 表 - 下载 URL 管理
- `flows` 表 - RPA 流程定义

---

## 3. Worker 安装

Worker 是桌面端客户端，负责通过 Airtest 驱动 Android 设备执行 RPA 流程。

### 3.1 Python 环境配置

```bash
cd worker

# 创建虚拟环境 (推荐使用 UV)
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate

# 或使用 UV (更快的包管理)
# pip install uv
# uv venv
# source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

**依赖说明:**
- `airtest==1.2.16` - UI 自动化框架
- `pocoui==1.0.35` - 跨平台控件识别库
- `requests==2.32.3` - HTTP 客户端
- `pyyaml==6.0.2` - 配置文件解析
- `websocket-client==1.8.0` - WebSocket 通信

### 3.2 Android SDK 与 ADB 配置

```bash
# 安装 Android SDK Platform Tools
# 下载地址: https://developer.android.com/studio/releases/platform-tools

# 验证 ADB 安装
adb version
# 预期输出: Android Debug Bridge version 1.0.41

# 在 Android 设备上启用 USB 调试
# 设置 → 开发者选项 → USB 调试 → 开启
```

### 3.3 配置 Worker

创建 `worker/.env` 文件:

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

### 3.4 获取设备序列号

```bash
# 连接 Android 设备后执行
adb devices
# 输出示例:
# List of devices attached
# RF8N1234567A    device

# 使用序列号启动 Worker
export ADB_SERIAL=RF8N1234567A
```

### 3.5 启动 Worker

```bash
source .venv/bin/activate
export ADB_SERIAL=<device-serial>
export BACKEND_URL=http://localhost:8000
python worker/main.py
```

**预期输出:**
```
INFO: Worker starting with ADB serial: RF8N1234567A
INFO: Worker registered: WKR-20260608-a1b2c3d4
INFO: Worker started successfully
```

### 3.6 多 Worker 同机配置

同一台电脑可启动多个 Worker 进程 (端口递增):

```bash
# Terminal 1 - Worker 1
export ADB_SERIAL=DEVICE1_SERIAL
export WORKER_PORT=8765
python worker/main.py

# Terminal 2 - Worker 2
export ADB_SERIAL=DEVICE2_SERIAL
export WORKER_PORT=8766
python worker/main.py

# Terminal 3 - Worker 3
export ADB_SERIAL=DEVICE3_SERIAL
export WORKER_PORT=8767
python worker/main.py
```

### 3.7 Worker 目录结构

```
worker/
├── __init__.py
├── main.py              # Worker 入口程序
├── config.py            # 配置管理
├── device_controller.py # ADB 设备控制
├── airtest_executor.py  # Airtest 运行时
└── requirements.txt    # Python 依赖
```

> **注**：`.env` 文件由用户根据 3.3 节自行创建，未包含在项目仓库中。

---

## 4. Device 安装

Device 是简化的 Android Agent，负责:
- 通过 Socket 接收 Worker 的下载指令
- 从 Backend 下载影像文件
- 向 Backend 报告状态

### 4.1 APK 安装

Device Agent APK 文件位于项目根目录或由开发团队提供。

```bash
# 连接 Android 设备
adb devices

# 安装 APK
adb install device-app.apk

# 或推送 APK 到设备后手动安装
adb push device-app.apk /sdcard/
```

### 4.2 配置 Device

创建设备配置文件 `device/.env`:

```env
# Worker 连接 (局域网)
WORKER_HOST=192.168.1.100
WORKER_PORT=8765

# Backend 连接
BACKEND_URL=http://localhost:8000

# 设备标识
DEVICE_ID=device-001
```

### 4.3 启动 Device Agent

**方式 1: 通过 ADB 启动**
```bash
adb shell am start -n com.example.deviceagent/.MainActivity
```

**方式 2: 通过设备屏幕点击启动**
- 找到 Device Agent 图标
- 点击启动应用

**方式 3: 设备端命令行**
```bash
# 在设备上执行
am start -n com.example.deviceagent/.MainActivity
```

### 4.4 验证 Device 在线

```bash
# 检查 Backend 注册的设备列表
curl http://localhost:8000/api/v1/devices

# 预期: 返回设备状态列表
```

### 4.5 Device Socket 连接说明

Device 通过局域网 Socket 连接到 Worker:

```
Device (Android)  ──── Socket :8765 ────  Worker (Desktop)
```

**前提条件:**
- Device 与 Worker 在同一局域网
- Worker 已启动并监听端口
- `WORKER_HOST` 配置为 Worker 的 IP 地址

### 4.6 Device 目录结构

```
device/
├── __init__.py
├── main.py              # Device 入口程序
├── downloader.py        # 文件下载模块
├── socket_client.py     # Socket 客户端
├── requirements.txt      # Python 依赖
└── .env                 # 环境变量 (本地创建)
```

---

## 5. 配置指南

### 5.1 Backend 环境变量详解

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

### 5.2 Worker 环境变量详解

| 变量名 | 默认值 | 必填 | 说明 |
|--------|--------|------|------|
| `BACKEND_URL` | `http://localhost:8000` | 是 | Backend 服务地址 |
| `WORKER_ID` | - | 否 | Worker ID (自动注册后获取) |
| `WORKER_TOKEN` | - | 否 | Worker 认证 Token (自动获取) |
| `ADB_SERIAL` | - | 是 | 绑定的 Android 设备序列号 |
| `WORKER_PORT` | `8765` | 否 | Socket 监听端口 |
| `HEARTBEAT_INTERVAL` | `30` | 否 | 心跳间隔 (秒) |

### 5.3 Device 环境变量详解

| 变量名 | 默认值 | 必填 | 说明 |
|--------|--------|------|------|
| `WORKER_HOST` | `192.168.1.100` | 是 | Worker IP 地址 |
| `WORKER_PORT` | `8765` | 是 | Worker Socket 端口 |
| `BACKEND_URL` | `http://localhost:8000` | 是 | Backend 服务地址 |
| `DEVICE_ID` | `device-001` | 否 | 设备标识 (默认自动生成) |

### 5.4 生产环境安全配置

**重要: 生产环境必须修改以下密钥**

```bash
# Backend 生产环境
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export HMAC_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Worker 生产环境
export WORKER_TOKEN=<get-from-backend-registration>
```

### 5.5 网络拓扑配置

**USB 反向网络 (默认)**

Device 通过 USB ADB 反向网络访问 Backend:

```
Device → USB → Worker → Backend
```

**站点 VPN (备选)**

如 USB 反向网络不可用,切换站点 VPN:

```
Device → VPN → Backend
```

---

## 6. 快速启动

### 6.1 启动顺序

```
1. Backend (Docker Compose)
2. Worker (Desktop)
3. Device (Android)
4. 提交测试事务
```

### 6.2 Step 1: 启动 Backend

```bash
# 启动所有服务
docker-compose -f scripts/docker-compose.yaml up -d

# 验证服务
curl http://localhost:8000/health
# {"status":"healthy"}

# 查看日志
docker logs -f <container_name>
```

### 6.3 Step 2: 启动 Worker

```bash
# Terminal
cd worker
source .venv/bin/activate

export ADB_SERIAL=RF8N1234567A
export BACKEND_URL=http://localhost:8000

python worker/main.py
```

### 6.4 Step 3: 启动 Device

在 Android 设备上启动 Device Agent 应用

### 6.5 Step 4: 提交测试事务

```bash
# 单笔新保提交
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "business_type": "NEW",
    "customer_phone": "13812345678",
    "attachments_meta": [
      {"file_type": "ID_CARD", "file_format": "JPG"},
      {"file_type": "DRIVING_LICENSE", "file_format": "JPG"}
    ]
  }'

# 响应示例:
# {
#   "transaction_id": "TXN-20260608-abc12345",
#   "status": "PENDING",
#   "submitted_at": "2026-06-08T10:00:00Z",
#   "attachments": [...]
# }
```

### 6.6 监控状态

```bash
# 查看事务状态
curl http://localhost:8000/api/v1/transactions/<transaction_id>

# 查看 Worker 列表
curl http://localhost:8000/api/v1/workers

# 查看设备列表
curl http://localhost:8000/api/v1/devices

# 查看下载 URL
curl -X POST http://localhost:8000/api/v1/transactions/<transaction_id>/download-urls
```

---

## 7. 故障排查

### 7.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: airtest` | 依赖未安装 | `pip install -r worker/requirements.txt` |
| `ADB connection failed` | USB 调试未开启 | 在 Android 设置中启用 USB 调试 |
| `Worker registration failed` | Backend 不可达 | 检查 `BACKEND_URL` 和防火墙 |
| `Device socket connection refused` | 端口不匹配 | 确认 Worker 和 Device 的 `WORKER_PORT` 一致 |
| `401 Unauthorized` on downloads | Token 过期或缺失 | 重启 Worker 重新注册 |
| `curl: (7) Failed to connect` | Backend 未启动 | `docker-compose up -d` |
| `psql: connection refused` | PostgreSQL 未启动 | 检查 Docker 容器状态 |

### 7.2 网络检查清单

- [ ] Worker 可访问 `BACKEND_URL:8000` (出方向 443)
- [ ] Worker 与 Device 在同一局域网 (Socket 通信)
- [ ] Device 可通过 USB 反向网络访问 Backend

### 7.3 日志位置

| 组件 | 日志位置 |
|------|----------|
| Backend | `docker logs <container>` |
| Worker | 标准输出 (终端) |
| Device | Android Logcat: `adb logcat` |

### 7.4 网络诊断命令

```bash
# 检查 Worker → Backend 连接
curl -v http://localhost:8000/health

# 检查 ADB 设备连接
adb devices

# 检查端口占用
netstat -an | grep 8765

# 检查 Docker 容器
docker ps
docker logs <container_name>
```

---

## 8. 文件结构参考

```
3is-auto-app/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/v1/              # API 路由
│   │   ├── transactions.py  # 事务接口
│   │   ├── workers.py       # Worker 注册接口
│   │   └── downloads.py     # 下载 URL 接口
│   ├── models/              # SQLAlchemy 模型
│   │   ├── transaction.py   # 事务模型
│   │   ├── worker.py        # Worker 模型
│   │   ├── device.py        # 设备模型
│   │   └── attachment.py    # 附件模型
│   ├── services/            # 业务逻辑
│   │   ├── transaction_service.py
│   │   ├── dispatcher_service.py
│   │   └── url_signature_service.py
│   ├── storage/             # 存储后端
│   │   ├── base.py          # 存储抽象接口
│   │   └── local.py         # 本地存储实现
│   ├── requirements.txt
│   └── Dockerfile
│
├── worker/
│   ├── __init__.py          # 包初始化文件
│   ├── main.py             # Worker 入口
│   ├── config.py           # 配置管理
│   ├── device_controller.py  # ADB 设备控制
│   ├── airtest_executor.py  # Airtest 执行器
│   └── requirements.txt
│
├── device/
│   ├── __init__.py          # 包初始化文件
│   ├── main.py             # Device 入口
│   ├── downloader.py       # 文件下载
│   ├── socket_client.py    # Socket 客户端
│   └── requirements.txt
│
├── scripts/
│   ├── docker-compose.yaml # Docker 编排
│   ├── init_db.sql         # 数据库初始化
│   └── test_integration.py  # 集成测试
│
├── docs/
│   ├── user-manu.md        # 本文档
│   └── specs/              # 设计文档
│
└── tests/                  # 测试代码
```

## 9. 下一步

### 9.1 生产环境配置

- [ ] 配置生产环境 JWT_SECRET 和 HMAC_SECRET_KEY
- [ ] 配置 SSL/TLS 证书
- [ ] 设置监控 (Prometheus/Grafana)
- [ ] 配置日志收集 (Loki/ELK)

### 9.2 运行测试

```bash
# 集成测试
python scripts/test_integration.py

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

### 9.3 相关文档

- [PRD 设计文档](./superpowers/specs/2026-06-05-prd-design.md) - 产品需求说明书
- [架构设计](./superpowers/specs/) - 详细架构文档

---

**文档结束**
