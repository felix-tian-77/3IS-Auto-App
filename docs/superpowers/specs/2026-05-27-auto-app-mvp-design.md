# 3IS-Auto-App MVP 设计文档

## 概述

构建基于 Airtest 的企业级 Android 自动化 RPA 平台 MVP。脚本以文件形式存储于本地代码库，运行时动态从 PostgreSQL 拉取业务数据驱动执行，采用 UV 作为 Python 环境管理工具，实现灵活、高效的无人值守自动化。

### 需求决策摘要

| 维度 | 决策 |
|------|------|
| 范围 | 完整 MVP（骨架 + 数据层 + 引擎 + 编排），业务流程后续迭代 |
| 设备 | USB 物理设备，2-5 台并行 |
| 数据库 | PostgreSQL (Docker) |
| 触发方式 | CLI + 定时调度 + HTTP API |
| API | FastAPI + API Key 认证 |
| 结果存储 | 截图/日志存本地文件，PG 存路径引用 |
| 失败通知 | 抽象 Notifier 接口，MVP 实现 Webhook |
| 进程模型 | 单进程 + 内部任务队列抽象（InProcessExecutor），后续可替换为 Celery |

### 子项目分解

| 序号 | 子项目 | 内容 | 依赖 |
|------|--------|------|------|
| 1 | 项目骨架与环境 | 目录结构、UV 项目、pyproject.toml、.gitignore、日志框架、配置加载 | 无 |
| 2 | 数据访问层 | PostgreSQL 连接池、业务数据查询接口、数据模型、Alembic 迁移 | 1 |
| 3 | 执行引擎 | Airtest/Poco 封装、设备管理、脚本运行器、截图/日志采集 | 1 |
| 4 | 流程编排引擎 | YAML 配置解析、原子脚本注册、串行/并行/条件分支执行、流程调度器 | 1, 2, 3 |
| 5 | 入口层 | CLI (Typer)、HTTP API (FastAPI)、定时调度 (APScheduler) | 1, 2, 3, 4 |
| 6 | MVP 业务流程 | 2-3 个真实业务流程脚本 + 对应的数据库种子数据 + 配置文件（后续迭代） | 1-5 |

子项目 1-3 可并行开发，4 是集成层，5 是入口层，6 是验证。

---

## 1. 整体架构与组件边界

```
+-------------------------------------------------------------+
|                     Entry Layer (入口层)                     |
|   +----------+    +----------+    +------------------+      |
|   |   CLI    |    |   API    |    |   Scheduler      |      |
|   | (Typer)  |    |(FastAPI) |    |  (APScheduler)   |      |
|   +----+-----+    +----+-----+    +--------+---------+      |
+------|---------------|-------------------|------------------+
       |               |                   |
       +---------------+-------------------+
                       |  submit(flow_run_request)
                       v
+-------------------------------------------------------------+
|              Orchestration Layer (编排层)                    |
|   +--------------+  +--------------+  +--------------+      |
|   | FlowLoader   |  | FlowExecutor |  |TaskExecutor  |      |
|   | (YAML->Plan) |  | (DAG runner) |  | (interface)  |      |
|   +--------------+  +--------------+  +------+-------+      |
|                                              |              |
|                                +-------------+-------+      |
|                                v                     v      |
|                       InProcessExecutor      [Future:Celery]|
+-------------------------------------------------------------+
                       |
                       v
+-------------------------------------------------------------+
|              Execution Layer (执行层)                        |
|   +--------------+  +--------------+  +--------------+      |
|   | DeviceManager|  | ScriptRunner |  | ArtifactSink |      |
|   | (ADB pool)   |  | (Airtest)    |  | (file+log)   |      |
|   +--------------+  +--------------+  +--------------+      |
+-------------------------------------------------------------+
                       |
                       v
+-------------------------------------------------------------+
|              Infrastructure Layer (基础设施层)                |
|   +--------------+  +--------------+  +--------------+      |
|   |   Database   |  |   Notifier   |  |   Storage    |      |
|   | (PG+SQLAlch) |  | (Webhook)    |  | (local file) |      |
|   +--------------+  +--------------+  +--------------+      |
+-------------------------------------------------------------+
```

