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
