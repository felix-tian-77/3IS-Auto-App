# User Manual Design - 3IS-Auto-App MVP

## Document Overview

**Title:** 3IS-Auto-App 用户操作手册 (User Manual)  
**Scope:** Backend, Worker, Device 三端安装与操作指南  
**Audience:** Developers / Deployment Engineers  
**Version:** V1.0 (MVP)

---

## 1. System Architecture

### 1.1 Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ PostgreSQL  │  │    Redis   │  │  FastAPI    │          │
│  │   (RDS)     │  │  (Stream)  │  │  :8000      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                           │
              HTTPS / WSS (443)
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Worker #1      │                 │  Worker #N      │
│  (Desktop PC)   │                 │  (Desktop PC)   │
│  ┌───────────┐  │                 │  ┌───────────┐  │
│  │ Airtest   │  │                 │  │ Airtest   │  │
│  │ Runtime   │  │                 │  │ Runtime   │  │
│  └───────────┘  │                 │  └───────────┘  │
│  ┌───────────┐  │                 │  ┌───────────┐  │
│  │ Socket    │  │                 │  │ Socket    │  │
│  │ Client    │  │                 │  │ Client    │  │
│  └───────────┘  │                 │  └───────────┘  │
└────────┬────────┘                 └────────┬────────┘
         │ USB ADB (:5555)                   │ USB ADB
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Device #1      │                 │  Device #N      │
│  (Android)      │                 │  (Android)      │
│  ┌───────────┐  │                 │  ┌───────────┐  │
│  │ Socket    │  │                 │  │ Socket    │  │
│  │ Server    │  │                 │  │ Server    │  │
│  └───────────┘  │                 │  └───────────┘  │
│  ┌───────────┐  │                 │  ┌───────────┐  │
│  │ Downloader│  │                 │  │ Downloader│  │
│  └───────────┘  │                 │  └───────────┘  │
└─────────────────┘                 └─────────────────┘
```

### 1.2 Port Mapping

| Component | Port | Protocol | Purpose |
|-----------|------|----------|---------|
| Backend API | 8000 | HTTPS | REST API + WebSocket |
| PostgreSQL | 5432 | TCP | Database |
| Redis | 6379 | TCP | Stream Queue |
| Worker Socket | 8765/8766/8767 | TCP | Worker ↔ Device LAN |
| ADB | 5555 | USB | Worker ↔ Device |

### 1.3 Prerequisites

- Python 3.14+
- Docker + Docker Compose
- Android SDK (for ADB)
- USB data cable (Device to Worker)
- Network: Worker → Backend outbound 443

---

## 2. Backend Installation

### 2.1 Docker Compose Method (Recommended)

```bash
cd /data/workspaces/3IS-Auto-App
docker-compose -f scripts/docker-compose.yaml up -d
```

**Services:**
- `postgres`: PostgreSQL 16 with `init_db.sql` schema
- `redis`: Redis 7 for Stream queue
- `backend`: FastAPI application

**Verification:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### 2.2 Manual Python Installation (Development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run migrations (if using Alembic)
# alembic upgrade head

# Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2.3 Environment Variables

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/3is_auto

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_LOCAL_PATH=/data/attachments
STORAGE_BACKEND=local

# Security
JWT_SECRET=your-production-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# URL Signing
HMAC_SECRET_KEY=your-hmac-secret-here

# Timeouts
DOWNLOAD_URL_TTL_SECONDS=300
PENDING_TIMEOUT_SECONDS=600
TRANSACTION_TIMEOUT_SECONDS=1800

# App
APP_NAME=3IS-Auto-App
```

---

## 3. Worker Installation

### 3.1 Python Environment Setup

```bash
cd worker
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Requirements: airtest==1.2.16, pocoui==1.0.35, requests, pyyaml, websocket-client
```

### 3.2 Android SDK & ADB

```bash
# Install Android SDK Platform Tools
# Download from: https://developer.android.com/studio/releases/platform-tools

# Verify ADB installation
adb version
# Expected: Android Debug Bridge version 1.0.41

# Enable USB debugging on Android device
# Settings → Developer Options → USB debugging → ON
```

### 3.3 Configuration

Create `worker/.env`:

```env
# Backend Connection
BACKEND_URL=http://localhost:8000

# Worker Identity
WORKER_ID=
WORKER_TOKEN=
ADB_SERIAL=<your-device-serial>
WORKER_PORT=8765

# Optional: Multiple Workers on same machine
# WORKER_PORT=8766
# WORKER_PORT=8767
```