### 四层职责

- **入口层**：三种触发方式的薄封装，都最终调用编排层的同一个 `submit()` 接口
- **编排层**：解析 YAML 流程定义 -> 生成执行计划（DAG）-> 通过 `TaskExecutor` 接口提交任务。`TaskExecutor` 是抽象，MVP 实现 `InProcessExecutor`（基于 `concurrent.futures.ThreadPoolExecutor`）
- **执行层**：单个原子脚本的运行环境，负责拿设备、跑脚本、收集产物
- **基础设施层**：跨层的横切关注点，每个都是接口 + 实现，便于替换

### 边界规则

- 编排层不直接 import Airtest，只通过执行层调用
- 执行层不知道流程编排，只接收"在设备 X 上运行脚本 Y，参数 Z"
- 入口层不直接调用执行层，必须经过编排层
- 通知器、存储器都是接口注入，业务代码不感知具体实现

---

## 2. 目录结构与项目骨架

```
3IS-Auto-App/
+-- pyproject.toml              # UV 项目定义，依赖、脚本入口
+-- uv.lock                     # UV 锁文件
+-- .python-version             # Python 版本（3.11）
+-- .gitignore
+-- .env.example                # 环境变量模板
+-- README.md
+-- docker-compose.yml          # PostgreSQL 容器
|
+-- src/
|   +-- auto_app/               # 主包（snake_case，import 友好）
|       +-- __init__.py
|       |
|       +-- cli/                # 入口层 - CLI
|       |   +-- __init__.py
|       |   +-- main.py         # Typer 应用入口
|       |
|       +-- api/                # 入口层 - HTTP API
|       |   +-- __init__.py
|       |   +-- app.py          # FastAPI 实例
|       |   +-- auth.py         # API Key 中间件
|       |   +-- routers/
|       |   |   +-- flows.py    # /flows/* 端点
|       |   |   +-- runs.py     # /runs/* 端点
|       |   |   +-- devices.py  # /devices/* 端点
|       |   +-- schemas.py      # Pydantic 请求/响应模型
|       |
|       +-- scheduler/          # 入口层 - 定时调度
|       |   +-- __init__.py
|       |   +-- scheduler.py    # APScheduler 封装
|       |
|       +-- orchestration/      # 编排层
|       |   +-- __init__.py
|       |   +-- loader.py       # YAML -> FlowDefinition
|       |   +-- models.py       # FlowDefinition / StepDefinition / RunRequest
|       |   +-- executor.py     # FlowExecutor，编排 DAG
|       |   +-- task_executor.py # TaskExecutor 接口 + InProcessExecutor
|       |
|       +-- execution/          # 执行层
|       |   +-- __init__.py
|       |   +-- device_manager.py  # ADB 设备发现/分配/释放
|       |   +-- script_runner.py   # Airtest/Poco 脚本执行
|       |   +-- artifact_sink.py   # 截图/日志收集
|       |
|       +-- infrastructure/     # 基础设施层
|       |   +-- __init__.py
|       |   +-- db/
|       |   |   +-- engine.py        # SQLAlchemy engine + session
|       |   |   +-- models.py        # ORM 模型（FlowRun/StepRun/Device 等）
|       |   |   +-- repositories.py  # 业务数据查询接口
|       |   +-- notifier/
|       |   |   +-- base.py          # Notifier 接口
|       |   |   +-- webhook.py       # WebhookNotifier 实现
|       |   +-- storage/
|       |       +-- base.py          # ArtifactStorage 接口
|       |       +-- local.py         # LocalFileStorage 实现
|       |
|       +-- config/             # 配置加载
|       |   +-- __init__.py
|       |   +-- settings.py     # Pydantic Settings (从 env + yaml)
|       |
|       +-- logging_config.py   # 结构化日志（structlog）
|       +-- context.py          # 脚本运行上下文（get_params / set_result）
|
+-- flows/                      # 原子化业务脚本（本地仓库）
|   +-- README.md
|   +-- _example/
|       +-- hello.py            # 示例脚本，验证调度链路
|
+-- configs/                    # 流程编排配置
|   +-- flows/
|   |   +-- _example.yaml       # 示例流程定义
|   +-- schedules/
|       +-- _example.yaml       # 示例定时调度
|
+-- migrations/                 # Alembic 数据库迁移
|   +-- alembic.ini
|   +-- env.py
|   +-- versions/
|
+-- artifacts/                  # 运行产物（截图/日志）-- gitignore
|   +-- .gitkeep
|
+-- tests/
|   +-- conftest.py
|   +-- unit/
|   |   +-- test_loader.py
|   |   +-- test_executor.py
|   +-- integration/
|       +-- test_end_to_end.py
|
+-- docs/
    +-- superpowers/
        +-- specs/              # 设计文档存放处
```

### 目录设计决策

1. `src/` 布局：避免开发时 import 路径污染，符合现代 Python 包最佳实践
2. 包名 `auto_app`：原仓库名 `3IS-Auto-App` 含连字符和数字开头，不能作为 Python 包名
3. `flows/` 与 `src/` 平级：业务脚本不属于核心代码包，但同属仓库，便于版本控制
4. `configs/` 拆分 `flows/` 和 `schedules/`：流程定义和调度计划是不同关注点
5. `migrations/` 用 Alembic：DDL 变更纳入版本控制，企业级必备
6. `artifacts/` 加 `.gitkeep` 但内容 gitignore：保留目录结构，运行产物不入库

### 核心依赖（pyproject.toml）

- `airtest`, `pocoui` -- 自动化引擎
- `fastapi`, `uvicorn[standard]` -- HTTP API
- `typer` -- CLI
- `apscheduler` -- 定时调度
- `sqlalchemy[asyncio]`, `psycopg[binary]`, `alembic` -- 数据库
- `pydantic`, `pydantic-settings` -- 配置和数据校验
- `pyyaml` -- 流程配置解析
- `httpx` -- Webhook 通知
- `structlog` -- 结构化日志
- 开发：`pytest`, `pytest-asyncio`, `ruff`, `mypy`

---

## 3. 数据模型与数据库设计

### business_data（业务数据）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| category | VARCHAR | 数据分类（如 "account", "product"） |
| key | VARCHAR | 数据标识（如 "user_001"） |
| payload | JSONB | 灵活的业务数据内容 |
| env | VARCHAR | 环境标识（dev/staging/prod） |
| is_active | BOOLEAN | 软删除标记 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

索引：`(category, env)`, `(key, env)`

### devices（设备）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| serial | VARCHAR UNIQUE | ADB 序列号 |
| model | VARCHAR | 设备型号 |
| status | ENUM | available / busy / offline |
| last_heartbeat | TIMESTAMP | 最后心跳时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### flow_runs（流程运行记录）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| flow_name | VARCHAR | 流程名（对应 YAML 文件名） |
| status | ENUM | pending / running / success / failed |
| trigger_type | ENUM | cli / api / schedule |
| trigger_by | VARCHAR | 触发者（API key ID / "cli"） |
| config_snapshot | JSONB | 执行时的流程配置快照 |
| business_data_refs | JSONB | 关联的业务数据 ID 列表 |
| started_at | TIMESTAMP | 开始时间 |
| finished_at | TIMESTAMP | 结束时间 |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

索引：`(flow_name)`, `(status)`, `(created_at)`

### step_runs（步骤运行记录）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| flow_run_id | UUID FK -> flow_runs.id | 所属流程运行 |
| step_name | VARCHAR | 步骤名（对应原子脚本名） |
| sequence | INTEGER | 执行顺序 |
| device_id | UUID FK -> devices.id NULLABLE | 分配的设备 |
| status | ENUM | pending / running / success / failed |
| business_data_id | UUID FK -> business_data.id NULLABLE | 关联业务数据 |
| started_at | TIMESTAMP | 开始时间 |
| finished_at | TIMESTAMP | 结束时间 |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

索引：`(flow_run_id)`, `(device_id)`, `(status)`

### artifacts（运行产物）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| step_run_id | UUID FK -> step_runs.id | 所属步骤运行 |
| artifact_type | ENUM | screenshot / log / video |
| file_path | VARCHAR | 本地文件路径 |
| file_size | BIGINT | 字节数 |
| created_at | TIMESTAMP | 创建时间 |