### 3.4 Device Serial Connection

```bash
# Connect Android device via USB
# Verify device is detected
adb devices
# Expected output:
# List of devices attached
# <serial_number>    device

# If device not authorized:
adb kill-server
adb start-server
adb devices
```

### 3.5 Start Worker

```bash
source .venv/bin/activate
export ADB_SERIAL=<your-device-serial>
export BACKEND_URL=http://localhost:8000
python worker/main.py
```

**Expected output:**
```
INFO: Worker starting with ADB serial: <serial>
INFO: Worker registered: WKR-20260608-xxxxxxx
INFO: Worker started successfully
```

---

## 4. Device (Android Agent) Installation

### 4.1 APK Installation

The Device Agent is a simplified Android app (APK) that:
- Receives download instructions via Socket from Worker
- Downloads files from Backend signed URLs
- Reports status to Backend

**Installation:**
```bash
# Connect device
adb install device-app.apk
```

### 4.2 Configuration

Create `device/.env`:

```env
# Worker Connection (LAN)
WORKER_HOST=192.168.1.100
WORKER_PORT=8765

# Backend Connection
BACKEND_URL=http://localhost:8000

# Device Identity
DEVICE_ID=device-001
```

### 4.3 Start Device Agent

```bash
# On Android device or via ADB
am start -n com.example.deviceagent/.MainActivity

# Or via command line
adb shell am start -n com.example.deviceagent/.MainActivity
```

---

## 5. Quick Start Workflow

### 5.1 Start Backend

```bash
docker-compose -f scripts/docker-compose.yaml up -d
# Verify
curl http://localhost:8000/health
```

### 5.2 Start Worker

```bash
# Terminal 1
source worker/.venv/bin/activate
export ADB_SERIAL=<device-serial>
python worker/main.py
```

### 5.3 Start Device

```bash
# On Android device
# Launch Device Agent app
```

### 5.4 Submit Transaction (Test)

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "business_type": "NEW",
    "customer_phone": "13812345678",
    "attachments_meta": [{"file_type": "ID_CARD", "file_format": "JPG"}]
  }'
```

### 5.5 Monitor Status

```bash
# Check transaction status
curl http://localhost:8000/api/v1/transactions/<transaction_id>

# Check worker status
curl http://localhost:8000/api/v1/workers
```

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: airtest` | Dependencies not installed | `pip install -r worker/requirements.txt` |
| `ADB connection failed` | USB debugging not enabled | Enable USB debugging in Android settings |
| `Worker registration failed` | Backend not reachable | Check `BACKEND_URL` and firewall rules |
| `Device socket connection refused` | Worker port mismatch | Verify `WORKER_PORT` matches in worker and device |
| `401 Unauthorized` on downloads | Token expired or missing | Restart worker to re-register |

### 6.2 Network Checklist

- [ ] Worker can reach `BACKEND_URL:8000` (outbound 443)
- [ ] Worker and Device on same LAN (for Socket communication)
- [ ] Device can reach Backend via USB reverse network

### 6.3 Log Locations

| Component | Log Location |
|----------|--------------|
| Backend | Docker: `docker logs <container>` |
| Worker | stdout (terminal) |
| Device | Android Logcat: `adb logcat` |

---

## 7. File Structure Reference

```
3is-auto-app/
├── backend/
│   ├── main.py              # FastAPI entry
│   ├── config.py            # Settings
│   ├── api/v1/              # API routes
│   ├── models/              # SQLAlchemy models
│   ├── services/            # Business logic
│   ├── storage/            # StorageBackend
│   ├── requirements.txt
│   └── Dockerfile
├── worker/
│   ├── main.py             # Worker entry
│   ├── config.py           # Configuration
│   ├── device_controller.py # ADB control
│   ├── airtest_executor.py # Airtest runtime
│   └── requirements.txt
├── device/
│   ├── main.py             # Device entry
│   ├── downloader.py       # File download
│   ├── socket_client.py   # Socket to Worker
│   └── requirements.txt
├── scripts/
│   ├── docker-compose.yaml
│   ├── init_db.sql
│   └── test_integration.py
└── docs/
    └── user-manu.md        # This document
```

---

## 8. Next Steps

- Configure production secrets (JWT_SECRET, HMAC_SECRET_KEY)
- Set up monitoring (Prometheus/Grafana)
- Configure SSL/TLS for production
- Run integration tests: `python scripts/test_integration.py`