索引：`(step_run_id)`, `(artifact_type)`

### notifications（通知记录）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| flow_run_id | UUID FK -> flow_runs.id | 所属流程运行 |
| notifier_type | VARCHAR | "webhook" |
| target | VARCHAR | Webhook URL 等 |
| status | ENUM | pending / sent / failed |
| payload | JSONB | 发送的内容 |
| response_code | INTEGER | HTTP 响应码 |
| attempts | INTEGER | 重试次数 |
| created_at | TIMESTAMP | 创建时间 |
| sent_at | TIMESTAMP | 发送时间 |

索引：`(flow_run_id)`, `(status)`

### 数据模型设计决策

1. `business_data.payload` 用 JSONB：业务数据结构多变，JSONB 避免为每种数据建表，同时保留索引和查询能力
2. `flow_runs.config_snapshot`：执行时快照流程配置，防止后续修改配置导致历史记录不可追溯
3. `business_data_refs` 用 JSONB 存 ID 列表：一次流程运行可能关联多条业务数据，但不需要中间表的关联查询复杂度
4. `step_runs.device_id` 可 NULL：步骤未开始执行时未分配设备
5. `notifications` 独立表：通知是异步操作，需要独立的状态追踪和重试机制
6. 全部主键用 UUID：分布式环境下友好，API 暴露 ID 时不会泄露业务量信息

---

## 4. 编排引擎

### 流程定义格式（YAML）

```yaml
# configs/flows/ecommerce_checkout.yaml
name: ecommerce_checkout
description: "电商下单流程"
tags: [ecommerce, checkout]

business_data:
  category: account
  env: "${ENV}"
  strategy: round_robin    # round_robin / random / all

steps:
  - name: login
    script: flows/login.py
    params:
      username: "${data.username}"
      password: "${data.password}"

  - name: browse_product
    script: flows/browse.py
    depends_on: [login]
    params:
      product_id: "${data.product_id}"

  - name: add_to_cart
    script: flows/add_cart.py
    depends_on: [browse_product]

  - name: checkout
    script: flows/checkout.py
    depends_on: [add_to_cart]

  - name: cleanup
    script: flows/cleanup.py
    depends_on: [checkout]
    always_run: true
```

### 编排流程

1. YAML 文件通过 `FlowLoader.parse()` 解析为 `FlowDefinition`
2. `FlowExecutor.execute()` 接收 `RunRequest`，构建 DAG（拓扑排序）
3. 解析数据依赖（替换 `${data.xxx}` 和 `${ENV}`）
4. 通过 `TaskExecutor.submit()` 提交任务
5. 无依赖步骤可并行提交，有依赖步骤等待依赖完成
6. 每个步骤执行：`DeviceManager.allocate()` -> `ScriptRunner.run()` -> `ArtifactSink.collect()` -> `DeviceManager.release()` -> 更新 `step_runs` 状态
7. 全部完成 -> 汇总结果；任何步骤失败 -> 检查 `always_run` -> `Notifier.notify()`

### 核心接口

```python
# orchestration/models.py
class FlowDefinition:
    name: str
    steps: list[StepDefinition]
    business_data_config: BusinessDataConfig

class StepDefinition:
    name: str
    script: str
    params: dict[str, Any]
    depends_on: list[str]
    always_run: bool

class RunRequest:
    flow_name: str
    trigger_type: Literal["cli", "api", "schedule"]
    trigger_by: str
    env: str
    business_data_ids: list[str] | None
```

```python
# orchestration/task_executor.py
class TaskExecutor(Protocol):
    def submit(self, func: Callable, **kwargs) -> TaskHandle: ...
    def shutdown(self) -> None: ...

class TaskHandle(Protocol):
    def result(self) -> Any: ...
    def status(self) -> TaskStatus: ...

class InProcessExecutor:
    """MVP 实现，基于 concurrent.futures.ThreadPoolExecutor"""
    def __init__(self, max_workers: int = 5): ...
```

### 编排设计决策

1. DAG 拓扑排序：`depends_on` 声明依赖，无依赖步骤自动并行，无需显式标记并行/串行
2. `${data.xxx}` 模板变量：运行时从 `business_data.payload` 替换，脚本不感知数据来源
3. `${ENV}` 环境变量注入：流程配置可以引用环境变量，同一套 YAML 适配多环境
4. `always_run`：类似 CI 的 cleanup 步骤，用于登出、恢复环境等
5. `business_data.strategy`：round_robin（轮询负载均衡）、random（随机取一条）、all（每条数据都执行一遍完整流程）
6. `TaskExecutor` 为 Protocol：MVP 用 `InProcessExecutor`，后续替换 Celery 只需新增一个实现类
7. 线程池 max_workers=5：对应 2-5 台设备，每个线程绑定一台设备执行

---

## 5. 执行引擎与设备管理

### 设备管理

```
DeviceManager
|
|-- discover()
|   |-- adb devices -> 已连接设备列表
|   |-- 与 PG devices 表同步
|   |   |-- 新设备 -> INSERT (status=available)
|   |   |-- 已有设备 -> UPDATE heartbeat
|   |   +-- 失联设备 -> UPDATE status=offline
|   +-- 启动时调用 + 定时心跳（每 30s）
|
|-- allocate(requirements=None) -> Device
|   |-- 从 PG 查 status=available 的设备
|   |-- SELECT ... FOR UPDATE SKIP LOCKED (避免并发分配同一台设备)
|   |-- UPDATE status=busy
|   +-- 返回 Device 对象
|
|-- release(device_id)
|   |-- UPDATE status=available
|   +-- 更新 heartbeat
|
+-- health_check(device_id) -> bool
    |-- adb -s <serial> shell echo ok
    +-- 失败 -> UPDATE status=offline
```

### 脚本运行器（子进程隔离）

主进程 (编排)                    子进程 (Airtest)
+------------------+             +------------------+
| FlowExecutor     |             |                  |
|   |              |  subprocess |  flows/login.py  |
|   +-- submit() --+----------->|  import airtest  |
|   |              |             |  操作设备...      |
|   |              |<-----------+|  exit(0/1)       |
|   +-- collect    |  exit code  |                  |
|      result      |             +------------------+
+------------------+

**为什么子进程而不是直接 import 调用？**

1. 隔离 Airtest 的全局状态：Airtest 在进程内维护设备连接等全局变量，多个流程共用进程会导致状态污染
2. 崩溃隔离：Airtest/Poco 的 native 崩溃不会拖垮编排进程
3. 资源释放：子进程退出后 ADB 连接自然释放，不会泄漏
4. 并行安全：每个子进程独立持有设备连接，无线程安全问题

**参数传递机制**：

- 主进程将 `params` 序列化为 JSON 写入临时文件
- 子进程通过环境变量 `AUTO_APP_PARAMS_FILE` 获取文件路径
- 子进程内通过 `auto_app.context.get_params()` 读取

**结果回传机制**：

- 子进程将结果写入 `AUTO_APP_RESULT_FILE` 指定的 JSON 文件
- 主进程在子进程退出后读取，结合 exit code 判断成功/失败
- 截图/日志由 `ArtifactSink` 在子进程退出后从已知目录收集

### ArtifactSink

```python
# execution/artifact_sink.py
class ArtifactSink:
    def __init__(self, storage: ArtifactStorage, db: Repository): ...

    def collect(self, step_run_id: str, work_dir: Path):
        """
        从脚本工作目录收集产物：
        1. 扫描 log/ 子目录 -> log 文件
        2. 扫描 screenshot/ 子目录 -> 截图
        3. 通过 Storage 保存，获取路径
        4. 写入 artifacts 表
        """
```

### 原子脚本约定

每个 `flows/` 下的原子脚本必须遵循以下约定：

```python
# flows/login.py
from auto_app.context import get_params, set_result

params = get_params()  # 获取注入参数

# ... Airtest 操作 ...

set_result({"order_id": "12345"})  # 可选，输出给下游步骤
```

约定：
- 入口无参数，通过 `get_params()` 获取数据
- 成功退出码 0，非零为失败
- 截图保存到 `./screenshot/` 目录（Airtest 默认行为）
- 日志保存到 `./log/` 目录
- 可选调用 `set_result()` 输出数据供下游步骤使用

---

## 6. 入口层（CLI / API / 调度器）

### CLI（Typer）

```bash
# 运行流程
auto-app run --flow ecommerce_checkout --env dev

# 查看流程列表
auto-app flows list

# 查看设备状态
auto-app devices list

# 查看运行历史
auto-app runs list --flow ecommerce_checkout --limit 10

# 查看单次运行详情
auto-app runs show <run_id>

# 启动 API 服务
auto-app serve --host 0.0.0.0 --port 8000

# 数据库迁移
auto-app db migrate
auto-app db upgrade

# 刷新设备发现
auto-app devices discover
```

所有命令最终调用编排层的 `FlowExecutor.execute()` 或 `Repository` 查询接口，CLI 只是薄封装。

### HTTP API（FastAPI）

```
认证：X-API-Key header，key 存储在 .env / 环境变量

POST   /api/v1/runs                 # 提交流程执行
       body: { flow_name, env, business_data_ids? }
       resp: { run_id, status: "pending" }

GET    /api/v1/runs                  # 查询运行列表
       query: flow_name?, status?, limit?, offset?
       resp: { items: [...], total }

GET    /api/v1/runs/{run_id}        # 单次运行详情（含步骤）
       resp: { run, steps: [...], artifacts: [...] }

POST   /api/v1/runs/{run_id}/cancel  # 取消运行

GET    /api/v1/flows                 # 列出可用流程（扫描 configs/flows/）
       resp: { items: [{ name, description, steps_count }] }

GET    /api/v1/flows/{name}          # 流程定义详情

GET    /api/v1/devices               # 设备列表
       resp: { items: [{ serial, model, status }] }

GET    /api/v1/artifacts/{id}/download  # 下载产物文件
```

**API Key 认证实现**：

```python
# api/auth.py
async def verify_api_key(request: Request) -> str:
    key = request.headers.get("X-API-Key")
    if key not in settings.api_keys:
        raise HTTPException(401, "Invalid API Key")
    return key  # 返回 key_id 作为 trigger_by
```

`api_keys` 配置在 `.env` 中，格式：`API_KEYS=key1:secret1,key2:secret2`

### 定时调度器（APScheduler）

```yaml
# configs/schedules/ecommerce_nightly.yaml
flow_name: ecommerce_checkout
env: prod
schedule:
  type: cron
  hour: 2
  minute: 0
  day_of_week: "mon-fri"
business_data:
  strategy: round_robin
```

```python
# scheduler/scheduler.py
class FlowScheduler:
    def __init__(self, executor: FlowExecutor, loader: FlowLoader): ...

    def start(self):
        """扫描 configs/schedules/，注册定时任务"""
        for schedule_config in self._load_schedules():
            self._scheduler.add_job(
                self.executor.execute,
                trigger=CronTrigger(**schedule_config.schedule),
                args=[RunRequest(...)],
                id=schedule_config.flow_name,
                replace_existing=True,
            )
        self._scheduler.start()

    def reload(self):
        """热重载调度配置（监听文件变更或 API 触发）"""
        self._scheduler.remove_all_jobs()
        self.start()
```

### 单进程启动流程

```bash
# 启动全部组件（API + 调度器）
auto-app serve --with-scheduler

# 仅启动 API（不含定时调度）
auto-app serve

# 仅运行一次性流程
auto-app run --flow xxx
```

`serve` 命令内部：
1. 初始化 DB 连接池
2. 启动 DeviceManager 心跳
3. 如果 `--with-scheduler`，启动 APScheduler
4. 启动 uvicorn（FastAPI）
5. APScheduler 运行在 FastAPI 的同一个事件循环中（`lifespan` 中启动）

### 入口层设计决策

1. CLI 和 API 调用同一个 `FlowExecutor`：保证行为一致，CLI 只是 API 的同步版本
2. API 返回 `run_id` 后立即响应：执行异步进行，客户端通过 `GET /runs/{id}` 轮询状态
3. `--with-scheduler` 显式开关：开发调试时不需要调度器，避免定时任务干扰
4. 调度配置支持热重载：修改 `configs/schedules/` 后无需重启服务
5. API Key 格式 `id:secret`：日志中记录 `id` 而非 `secret`，便于审计

---

## 7. 基础设施层

### 数据库访问

```python
# infrastructure/db/engine.py
# SQLAlchemy 2.0 async 风格
engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=5)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# infrastructure/db/repositories.py
class Repository:
    async def create_flow_run(self, run: FlowRunCreate) -> FlowRun: ...
    async def update_flow_run_status(self, run_id: str, status: RunStatus) -> None: ...
    async def allocate_device(self) -> Device | None: ...
    async def release_device(self, device_id: str) -> None: ...
    async def query_business_data(self, category: str, env: str, strategy: str) -> list[BusinessData]: ...
    async def save_artifact(self, artifact: ArtifactCreate) -> Artifact: ...
    async def save_notification(self, notification: NotificationCreate) -> Notification: ...
```

关键点：
- 全部 async，与 FastAPI 事件循环兼容
- `allocate_device()` 使用 `SELECT ... FOR UPDATE SKIP LOCKED`，保证并发安全
- 数据库迁移通过 Alembic 管理，CLI 提供 `auto-app db upgrade` 命令

### 通知器

```python
# infrastructure/notifier/base.py
class Notifier(Protocol):
    async def send(self, notification: Notification) -> SendResult: ...

class SendResult:
    success: bool
    response_code: int | None
    error: str | None

# infrastructure/notifier/webhook.py
class WebhookNotifier:
    def __init__(self, http_client: httpx.AsyncClient): ...

    async def send(self, notification: Notification) -> SendResult:
        """
        POST JSON payload 到配置的 Webhook URL
        超时 10s，失败重试最多 3 次（指数退避）
        """
```

通知触发时机：
- `flow_runs` 状态变为 `failed` 时触发
- 通知内容包含：流程名、运行 ID、失败步骤、错误信息、时间戳
- 通知结果写入 `notifications` 表

Webhook 配置（`.env`）：
```
NOTIFIER_WEBHOOK_URL=https://hooks.dingtalk.com/xxx
NOTIFIER_WEBHOOK_SECRET=xxx          # 可选，签名用
```

### 存储器

```python
# infrastructure/storage/base.py
class ArtifactStorage(Protocol):
    def save(self, src: Path, artifact_type: str, step_run_id: str) -> str: ...

# infrastructure/storage/local.py
class LocalFileStorage:
    """
    MVP 实现：保存到本地 artifacts/ 目录
    目录结构：artifacts/{run_id}/{step_name}/{filename}
    """
    def save(self, src: Path, artifact_type: str, step_run_id: str) -> str:
        dest = self.base_dir / run_id / step_name / src.name
        shutil.copy2(src, dest)
        return str(dest)
```

后续替换为 S3/MinIO 时，只需新增 `S3Storage` 实现，`save()` 返回 S3 URL。

### 配置加载

```python
# config/settings.py
class Settings(pydantic_settings.BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # 数据库
    database_url: str = "postgresql+asyncpg://auto_app:secret@localhost:5432/auto_app"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_keys: dict[str, str] = {}  # key_id -> key_secret

    # 设备
    device_heartbeat_interval: int = 30  # 秒

    # 存储
    artifact_base_dir: str = "./artifacts"

    # 通知
    notifier_webhook_url: str = ""
    notifier_webhook_secret: str = ""
    notifier_max_retries: int = 3

    # 执行器
    task_executor_workers: int = 5

    # 调度器
    scheduler_enabled: bool = False
```

所有配置通过环境变量或 `.env` 文件注入，无硬编码。

### 结构化日志

```python
# logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if IS_DEV else structlog.processors.JSONRenderer(),
    ],
)
```

日志策略：
- 开发环境：彩色控制台输出，易读
- 生产环境：JSON 格式，便于 ELK/Loki 采集
- 每条日志自动绑定 `flow_run_id`、`step_run_id`（通过 contextvars），全链路可追溯
- 日志同时写入本地文件（`artifacts/{run_id}/` 下）和 PG

### docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: auto_app
      POSTGRES_USER: auto_app
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

开发环境只需 `docker compose up -d` 启动 PG，其余组件通过 `auto-app serve` 运行。
