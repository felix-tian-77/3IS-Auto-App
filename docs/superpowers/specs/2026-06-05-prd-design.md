# 3IS-Auto-App 产品需求说明书（PRD）

## 文档信息

| 字段 | 内容 |
|------|------|
| 产品名称 | 3IS-Auto-App（车险保单自动生成 RPA 系统） |
| 文档版本 | V1.3 |
| 创建日期 | 2026-06-02 |
| 最近更新 | 2026-06-05 |
| 文档状态 | Draft（待评审） |

**文档状态机：** `Draft` → `Review` → `Approved` → `Frozen`。任何重大修订必须先回退到 `Draft`，再走一轮同行评审。当前状态为 `Draft`，正在应用 2026-06-05 存储架构调整方案（OSS-first → Server-first），等待业务方、合规方、运维方三方签字后进入 `Review` / `Approved`。

### 修订记录

| 版本 | 日期 | 修订内容 | 作者 | 评审人 |
|------|------|----------|------|--------|
| V1.0 | 2026-06-02 | 初始版本 | - | - |
| V1.1 | 2026-06-03 | 应用 2026-06-03 共识会 7 项决议 + review 8 处小修 + 4 个架构级替代方案 + 10 个缺失章节初稿 | office-hours | 待签 |
| V1.2 | 2026-06-04 | **应用 2026-06-03 架构调整方案**：RPA 引擎由 Device 端迁至 Worker 端，Device Agent 极简化为"下载器 + ADB 目标"。架构级偏移，触达 §1.3/§1.4/§2.1/§3.1/§3.4/§3.5/§3.6/§4.2/§4.3/§5.2/§6.2.3/§6.3/§7.2/§7.5/§8.1/§9/§10/§10.3/§11.1/§12 等 27 处。详见下方"V1.2 修订明细"表。 | office-hours | 待签 |
| V1.3 | 2026-06-05 | **应用存储架构调整方案**：文件存储从"OSS-first"翻转为"Server-first"。V1.2 客户端先传 OSS、提交时只传 `file_url` 的设计被废弃；V1.3 起客户端 `POST /api/v1/transactions` 一并 multipart 上传文件，后端落地存储（默认 `LocalStorageBackend`），通过 `POST /transactions/{id}/download-urls` 生成内部签名 URL 供 Device 直连下载。`StorageBackend` 抽象接口预留 OSS/MinIO 等扩展后端。`OssSignedUrl` 实体 DEPRECATED，由新 `DownloadUrl` 替代。架构级偏移，触达 27 处。详见下方"V1.3 修订明细"表。 | office-hours | 待签 |

**V1.2 修订明细（基于架构设计文档 `2026-06-03-rpa-worker-side-architecture-design.md` V1.0）**：

| # | 章节 | 改动 |
|---|------|------|
| 1 | §1.3 价值主张 | ATT 调整为 5-8 分钟；新增桌面 IDE 调试便利、脚本热更新、Device Agent 极简化 |
| 2 | §1.4 范围边界 | 新增"单 Worker 限 2-3 Device"约束 |
| 3 | §2.1 角色定义 | Worker 升级为"编排 + 执行"；Android 设备降级为"下载器 + ADB 目标" |
| 4 | §3.1 主流程 | 重画为 Worker 通过 ADB 控制 Device |
| 5 | §3.4 状态机 | 新增 `ADB_CONNECTING`、`READY` 子状态 |
| 6 | §3.5 异常分支 | 新增 ADB 断开重连、Airtest 失败、USB 物理断开 |
| 7 | §3.6 BCP | 新增"Worker 进程崩溃 → 所有 Device 事务回退"场景 |
| 8 | §4.2 FR-CLI-005 | 升级为"编排 + 执行"角色 |
| 9 | §4.3 FR-MOB-001~006 | 重写 6 个移动端需求（旧描述保留并标 DEPRECATED） |
| 10 | §5.2 Device 实体 | 新增 `adb_serial`、`sandbox_path` 字段 |
| 11 | §5.2 Worker 实体 | 新增 `max_concurrent_devices` 字段 |
| 12 | §6.2.3 设备接口 | 移除 `files`、`step-result`；新增 `download-ack` |
| 13 | §6.3 Socket 通道 | 移除 `EXECUTE_STEP`、`STEP_RESULT`；保留 `DOWNLOAD_FILES` |
| 14 | §7.2 部署架构图 | 重画 |
| 15 | §7.5 硬件建议 | Worker 4C 8GB → 8C 16GB；Device 中高端 → 中低端可 |
| 16 | §8.1 性能 | ATT ≤5min → ≤8min；销售 API 限流 60/min → 40/min |
| 17 | §9 技术约束 | 新增 `airtest`、`pocoui`、`airtest.core.android.adb` |
| 18 | §10.1 验收 | 新增 AC-NEW-001~010 |
| 19 | §10.2 非功能验收 | 调整 NAC-001（ATT 5min → 8min）、NAC-002（并发 50笔/分） |
| 20 | §10.3 测试策略 | L4 录屏回归权重提升；新增桌面 IDE 调试便利性 |
| 21 | §11.1 风险 | 移除 ADB 反检测风险；新增 Worker CPU 瓶颈、单事务 ATT 延长、USB 不稳定 |
| 22 | §11.3 假设前提 | 新增 AS-010 USB 物理连接稳定性 |
| 23 | §11.4 决策记录 | **新增小节**：7 项架构级决议 |
| 24 | §12 容量规划 | 单站点 4-9 Device；月成本 ¥1200-1800 |
| 25 | §14 开放问题 | 引用架构设计文档 Q1-Q5 |

**V1.3 修订明细（基于 2026-06-05 brainstorming 决策）**：

| # | 章节 | 改动 |
|---|------|------|
| 1 | 头文件 + 修订记录 | V1.2 → V1.3；新增"应用存储架构调整"条目 |
| 2 | 术语表 | 新增 `StorageBackend`、`LocalStorageBackend`、`DownloadUrl`；`OssSignedUrl` 标记 DEPRECATED |
| 3 | §1.4 范围边界 | 新增"文件存储后端可插拔（默认本地，未来 OSS）" |
| 4 | §2.5 合规 | 调整"OSS 地域约束"为"文件存储地域约束"（不限于 OSS） |
| 5 | §3.1 主流程 | "OSS 签名 URL API" → "下载 URL API" |
| 6 | §3.5 异常分支 | 新增"本地存储磁盘满" / "存储后端不可用" |
| 7 | §3.6 BCP | 新增"本地存储故障" 场景 |
| 8 | §4.1 FR-SVR-001/002 | 改 multipart/form-data；文件随事务一并提交 |
| 9 | §4.3 FR-MOB-002 | 设备下载源从 OSS 改为后端内部 URL（协议不变） |
| 10 | §5.1 实体清单 | `OssSignedUrl` 标 DEPRECATED；新增 `DownloadUrl`、`StorageBackend` 配置 |
| 11 | §5.2 Attachment | `storage_url` 改为通用"存储后端路径"；新增 `storage_backend` 字段 |
| 12 | §5.2 新增 DownloadUrl | 实体定义（后端无关的下载凭证） |
| 13 | §6.2.1 业务接口 | `POST /transactions` 改 multipart；新增 `POST /transactions/{id}/download-urls`（重命名自 oss-urls） |
| 14 | §6.2.2 调度接口 | 接口列表更新（download-urls 替换 oss-urls） |
| 15 | §6.2.3 设备接口 | Device 仍 `GET` URL 下载，但 URL 指向后端 |
| 16 | §6.3 Socket 通道 | 协议不变（DOWNLOAD_FILES 携带 URL，URL 指向已变为后端） |
| 17 | §7.5 硬件 | **新增**：后端本地存储容量规划（如 1TB SSD）；删除原 OSS 按量 |
| 18 | §8.4 可观测性 | 新增"存储后端使用率"指标 |
| 19 | §9 技术约束 | 新增 `StorageBackend` 抽象、`LocalStorageBackend` 默认实现；OSS 列为"扩展后端" |
| 20 | §10.1 验收 | 新增 AC-NEW-V13-001~008（存储相关） |
| 21 | §10.2 非功能 | 新增 NAC-V13-001~003（存储容量、下载延迟、存储故障 RTO） |
| 22 | §11 风险 | 新增"本地存储容量风险"；调整"OSS 不可用" → "存储后端不可用" |
| 23 | §12 发布变更 | 新增"V1.2 → V1.3 存储切换"双轨方案 |
| 24 | §13 Runbook | 新增 RB-STORAGE-BACKEND-SWITCH、RB-STORAGE-DISK-FULL |
| 25 | §14 开放问题 | 新增 V1.3 存储 Q12-Q15 |


### 术语表

| 术语 | 定义 |
|------|------|
| Transaction | 一次完整的保单录入事务，从资料提交到结果回传的全过程。**业务类型（NEW/RENEWAL）由用户在 Web/API 提交时显式指定**，错误指定由用户承担。 |
| Worker | 安装在桌面端的客户端代理，**V1.2 起升级为"编排 + 执行"双重角色**：接收调度指令、编排 RPA 流程，**并通过 Airtest runtime 实际驱动 Android 设备执行 UI 自动化**。 |
| Device | 挂载在 Worker 上的 Android 设备，**V1.2 起降级为"下载器 + ADB 目标"**：仅负责下载输入影像到本地沙箱 + 作为 ADB 控制目标，不再持有 Flow 脚本、不再执行 RPA 步骤。 |
| **Airtest** | **V1.2 新增术语**。开源移动端 UI 自动化框架（基于图像识别 + 控件识别 + ADB），本项目用其驱动 Android 设备 UI 操作。设计哲学为"桌面 Python 控制手机"。 |
| **POCO** | **V1.2 新增术语**。Airtest 配套的跨平台 UI 控件识别库，支持 Android/iOS/Web。本项目用其做 Android 控件树查询与操作。 |
| **ADB** | **V1.2 新增术语**。Android Debug Bridge，Android 官方调试桥。本项目用其做 USB 设备连接、Shell 命令、文件传输。 |
| **adb_serial** | **V1.2 新增字段术语**。Android 设备 USB ADB 序列号，Worker 通过此值连接 ADB。 |
| **sandbox_path** | **V1.2 新增字段术语**。Device 端临时沙箱路径，默认 `/sdcard/sandbox/{txn_id}/`，用于存储下载的输入影像。 |
| **max_concurrent_devices** | **V1.2 新增字段术语**。Worker 端最大并发 Device 数，受 CPU 限制默认为 2-3。 |
| **download-ack** | **V1.2 新增接口术语**。Device 完成输入影像下载后调用 `POST /api/v1/devices/{id}/download-ack` 通知 Worker。 |
| Flow | 一个完整的 RPA 流程定义，由多个有序 Step 组成 |
| FlowVersion | Flow 的版本记录，包含脚本包和参数，支持多版本共存与回滚 |
| Step | Flow 中的单个操作步骤，如"打开APP"、"填写表单"、"上传照片"。**V1.2 起 Step 在 Worker 端 Airtest runtime 中执行** |
| CONFIRM Step | **DEPRECATED**（V1.1 起）。原"用户确认"步骤已废止，由"全自动 + 异步审计"取代。原 StepExecution 中相关字段保留但标 DEPRECATED。 |
| DLQ | Dead Letter Queue，死信队列，用于隔离连续失败的事务 |
| ATT | Average Transaction Time，事务平均执行时长（**仅指 RUNNING 阶段**，不含用户等待）。**V1.2 调整为 5-8 分钟**（新架构 Worker 端 Airtest 执行的预期值）。 |
| SN/UDID | Android 设备序列号/唯一设备标识 |
| Attachment | 事务关联的影像文件，数量不限，用户可自由上传 |
| SLB/CLB | 云负载均衡服务（阿里云 SLB / 腾讯云 CLB） |
| OSS/COS | 云对象存储服务（阿里云 OSS / 腾讯云 COS） |
| OssSignedUrl | **DEPRECATED（V1.3 起）**。**V1.3 之前**的 OSS 对象临时签名 URL 记录。V1.3 起被通用 `DownloadUrl` 实体替代（后端无关的下载凭证），保留表结构不删除以兼容历史引用。 |
| **DownloadUrl（V1.3 新增）** | **通用下载凭证实体**。Backend 生成的临时签名 URL（TTL 5 分钟），供 Device 直连下载。后端实现基于 `StorageBackend.generate_signed_url()`，默认 `LocalStorageBackend` 返回的是 Backend 自身服务的 URL（指向 `/api/v1/downloads/{token}`），未来切换 OSS 后端时自动返回 OSS 签名 URL。生成后由 Backend 通过 `POST /api/v1/transactions/{id}/download-urls` 下发，不经 Worker 中转。 |
| **StorageBackend（V1.3 新增）** | **文件存储后端抽象接口**。统一封装 `put` / `get` / `generate_signed_url` / `delete` / `exists` 等操作。V1.3 默认实现 `LocalStorageBackend`（本地文件系统），未来可扩展 `OssStorageBackend`（阿里云 OSS）、`MinioStorageBackend`（S3 兼容）。后端通过配置选择当前实现，业务代码不感知具体后端。 |
| **LocalStorageBackend（V1.3 新增）** | **本地文件存储后端实现**（V1.3 MVP 默认）。文件存储于 Backend 主机本地文件系统，默认路径 `/data/attachments/{attachment_id}/{filename}`。签名 URL 指向 Backend 自身服务，Device 通过 `GET /api/v1/downloads/{token}` 下载。 |
| **OssStorageBackend（V1.3 新增，中期实现）** | **阿里云 OSS 存储后端实现**。通过阿里云 OSS SDK 封装 `StorageBackend` 接口。签名 URL 由 OSS 生成（5 分钟 TTL），Device 通过 OSS 域名直连下载。 |
| KMS | **新增（V1.1）**。Key Management Service，密钥管理服务。手机号/身份证号等敏感字段加密密钥由 KMS 托管，权限按角色隔离。 |
| RedisStream | **新增（V1.1）**。基于 Redis Stream + Consumer Group 的任务队列。**MVP 必需**，替代原"DB 轮询"作为唯一调度方案。 |
| DPoP | **新增（V1.1）**。Data Principal rights，数据主体权利。PIPL 规定的数据主体查询/更正/删除/导出权利。 |
| **ADB_CONNECTING（V1.2 新增）** | 状态机子状态。Worker 启动 Airtest runtime 并连接 Android 设备 ADB 时的握手阶段。 |
| **READY（V1.2 新增）** | 状态机子状态。Device 下载完成且 Worker 准备执行 Airtest 流程的中间状态。 |

---

## 1. 产品概述

### 1.1 背景

车险投保流程涉及大量影像资料的人工录入（身份证、行驶证、合格证、发票等），耗时长、易出错、人力成本高。

### 1.2 目标

构建分布式、高可用的 RPA 编排平台，实现投保资料的自动化录入与处理，覆盖新保单和续保单两种场景。

### 1.3 价值主张（V1.2 更新）

- 将单笔保单录入时间从人工 15-20 分钟降至自动化 **5-8 分钟**（**V1.2 调整**：Worker 端 Airtest runtime 实际驱动的预期 ATT，原 V1.1 "3-5 分钟"是 Device 端 Airtest 假设下的乐观值）
- 消除人工录入的格式错误和遗漏
- 支持多设备并行处理，线性扩展吞吐量
- 全流程可审计、可追溯
- **V1.2 新增价值（架构调整带来）**：
  - **桌面 IDE 断点调试便利**：Flow 脚本在 Worker 桌面 Python 进程执行，可直接用 PyCharm/VSCode 断点调试，降低 RPA 维护成本
  - **脚本热更新免下发**：Flow 脚本不再下发到 Device，改完直接重启 Worker 即可生效，版本一致性风险归零
  - **Device Agent 极简化**：Device 端不再需要 Airtest runtime，App 包大小从 ~50MB 降至 ~5MB
- **V1.2 重要假设：** "5-8 分钟" **仅指 RUNNING 阶段（Worker 端 Airtest 自动化执行时间）**，**不含**任何用户等待时间。原 V1.0 中的 CONFIRM Step（最长 30 分钟确认等待）已在 V1.1 移除，改为"全自动 + 异步审计"模式。

### 1.4 范围边界

| In Scope | Out of Scope |
|----------|-------------|
| 新保单/续保单的路由分发 | 保单核保与定价逻辑 |
| 影像资料的上传、校验、分发 | 保险公司核心业务系统 |
| 多设备集群调度与负载均衡 | OCR 识别能力（假设外部服务提供，**V1.x 阶段不实现**） |
| **Worker 端 Airtest runtime 执行 UI 自动化（V1.2 新增）** | iOS 设备支持（未来扩展） |
| **ADB 连接管理（USB 物理连接，V1.2 新增）** | 支付/出单环节 |
| 全链路状态监控与审计日志 | 业务类型的智能识别 |
| **业务类型的提交时指定（V1.1 明确）** | **业务类型的智能识别（V2.x 规划）** |
| **单 Worker 限 2-3 Device（V1.2 新增约束）** | **多 Worker 负载均衡（V1.2 由云端调度中心承担）** |
| **文件存储后端可插拔（V1.3 新增）** | **存储后端用户侧不可见（V1.3 由 Backend 抽象）** |

**V1.1 范围说明。** 业务类型（NEW/RENEWAL）由用户在 Web/API 提交事务时显式指定，系统按配置规则路由到对应 Flow。V1.x 不实现自动识别能力（依赖 OCR 等外部服务）。V2.x 规划智能识别能力。

**V1.2 范围补充。** 执行架构从"Device 端 Airtest + Worker 编排"调整为"Worker 端 Airtest + Device 极简化"。由此引入两个新约束：
- **单 Worker 同时挂载的 Device ≤ 3 台**（CPU 瓶颈，Airtest 进程 + 图像处理压力大）
- **单站点推荐配置 2-3 个 Worker，共 4-9 台 Device**（覆盖 500 笔/日的事务量）

**V1.3 范围补充。** 文件存储架构从"OSS-first"翻转为"Server-first"：
- **MVP（V1.3）：** 客户端通过 multipart/form-data 一并上传文件，Backend 落地到本地文件系统（`LocalStorageBackend`）；下载通过 Backend 自身提供的签名 URL 直连（不依赖 OSS）
- **中期（V1.4 规划）：** 可切换为 `OssStorageBackend`（阿里云 OSS）或 `MinioStorageBackend`（S3 兼容），通过配置切换，业务代码不感知
- **存储后端对用户/Worker/Device 透明**：接口契约（`POST /download-urls` 生成的 URL）保持稳定，仅 URL 指向在不同后端下指向不同服务（Backend 自身 / OSS / MinIO）

---

## 2. 用户角色与权限

### 2.1 角色定义

| 角色 | 描述 | 核心操作 |
|------|------|----------|
| 销售人员 | 提交投保资料的业务人员 | 提交保单资料（Web/API）、查看**自有**事务状态 |
| 运维管理员 | 监控系统运行状态的运维人员 | 查看 Dashboard、管理设备池、处理 DLQ 事务 |
| 系统管理员 | 系统配置与权限管理 | 管理用户/角色、配置校验规则、管理 Flow 定义 |
| Worker 节点 | 桌面端客户端代理（系统角色） | **V1.2 升级**：注册/心跳、接收任务、**编排 + 执行**（通过 Airtest runtime 驱动 Android 设备）、上报结果 |
| Android 设备 | 移动端执行代理（系统角色） | **V1.2 降级**：仅下载输入影像（直连 OSS 签名 URL）+ 作为 ADB 控制目标（**不再持有 Flow 脚本、不再执行 RPA 步骤**） |
| **数据主体（V1.1 新增）** | 自然人/投保人 | 通过 DPoP API 查询/更正/删除/导出自身数据 |

### 2.2 权限矩阵

| 操作 | 销售人员 | 运维管理员 | 系统管理员 | Worker | Device | 数据主体 |
|------|:--------:|:----------:|:----------:|:------:|:------:|:--------:|
| 提交保单资料 | Y | Y | Y | - | - | - |
| 查看事务状态（**自有**） | Y | - | - | - | - | - |
| 查看所有事务 | - | Y | Y | - | - | - |
| 管理设备池 | - | Y | Y | - | - | - |
| 处理 DLQ 事务 | - | Y | Y | - | - | - |
| 管理用户/角色 | - | - | Y | - | - | - |
| 配置校验规则 | - | - | Y | - | - | - |
| 管理 Flow 定义 | - | - | Y | - | - | - |
| 注册/心跳 | - | - | - | Y | - | - |
| 接收/执行任务 | - | - | - | Y（**V1.2 升级：编排 + 执行**） | Y（**V1.2 降级：仅下载 + ADB 目标**） | - |
| 下载影像资料 | - | - | - | - | Y | - |
| 查看 Dashboard | - | Y | Y | - | - | - |
| **行使 DPoP 权利（V1.1）** | - | - | Y | - | - | Y |

**行级权限说明（V1.1 新增）。** "查看事务状态"在销售角色下需做行级过滤：销售只能查看 `submitted_by = 当前用户 User ID` 的事务。运维/管理员可查看全部。**禁止**通过 API 参数绕过行级过滤（需对 `submitted_by` 字段做服务端强制覆盖）。

### 2.5 数据合规与隐私（V1.1 新增）

车险影像 + 身份证 + 手机号属于**敏感个人信息**（PIPL 第二十四条），本节明确合规要求。

| 合规章节 | 要求 | 实施要点 |
|----------|------|----------|
| **PIPL 第二十四条** | 处理敏感个人信息需取得单独同意 | 在 Web/API 提交端增加"单独同意"勾选，未勾选拒绝提交 |
| **KMS 密钥管理** | 加密密钥不可硬编码、不可由开发人员持有 | 手机号、身份证号 AES-256 密钥由 KMS 托管；KMS IAM 权限按角色隔离；密钥轮转周期 ≤90 天 |
| **OSS 地域约束**（V1.3 调整为"存储后端地域约束"） | 数据不出境、客户允许的地域范围 | **V1.3 起**：存储后端（无论 LocalStorageBackend 还是 OssStorageBackend）固定在客户指定地域；**V1.3 默认 LocalStorageBackend**：Backend 主机部署在客户指定地域的云上；**V1.4+ OssStorageBackend**：OSS 桶固定在客户指定地域（默认华东 1 / 华北 2），**禁止**跨地域复制到非白名单区域 |
| **《保险法》第二十一条** | 投保数据至少保存 10 年 | Transaction、Attachment 元数据保存期 ≥10 年；影像文件保存期由业务方定（参考区间 3-10 年） |
| **DPoP 数据主体权利** | 查询 / 更正 / 删除 / 导出 | 提供 `POST /api/v1/dpop/{action}` API；删除采用软删除（标记 `dpop_deleted_at`），不物理删除；导出采用打包下载 |
| **审计日志保留** | 合规审查可还原 | 审计日志保留期 ≥180 天（PIPL 推荐），与保险数据保留期分别管理 |

**分阶段策略（V1.1 共识会决议 P5）。**
- **MVP（V1.1）覆盖：** PIPL 第二十四条（单独同意）、KMS 密钥管理、OSS 地域约束、审计日志 180 天
- **中期（V1.2-V1.3）补：** 《保险法》10 年保存、DPoP 完整接口、保险法对应的存储架构变动

**数据加密策略。**
- 传输：全链路 TLS 1.2+
- 存储：手机号、身份证号 AES-256（密钥 KMS 托管）；其他字段明文
- API 响应：脱敏显示（手机号 `138****1234`，身份证号 `310***********1234`）
- 日志：所有结构化日志自动脱敏，禁止打印完整手机号/身份证号


---

## 3. 业务流程

### 3.1 主流程（端到端，V1.2 全自动 + Worker 端 Airtest 模式）

```
销售人员提交资料(指定业务类型, multipart含文件) → [事务接入] → 智能路由(按权重) → Schema校验
    → Backend落地文件到存储后端（V1.3 默认 LocalStorageBackend）
    → 生成Transaction ID + Attachment ID → [调度中心] → 选择Worker+Device
    → 状态: DISPATCHED → Worker接收任务 → 启动Airtest runtime
    → 状态: ADB_CONNECTING (Worker通过USB ADB连接Device)
    → 调用 /download-urls API获取下载URL（V1.3：指向后端自身；V1.4+ OSS 后端：指向 OSS）
    → Socket通知Device下载（Device直连下载源）
    → 状态: DOWNLOADING → 下载完成 → 状态: READY
    → 状态: RUNNING → Worker Airtest执行Step序列
    → 执行完成 → 结果回传
    → 状态: SUCCESS/FAIL → 失败进DLQ运维兜底 → 销售人员查看结果
```

**V1.1 关键变化。**
- 业务类型由用户提交时显式指定，系统不再"智能识别"
- Device 直连下载源（V1.1/V1.2：OSS 签名 URL；V1.3 起：后端内部签名 URL，URL 来源由存储后端决定）
- 全自动执行：失败进 DLQ 运维兜底，**不**在流程中插入用户确认环节

**V1.2 关键变化。**
- **执行位置变更**：RPA 步骤执行从 Device 端迁移到 Worker 端（Airtest runtime）
- **新增 ADB_CONNECTING 子状态**：Worker 通过 USB ADB 连接 Device 的握手阶段
- **新增 READY 子状态**：Device 下载完成且 Worker 准备开始 Airtest 执行的中间点
- **Device 角色降级**：Device 不再持有 Flow 脚本、不再执行 RPA Step，仅负责输入影像下载 + 作为 ADB 目标

**V1.3 关键变化。**
- **文件存储后端 Server-first**：客户端 multipart 一并上传，Backend 落地存储（默认本地）；Device 仍直连下载源（**URL 来源从 OSS 变 Backend 自身**）
- **`StorageBackend` 抽象**：未来切换 OSS/MinIO 不影响业务代码
- **Device 端下载协议不变**：Device 仅感知"按 URL 下载"，URL 指向对 Device 透明

### 3.2 新保单流程

输入资料：影像文件（不限制数量和张数，可能包含身份证、车辆合格证、发票等）、手机号码、业务类型=NEW

```
提交资料(业务类型=NEW) → 校验(至少1份影像+手机号) → 路由至新保Flow
→ Step1: 打开保险APP(Worker Airtest: start_app) → Step2: 选择新保入口
→ Step3: 填写手机号(Worker Airtest: text) → Step4~StepN: 逐张上传影像(Worker Airtest: touch + 文件选择)
→ StepN+1: 提交表单(Worker Airtest: touch) → 状态: SUCCESS
```

**V1.1 移除：** StepN+2 截图等待用户确认(CONFIRM)、StepN+3 确认后提交。

**V1.2 明确：** 所有 Step 在 Worker 端 Airtest runtime 中执行，Device 端仅在 Step 中作为 UI 操作目标（被 Airtest 通过 ADB 驱动）。

### 3.3 续保单流程

输入资料：影像文件（不限制数量和张数，可能包含身份证、行驶证等）、手机号码、业务类型=RENEWAL

```
提交资料(业务类型=RENEWAL) → 校验(至少1份影像+手机号) → 路由至续保Flow
→ Step1: 打开保险APP → Step2: 选择续保入口
→ Step3: 填写手机号 → Step4~StepN: 逐张上传影像
→ StepN+1: 提交表单 → 状态: SUCCESS
```

**V1.1 移除：** StepN+2 截图等待用户确认(CONFIRM)、StepN+3 确认后提交。

### 3.4 状态机（V1.2 扩展：新增 ADB_CONNECTING + READY 子状态）

```
PENDING → DISPATCHED → ADB_CONNECTING → DOWNLOADING → READY → RUNNING → SUCCESS
                                              │                          → FAIL
                                              │                          → RETRY → RUNNING (最多N次)
                                              │                          → DLQ (终态失败，需人工介入)
                                              ↓
                                        (download fail)
                                              → FAIL
```

| 状态 | 触发条件 | 说明 |
|------|----------|------|
| PENDING | 事务创建，校验通过 | 等待调度 |
| DISPATCHED | 调度中心分配 Worker+Device | 任务已下发 |
| **ADB_CONNECTING（V1.2 新增）** | **Worker 启动 Airtest runtime 并连接 Android USB ADB** | **新增**：ADB 握手阶段；失败 → FAIL |
| DOWNLOADING | Device 开始下载影像资料 | 资料传输中 |
| **READY（V1.2 新增）** | **Device 下载完成，Worker 准备执行 Airtest 流程** | **新增**：可选中间点 |
| RUNNING | Worker 端 Airtest 开始执行 Step 序列（**V1.2 调整**：执行位置由 Device 迁至 Worker） | 自动化操作中 |
| SUCCESS | RPA 执行完成，结果验证通过 | 正常终态 |
| FAIL | 执行异常/超时/校验失败 | 可重试 |
| DLQ | 连续失败超过阈值或事务级超时 | 死信队列，需人工介入 |

**V1.1 移除状态：** `WAITING_CONFIRM`。原 CONFIRM 流程已废止，改为"全自动 + 异步审计"（失败进 DLQ 运维处理）。

**V1.1 新增触发：** 事务级超时（30 分钟未到终态）强制进 DLQ，详见 §3.5。

**V1.2 新增触发：**
- **ADB 握手失败**（30s 内未连上 USB ADB）→ FAIL → RETRY → DLQ
- **Airtest runtime 启动失败**（依赖缺失、Python 环境异常）→ FAIL → 运维介入
- **USB 物理断开**（事务执行中）→ 事务回退 PENDING 重新调度

### 3.5 异常分支

- **文件下载失败**：Device 侧断点续传，超过重试次数后状态置为 FAIL
- **RPA 步骤失败**：Step 级重试（按 Retry Policy），全部重试耗尽后事务 FAIL
- **Worker 宕机**：服务端心跳超时检测，事务回退至 PENDING 重新调度
- **Device 离线**：调度中心跳过该设备，重新选择可用设备
- **事务级超时（V1.1 新增）**：单事务从 PENDING 起超过 30 分钟（可配置）未到达终态（SUCCESS/FAIL），强制置为 DLQ；防止事务在 RUNNING 状态挂死占用设备
- **OSS 签名 URL 过期**：Device 端发起续签请求（FR-MOB-006）；过期超过 3 次该事务置为 FAIL
- **ADB 断开重连（V1.2 新增）**：Worker 检测 ADB 连接断开时执行 `adb reconnect offline` 重连；重连成功则继续执行；重连失败则事务回退 PENDING
- **Airtest runtime 失败（V1.2 新增）**：Worker 端 Airtest 进程崩溃或图像识别持续失败 → Step 重试（默认 3 次，指数退避 1s/2s/4s）；超过重试次数 Step 失败截图推 Dashboard（FR-SVR-018）
- **USB 物理断开（V1.2 新增）**：USB 数据线拔出或接触不良 → 运维告警 + 事务回退 PENDING；单 Worker 挂载的所有 Device 事务同时回退
- **Worker 进程崩溃（V1.2 新增）**：Worker 进程崩溃 → 该 Worker 挂载的所有 Device 当前事务回退 PENDING；切换至其他 Worker 重试
- **本地存储磁盘满（V1.3 新增）**：`LocalStorageBackend` 所在磁盘使用率 > 90% → 新事务提交失败返回 507（Insufficient Storage）；运维需清理过期文件或扩容
- **存储后端不可用（V1.3 新增）**：`StorageBackend` 调用失败（V1.3 默认 LocalStorageBackend：磁盘故障 / 文件系统只读；V1.4+ OssStorageBackend：OSS 服务故障）→ 新事务提交失败、已下发事务的下载失败 → 事务 FAIL → 运维切换后端或重试

### 3.6 业务连续性（BCP，V1.1 新增，V1.2 扩展）

| 故障场景 | 业务影响 | 恢复顺序 |
|----------|----------|----------|
| 单 Worker 宕机 | 该 Worker 上的事务回退 PENDING 重新调度 | 自动（≤60s） |
| **Worker 进程崩溃（V1.2 新增）** | **该 Worker 挂载的所有 Device 当前事务（2-3 个）回退 PENDING** | 自动（≤60s） |
| 站点全断（网络/电力） | 该站点所有 Worker 不可用，事务全量回退 PENDING | 自动，调度中心跳过该站点 |
| 云端 Backend 单实例故障 | SLB 自动切流到健康实例 | 自动（≤30s） |
| 云端 Backend 全部故障 | 销售可继续提交（写入 OSS 直传通道），Worker 任务排队等待恢复 | **半自动**：运维确认后人工恢复 |
| 数据库主从切换 | 短时（≤30s）写入失败，事务提交重试 | 自动 |
| OSS 不可用 | 影像上传和下载失败，所有事务 FAIL | **半自动**：运维确认后切备用 OSS 或重试 |
| **存储后端不可用（V1.3 新增，通用）** | **`StorageBackend` 故障（V1.3 默认 LocalStorageBackend：磁盘故障；V1.4+ OssStorageBackend：OSS 不可用）；事务提交 / 文件下载失败** | **半自动**：运维确认后切换后端（如 LocalStorageBackend → OssStorageBackend）或修复存储 |
| **本地存储磁盘满（V1.3 新增）** | **新事务提交失败（507）** | **半自动**：运维清理过期文件 / 扩容磁盘 / 切换后端 |
| KMS 不可用 | 敏感字段加解密失败，所有事务 FAIL | **半自动**：运维确认后重启 KMS Client |
| **ADB 短暂断开（V1.2 新增）** | **当前事务 RUNNING 中断** | **自动**：`adb reconnect offline` 重连，事务继续 |
| **USB 物理断开（V1.2 新增）** | **当前事务 FAIL，运维告警** | **半自动**：运维检查 USB 线材后手动恢复 |

**断电恢复顺序（站点侧）：** Worker 启动 → 自动注册 → 拉取最新 Flow 脚本 → 拉取待执行事务 → 恢复执行（Device 状态需重新校验）。预期从断电到恢复 ≤ 5 分钟（视事务积压量）。


---

## 4. 功能需求

### 4.1 服务端功能（FR-SVR-xxx）

#### FR-SVR-001 销售人员 Web 门户提交（V1.3 改 multipart 上传）

| 字段 | 内容 |
|------|------|
| 描述 | 销售人员通过 Web 表单手动提交单笔保单资料 |
| 输入 | 业务类型（新保/续保）、手机号、身份证号、影像文件（image/pdf，数量不限）；**V1.3 起**：文件通过 multipart/form-data 一并上传（V1.1/V1.2：先传 OSS 再传 file_url） |
| 输出 | Transaction ID、提交时间戳、初始状态 PENDING；**V1.3 新增**：返回每个附件的 `attachment_id` |
| 规则 | 文件大小单张 ≤10MB；图片格式 jpg/png/jpeg；PDF 单文件 ≤20MB；**V1.3 新增**：Backend 通过 `LocalStorageBackend`（默认）/ `OssStorageBackend`（未来）落地存储；multipart 总大小 ≤ 50MB；事务+文件原子性（任一校验失败回滚） |
| 验收 | 提交成功返回 Transaction ID + attachment_id 列表；缺失必填项返回 400 错误且提示具体字段；**V1.3 新增**：存储后端不可用返回 507；事务+文件不一致返回 422 |

#### FR-SVR-002 REST API 批量推送（V1.3 改 multipart 上传）

| 字段 | 内容 |
|------|------|
| 描述 | 第三方系统通过 REST API 批量推送保险人信息 |
| 输入 | 数组形式的保单数据（每条含业务类型、客户信息、影像**multipart 二进制**，**V1.3 起不再使用 file_url**） |
| 输出 | 每条记录对应的 Transaction ID 列表 + attachment_id 列表、失败明细 |
| 规则 | 单次批量 ≤100 条；API 需携带 Bearer Token；幂等性通过外部业务ID保障；**V1.3 新增**：单次请求 multipart 总大小 ≤ 500MB（10 事务 × 50MB）；事务级文件落地原子性 |
| 验收 | 批量提交支持部分成功；失败条目返回原因码；重复 externalId 不重复创建事务；**V1.3 新增**：存储后端不可用时整批 FAIL 并返回 503 |

#### FR-SVR-003 智能业务路由

| 字段 | 内容 |
|------|------|
| 描述 | 根据事务类型和路由规则，将事务分发至对应 Flow 执行，支持按百分比分配 |
| 输入 | 事务类型（**用户提交时显式指定**：NEW 或 RENEWAL）、已配置的路由规则 |
| 输出 | 路由后的事务（绑定对应 Flow ID） |
| 规则 | 每个事务类型可配置多个路由规则（如 NEW 下 Flow A 占 70%、Flow B 占 30%）；路由规则按权重百分比随机分配；支持按 Flow 版本分配；**事务类型由用户在提交时显式指定，错误指定由用户承担，系统不做自动识别** |
| 验收 | 用户提交时指定事务类型后，系统正确分配对应 Flow；权重分配在大量事务下符合配置比例（偏差 ≤5%） |

#### FR-SVR-004 Schema 校验

| 字段 | 内容 |
|------|------|
| 描述 | 根据业务类型动态加载 JSON Schema 校验输入数据 |
| 输入 | 事务数据、对应 Schema 定义 |
| 输出 | 校验通过/失败结果、失败明细 |
| 规则 | Schema 校验字段完整性（手机号格式、文件格式合法性），不校验文件数量和具体类型组合；Schema 配置化（YAML/JSON），支持热更新；校验失败不消耗调度资源 |
| 验收 | 校验失败的事务不进入调度队列；规则变更无需重启服务 |

#### FR-SVR-005 Transaction ID 生成

| 字段 | 内容 |
|------|------|
| 描述 | 为每个事务生成全局唯一 ID，贯穿所有服务调用 |
| 输入 | 无（系统自动生成） |
| 输出 | 全局唯一 ID（UUID v7 或 Snowflake ID） |
| 规则 | 单调递增；包含时间戳信息；长度 ≤32 字符 |
| 验收 | 100 万次生成无冲突；分布式环境下唯一性保障 |

#### FR-SVR-006 智能负载均衡调度

| 字段 | 内容 |
|------|------|
| 描述 | 调度中心根据 Worker 性能和设备空闲率分配任务 |
| 输入 | 待调度事务、Worker 列表（含CPU/内存/挂载设备数）、Device 状态 |
| 输出 | 分配结果（Transaction ID → Worker ID + Device ID） |
| 规则 | 算法：最小连接数 + 权重轮询；**V1.2 新增**：不分配给 `current_device_count >= max_concurrent_devices` 的 Worker |
| 验收 | 1000 笔事务调度后，Worker 间负载偏差 ≤15% |

#### FR-SVR-007 设备亲和性策略

| 字段 | 内容 |
|------|------|
| 描述 | 同一事务的所有步骤优先在固定设备上执行 |
| 输入 | Transaction ID、绑定的 Device ID |
| 输出 | 后续 Step 调度时优先使用同一 Device |
| 规则 | 绑定设备宕机时才允许重新调度；重新调度时从 Step1 开始 |
| 验收 | 正常情况下事务全程不切换设备；设备故障切换后状态正确重置 |

#### FR-SVR-008 状态机管理

| 字段 | 内容 |
|------|------|
| 描述 | 维护事务状态强一致性流转，记录每次变更 |
| 输入 | 状态变更事件（来自 Worker/Device 上报） |
| 输出 | 持久化的状态变更记录（含时间戳、操作者、原状态、新状态） |
| 规则 | 禁止非法状态跳转（如 PENDING 直接到 SUCCESS）；变更操作幂等；**V1.2 新增状态**：`ADB_CONNECTING`、`READY` |
| 验收 | 状态流转 100% 符合定义；非法变更被拒绝并记录告警 |

#### FR-SVR-009 客户端注册中心

| 字段 | 内容 |
|------|------|
| 描述 | 管理 Worker 节点的注册、心跳、版本、能力标签 |
| 输入 | Worker 注册请求（含本机指纹、版本号、Tag）、心跳包 |
| 输出 | 注册确认、Worker 列表查询接口 |
| 规则 | 心跳周期 ≤30s；连续 3 次未收到心跳标记为 OFFLINE；**V1.2 新增**：Worker 注册时上报 `max_concurrent_devices` 能力 |
| 验收 | Worker 上下线状态实时更新；OFFLINE 后任务自动回收 |

#### FR-SVR-010 设备池管理

| 字段 | 内容 |
|------|------|
| 描述 | 维护 Android 设备的唯一标识、在线状态、占用情况 |
| 输入 | Worker 上报的设备列表（含 SN/UDID、电量、存储、**adb_serial**（V1.2 新增）） |
| 输出 | 设备池视图（含状态、当前事务） |
| 规则 | 同一 SN 全系统唯一；支持手动禁用设备 |
| 验收 | 设备状态变更延迟 ≤5s；禁用设备不再被调度 |

#### FR-SVR-011 审计日志

| 字段 | 内容 |
|------|------|
| 描述 | 全量记录事务操作、异常堆栈、调度决策 |
| 输入 | 系统各模块的操作事件 |
| 输出 | 结构化日志（JSON 格式），可检索、可导出 |
| 规则 | 日志保留 ≥180 天；敏感字段脱敏（身份证号、手机号） |
| 验收 | 任一事务的完整生命周期可还原；日志查询响应 ≤2s |

#### FR-SVR-012 Dashboard 监控

| 字段 | 内容 |
|------|------|
| 描述 | 提供可视化监控看板 |
| 输入 | 系统运行数据 |
| 输出 | 实时展示：事务积压量、设备在线率、脚本成功率、ATT |
| 规则 | 数据刷新间隔 ≤30s；支持按时间范围/Worker/Device 筛选；**V1.2 新增**：Worker CPU 使用率面板（用于监控单 Worker 多 Device 负载） |
| 验收 | 关键指标可视化展示；支持告警阈值配置 |

#### FR-SVR-013 死信队列处理

| 字段 | 内容 |
|------|------|
| 描述 | 隔离连续失败的事务，支持人工介入 |
| 输入 | 连续失败次数 ≥N（可配置，默认 3 次）的事务 |
| 输出 | DLQ 列表、人工重试/丢弃接口 |
| 规则 | DLQ 事务不自动重试；运维可查看失败原因、重新提交或归档 |
| 验收 | DLQ 事务可单独管理；重新提交后回到正常流程 |

#### FR-SVR-014 用户确认通知

**【DEPRECATED，V1.1 起】** 已被全自动模式取代，移除相关实现。保留编号占位以兼容历史引用。

#### FR-SVR-015 用户确认回调

**【DEPRECATED，V1.1 起】** 同上，移除实现。

#### FR-SVR-016 流程脚本上传

| 字段 | 内容 |
|------|------|
| 描述 | 管理员通过 Web 门户或 API 上传 Airtest Python 脚本包（.zip/.py），并设置流程参数 |
| 输入 | Flow ID、脚本包文件、流程参数（JSON，如 APP 包名、等待超时等）、版本说明 |
| 输出 | 新版本号、脚本包存储路径 |
| 规则 | 脚本包单文件 ≤50MB；仅允许 .py/.zip 格式；上传时自动进行语法校验（`python -m py_compile`）；参数与 Schema 校验一致；每次上传自动递增版本号 |
| 验收 | 上传成功返回版本号；语法错误脚本拒绝上传并返回错误行号；参数缺失时提示补全 |

#### FR-SVR-017 流程版本管理

| 字段 | 内容 |
|------|------|
| 描述 | 管理 Flow 的多版本生命周期，支持发布、回滚、停用 |
| 输入 | Flow ID、版本号、操作类型（publish/rollback/deprecate） |
| 输出 | 操作结果、当前生效版本号 |
| 规则 | 同一 Flow 同时仅一个"已发布"版本；回滚操作将指定旧版本重新设为已发布；已停用版本不再分发给 Worker；版本号格式 semver（如 1.0.0 → 1.0.1） |
| 验收 | 发布后 Worker 可拉取到新版本；回滚后生效版本正确切换；停用版本不被调度使用 |

#### FR-SVR-018 异常截图推送（V1.1 新增）

| 字段 | 内容 |
|------|------|
| 描述 | RPA 执行失败时，将失败现场截图推送至运维 Dashboard，供事后审计 |
| 输入 | Transaction ID、Step execution ID、截图 URL、失败原因 |
| 输出 | 推送确认 |
| 规则 | 失败重试耗尽后自动推送；截图保留 30 天；推送去重（同一事务同一步骤失败只推一次） |
| 验收 | 失败事务在 Dashboard 30s 内可见；运维可按事务 ID 还原失败现场 |

#### FR-SVR-019 失败回滚（V1.1 新增）

| 字段 | 内容 |
|------|------|
| 描述 | 事务执行失败时，触发关联资源的回滚操作（如已上传的影像、已填写的表单） |
| 输入 | Transaction ID、失败 Step ID、已操作资源列表 |
| 输出 | 回滚结果 |
| 规则 | 回滚采用"软回滚"（标记 + 清理任务），不阻塞当前流程；回滚失败进人工队列 |
| 验收 | 失败事务的关联影像在 5 分钟内被清理；Dashboard 显示回滚状态 |

#### FR-SVR-020 异步审计日志（V1.1 新增）

| 字段 | 内容 |
|------|------|
| 描述 | 全量记录事务操作、状态变更、调度决策，异步写入审计存储 |
| 输入 | 系统各模块的操作事件（结构化事件流） |
| 输出 | 持久化的审计日志（JSON 格式） |
| 规则 | 异步写入（不阻塞主流程，事件丢失容忍度 ≤1%）；日志保留 ≥180 天；敏感字段自动脱敏 |
| 验收 | 任一事务的完整生命周期可还原；日志查询响应 ≤2s；事件丢失率 < 1% |

#### FR-SVR-021 全自动模式开关（V1.1 新增）

| 字段 | 内容 |
|------|------|
| 描述 | 系统提供"全自动模式"开关，可在 Flow 级别启用/禁用 |
| 输入 | Flow ID、开关状态（enabled/disabled） |
| 输出 | 配置结果 |
| 规则 | 默认全部 enabled；禁用后该 Flow 的事务仍可执行但失败率高时**不**自动重试，直接进 DLQ（人工兜底） |
| 验收 | 开关变更实时生效；配置变更记录审计日志 |

#### FR-SVR-022 ADB 连接状态上报（V1.2 新增）

| 字段 | 内容 |
|------|------|
| 描述 | Worker 上报与 Android Device 的 ADB 连接状态变更 |
| 输入 | Worker ID、Device ID、ADB 状态（CONNECTED / DISCONNECTED / RECONNECTING） |
| 输出 | 接收确认 |
| 规则 | ADB 状态变化时立即上报；连续 3 次心跳未上报视为 USB 物理断开 |
| 验收 | Dashboard 30s 内可见 ADB 状态变化；DISCONNECTED 触发事务回退 |


### 4.2 客户端功能（FR-CLI-xxx）

#### FR-CLI-001 自动注册

| 字段 | 内容 |
|------|------|
| 描述 | 客户端启动时向服务端注册 |
| 输入 | 本机指纹（MAC/主机名/CPU序列号哈希）、版本号、已连接 Android 设备列表（含每台的 `adb_serial`，V1.2 新增） |
| 输出 | 服务端返回的 Worker ID、Token |
| 规则 | Token 有效期 24h，自动续期；注册失败重试 3 次后退出 |
| 验收 | 首次启动注册成功；重启后保持原 Worker ID |

#### FR-CLI-002 状态同步

| 字段 | 内容 |
|------|------|
| 描述 | 周期性上报本机及挂载设备的健康度 |
| 输入 | 本机 CPU/内存/磁盘、设备电量/存储/锁屏状态、**ADB 连接状态（V1.2 新增）** |
| 输出 | 心跳包（含上述指标） |
| 规则 | 心跳间隔 30s；指标异常（如设备电量<20%）触发告警；心跳包中携带本地已缓存 Flow 版本信息，服务端据此判断是否有新版本需要下载；**V1.2 新增**：心跳包上报当前挂载 Device 数（≤ max_concurrent_devices） |
| 验收 | 服务端 Dashboard 实时反映客户端状态；服务端响应心跳中携带"有更新"标记，Worker 据此触发脚本下载 |

#### FR-CLI-003 指令监听

| 字段 | 内容 |
|------|------|
| 描述 | 实时接收服务端下发的任务指令 |
| 输入 | 服务端推送的任务消息 |
| 输出 | 任务接收确认 |
| 规则 | 优先使用 WebSocket；断线降级为长轮询；断线自动重连 |
| 验收 | 任务下发延迟 ≤1s；断网恢复后自动重新订阅 |

#### FR-CLI-004 数据拉取

**【DEPRECATED，V1.1 起】** 影像文件下载已迁移至 Device 直连 OSS 签名 URL（FR-MOB-002 / FR-MOB-006）。Worker 不再持有影像字节流。本条仅作为历史引用保留，新实现不得参考。

#### FR-CLI-004-Note（V1.1 替代方案，V1.2 更新）

**V1.1 替代方案。** Worker 接到任务后只做以下动作：
1. 调用 `POST /api/v1/transactions/{id}/download-urls`（V1.3 重命名自 oss-urls）获取下载 URL 列表（详见 §6.2.1）
2. 通过 Socket 将 URL 列表下发给 Device
3. 等待 Device 上报下载完成事件，进入 RUNNING 状态

Worker **不**再下载文件到本地沙箱、不再 AES-256 加密影像、不再通过 Socket 推送给 Device。

**V1.2 更新。** Worker 接到任务后执行以下动作：
1. 调用 `POST /api/v1/transactions/{id}/oss-urls`（**V1.3 重命名为 `/download-urls`**）获取下载 URL 列表（V1.3 默认指向后端自身；V1.4+ 可切 OSS）
2. 启动 Airtest runtime：`connect_device("android:///{adb_serial}")`
3. 通过 Socket :8765 将 URL 列表下发给 Device（**V1.3 默认** Device 直连后端下载；V1.4+ 可切 OSS；都不经 Worker 中转）
4. 等待 Device 通过 `POST /api/v1/devices/{id}/download-ack` 上报下载完成，进入 READY 状态
5. 按 Step 顺序执行 Airtest API（详见 FR-CLI-005）

#### FR-CLI-005 RPA 编排 + 执行器（V1.2 升级：从"编排"升级为"编排 + 执行"）

| 字段 | 内容 |
|------|------|
| 描述 | 编排 Flow → Steps 的执行流程，**V1.2 起 Worker 端通过 Airtest runtime 实际执行所有 Step** |
| 输入 | Flow 定义（含 Steps 顺序、参数、Retry Policy） |
| 输出 | 各 Step 的执行结果、最终事务结果 |
| 规则 | 支持 Step 级重试（默认 3 次，指数退避）；支持 Step 超时熔断（默认 60s/Step）；**V1.1 移除 CONFIRM Step 特殊处理**（遇到 CONFIRM 类型 Step 直接按普通 Step 执行，依赖 FR-SVR-018 失败截图兜底）；**V1.2 新增**：执行 Step.action_type → Airtest API 映射（OPEN_APP → start_app、INPUT → text、UPLOAD → touch(template) + 系统文件选择、CLICK → touch((x,y)) 或 touch(template)、SCREENSHOT → snapshot()、WAIT → sleep() 或 wait(template, timeout=)） |
| 验收 | Flow 按定义顺序执行；任一 Step 失败触发重试；超时不阻塞整体流程；CONFIRM Step 退化为普通 Step 不再暂停；**V1.2 新增**：100% Step 在 Worker 端 Airtest runtime 中执行，Device 端不执行任何 RPA 步骤 |

#### FR-CLI-006 结果回传

| 字段 | 内容 |
|------|------|
| 描述 | 执行完毕后向服务端上报结果 |
| 输入 | 事务执行结果、**Airtest 截图证据（V1.2 新增：来自 Worker 本地沙箱）**、各 Step 耗时 |
| 输出 | 服务端确认回传 |
| 规则 | 回传失败重试 5 次；截图压缩后上传（JPEG quality 70）；**V1.2 新增**：截图存储于 `~/.3is-auto/sandbox/{txn_id}/screenshots/`，仅供审计，不含输入影像 |
| 验收 | 服务端可查询到完整执行记录和截图；上报延迟 ≤5s |

#### FR-CLI-007 流程脚本同步

| 字段 | 内容 |
|------|------|
| 描述 | Worker 根据需要从服务端下载有效的 Flow 脚本并本地存储，检测到新版本时提示更新 |
| 输入 | Worker 已注册的 Flow 列表、本地已缓存版本 |
| 输出 | 下载的脚本包、本地存储路径 |
| 规则 | 启动时和服务端校验本地已缓存 Flow 版本；若有新版本则下载并替换本地脚本；本地脚本仅供当前 Worker 使用，目录权限 700；支持增量更新（仅下载版本差异部分）；无新版本时不重复下载；**V1.2 新增**：脚本不再下发到 Device，Device 不持有任何 Flow 脚本 |
| 验收 | 新版本发布后 Worker 在下次心跳前检测到差异；下载完成后本地脚本立即可用；旧版本脚本在更新前保留备份（.bak）；**V1.2 新增**：Worker 重启即加载新脚本（无需下发到 Device） |

### 4.3 移动端功能（FR-MOB-xxx，V1.2 全部重写）

> **V1.2 重大变更。** V1.1 中 Device 端承担"RPA 执行 + 文件下载"双重角色，V1.2 起 Device 端**仅承担"输入影像下载 + ADB 目标"角色**。RPA 步骤执行整体迁移至 Worker 端 Airtest runtime（详见 FR-CLI-005）。下方 6 个需求按 V1.2 新职责重写，旧 V1.1 描述保留为 DEPRECATED 引用。

#### FR-MOB-001 任务监听（V1.2 角色变更）

| 字段 | 内容 |
|------|------|
| 描述 | Android Agent 监听 Worker 通过局域网 Socket 下发的下载指令 |
| 输入 | 指令消息（Socket :8765） |
| 输出 | 指令接收确认 |
| 规则 | 监听端口可配置（默认 8765）；仅接受白名单 IP 连接（V1.1 不变） |
| 验收 | 指令接收延迟 ≤1s；非白名单连接被拒绝 |

**【DEPRECATED，V1.2 起】** 旧 V1.1 描述：Android Agent 监听桌面客户端或服务端的指令（含 RPA Step 执行指令 EXECUTE_STEP）。**V1.2 起 EXECUTE_STEP 指令被移除**，Device 不再接收 Step 执行指令。

#### FR-MOB-002 文件同步（V1.2 简化，V1.3 通用化）

| 字段 | 内容 |
|------|------|
| 描述 | 根据 Transaction ID 从 **下载 URL**（V1.3：后端内部 URL；V1.4+ OSS 后端：OSS 签名 URL）下载输入影像到 Device 本地沙箱（**Device 仍直连下载源，不经 Worker**） |
| 输入 | Transaction ID、下载 URL 列表（含 MD5、storage_backend 标识） |
| 输出 | 本地沙箱中的文件（默认 `/sdcard/sandbox/{txn_id}/`） |
| 规则 | 直连下载 URL（**V1.3 默认指向 Backend 自身**；V1.4+ 可指向 OSS / MinIO）；支持断点续传（HTTP Range）；下载完成后做 MD5 校验；存储路径可配置；URL 过期（默认 5min）自动调用续签接口 `POST /api/v1/downloads/{url_id}/refresh` |
| 验收 | 文件 100% 完整下载；网络中断后可恢复；MD5 不匹配自动重新下载；URL 过期自动续签 ≤3 次 |

**【DEPRECATED，V1.2 起】** 旧 V1.1 描述：Device 下载文件供 Worker 端 RPA 使用。**V1.2 起文件用途调整**：下载到 Device 沙箱的输入影像供**目标保险 APP** 读取（被 Worker 端 Airtest 通过 UI 操作触发文件选择器时使用），Worker 不再直接读取 Device 沙箱文件。

#### FR-MOB-003 状态上报（V1.2 重写：原"环境准备"已废止）

| 字段 | 内容 |
|------|------|
| 描述 | Device 向 Backend 上报下载完成、ADB 连接状态变更等 |
| 输入 | 状态变更事件（下载完成、ADB 状态） |
| 输出 | 状态上报确认 |
| 规则 | 启动时调用 `POST /api/v1/devices/{id}/ready` 上报就绪；下载完成调用 `POST /api/v1/devices/{id}/download-ack` 通知 Worker；ADB 状态变化调用 `POST /api/v1/devices/{id}/status` |
| 验收 | 状态变更可被服务端感知；上报延迟 ≤2s |

**【DEPRECATED，V1.2 起】** 旧 V1.1 描述：下载完成后唤醒 RPA 脚本执行环境（Airtest Android Runtime）。**V1.2 起该需求作废**：Airtest runtime 已迁移至 Worker 端，Device 不再需要唤醒任何 RPA 脚本执行环境。

#### FR-MOB-004 沙箱机制（V1.2 简化）

| 字段 | 内容 |
|------|------|
| 描述 | 输入影像仅存储在指定临时目录，事务完成后由 Worker 触发清理 |
| 输入 | 下载完成事件 |
| 输出 | 受控目录中的文件 |
| 规则 | 目录路径 `/sdcard/sandbox/{txn_id}/`（V1.2 默认值）；权限按 Android 文件系统规范配置；事务完成后由 Worker 通过 `adb shell rm -rf /sdcard/sandbox/{txn_id}` 清理 |
| 验收 | 目标保险 APP 可正常读取沙箱中的输入影像；其他应用无权访问；事务完成后沙箱文件被清理 |

**【DEPRECATED，V1.2 起】** 旧 V1.1 描述：影像文件通过 Android FileProvider 暴露给目标保险 APP；其他应用通过 FileProvider 访问。**V1.2 起简化为纯本地目录**，不再需要 FileProvider 配置（V1.1 的 FileProvider 复杂度已无必要）。

#### FR-MOB-005 清理策略（V1.2 调整为被动清理）

| 字段 | 内容 |
|------|------|
| 描述 | Device 端**不再主动清理**沙箱文件，由 Worker 在事务终态后通过 ADB 触发清理 |
| 输入 | Worker 下发的 ADB Shell 清理命令（事务终态后） |
| 输出 | 沙箱文件已删除确认（Device 上报） |
| 规则 | Worker 端事务终态后执行 `adb shell rm -rf /sdcard/sandbox/{txn_id}`；Device 端无需独立清理逻辑 |
| 验收 | 事务完成后 Device 沙箱文件被清理；日志记录清理操作 |

**【DEPRECATED，V1.2 起】** 旧 V1.1 描述：Device 主动清理沙箱（SUCCESS 立即清理、FAIL 保留 24h、DLQ 保留 7 天）。**V1.2 起 Device 不再做主动清理策略**，完全由 Worker 通过 ADB 触发；这样简化 Device Agent 逻辑，避免 Device 端"忘记清理"导致磁盘膨胀。

#### FR-MOB-006 OSS 签名 URL 处理与刷新（V1.1 新增，V1.2 保留）

| 字段 | 内容 |
|------|------|
| 描述 | Device 接收 OSS 签名 URL 列表，下载过程中处理 URL 过期、续签、失败重试 |
| 输入 | OSS 签名 URL 列表（含 TTL、MD5） |
| 输出 | 本地下载完成的文件 |
| 规则 | 签名 URL TTL ≤5min（Backend 控制）；过期前 1min 主动续签；过期后 3 次重试失败该事务置 FAIL；下载全过程通过 §6.2.3 设备接口与 Backend 同步状态 |
| 验收 | 签名 URL 过期自动续签成功；连续 3 次续签失败事务置 FAIL；下载过程 Backend 端状态实时更新 |


---

## 5. 数据模型设计

### 5.1 核心实体清单

| 实体 | 描述 |
|------|------|
| Transaction | 事务主体，记录一次完整保单录入 |
| User | 用户（销售/运维/管理员） |
| Role | 角色与权限 |
| Worker | 桌面客户端节点 |
| Device | Android 设备 |
| Flow | RPA 流程定义 |
| FlowVersion | Flow 的版本记录（含脚本包） |
| Step | Flow 中的步骤定义 |
| StepExecution | Step 执行记录 |
| Attachment | 影像附件 |
| AuditLog | 审计日志 |
| StateTransition | 状态变更记录 |
| RouteRule | 事务类型到 Flow 的路由规则，支持按百分比分配 |
| OssSignedUrl | **V1.1 新增，V1.3 起 DEPRECATED**。OSS 对象临时签名 URL 记录；V1.3 起被 `DownloadUrl` 替代 |
| **DownloadUrl** | **V1.3 新增**。通用下载凭证（后端无关）；通过 `StorageBackend.generate_signed_url()` 生成，V1.3 默认 `LocalStorageBackend` 返回 Backend 自身 URL |
| **StorageBackend 配置** | **V1.3 新增**。系统级配置项（YAML），指定当前激活的存储后端实现（`local` / `oss` / `minio`）；运行时可通过热更新切换 |

### 5.2 实体字段定义

#### Transaction（事务）

| 字段 | 类型 | 说明 |
|------|------|------|
| transaction_id | String(32) PK | 全局唯一 ID |
| external_id | String(64) | 外部业务 ID（幂等用） |
| transaction_type | String(64) | 用户提交时指定的事务类型（如 RENEWAL/NEW），由路由规则映射到 Flow |
| business_type | Enum | NEW（新保）/ RENEWAL（续保）|
| status | Enum | PENDING/DISPATCHED/**ADB_CONNECTING（V1.2 新增）**/DOWNLOADING/**READY（V1.2 新增）**/RUNNING/SUCCESS/FAIL/DLQ |
| customer_phone | String(11) | 手机号（加密存储） |
| customer_id_no | String(18) | 身份证号（加密存储） |
| submitted_by | String | 提交人 User ID |
| submitted_at | DateTime | 提交时间 |
| flow_id | String FK | 关联 Flow |
| worker_id | String FK | 分配的 Worker |
| device_id | String FK | 分配的 Device |
| retry_count | Int | 重试次数 |
| started_at | DateTime | 开始执行时间 |
| finished_at | DateTime | 完成时间 |
| duration_ms | Long | 总耗时（毫秒） |
| failure_reason | Text | 失败原因 |
| ~~callback_url~~ | ~~String(512)~~ | **DEPRECATED (V1.1)**：CONFIRM Step 移除后无意义。保留字段不删除以兼容历史数据。 |

#### User（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | String PK | 用户 ID |
| username | String(64) UK | 用户名 |
| password_hash | String | 密码哈希（bcrypt） |
| role_id | String FK | 角色 ID |
| email | String(128) | 邮箱 |
| status | Enum | ACTIVE/DISABLED |
| created_at | DateTime | 创建时间 |

#### Role（角色）

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | String PK | 角色 ID |
| role_name | String(64) UK | 角色名 |
| permissions | JSON | 权限列表 |

#### Worker（桌面节点，V1.2 增 `max_concurrent_devices`）

| 字段 | 类型 | 说明 | 变更 |
|------|------|------|------|
| worker_id | String PK | Worker 唯一 ID | 不变 |
| fingerprint | String(64) UK | 本机指纹哈希 | 不变 |
| hostname | String | 主机名 | 不变 |
| ip_address | String | IP 地址 | 不变 |
| version | String | 客户端版本 | 不变 |
| tags | JSON | 能力标签 | 不变 |
| cpu_usage | Float | CPU 使用率 | 不变 |
| memory_usage | Float | 内存使用率 | 不变 |
| **max_concurrent_devices** | **Int** | **最大并发 Device 数（V1.2 新增；默认 3，受 CPU 限制）** | **新增** |
| **current_device_count** | **Int** | **当前挂载 Device 数（V1.2 新增，从心跳包更新）** | **新增** |
| status | Enum | ONLINE/OFFLINE/BUSY | 不变 |
| last_heartbeat_at | DateTime | 最后心跳时间 | 不变 |
| registered_at | DateTime | 注册时间 | 不变 |

#### Device（Android 设备，V1.2 增 `adb_serial` + `sandbox_path` + `adb_status`）

| 字段 | 类型 | 说明 | 变更 |
|------|------|------|------|
| device_id | String PK | Device 唯一 ID | 不变 |
| sn | String(64) UK | 设备 SN/UDID | 不变 |
| worker_id | String FK | 挂载的 Worker | 不变 |
| **adb_serial** | **String** | **ADB 序列号（V1.2 新增；Worker 通过此值连接 ADB）** | **新增** |
| **sandbox_path** | **String** | **临时沙箱路径（V1.2 新增；默认 `/sdcard/sandbox/{txn_id}/`）** | **新增** |
| model | String | 设备型号 | 不变 |
| android_version | String | Android 版本 | 不变 |
| battery_level | Int | 电量（0-100） | 不变 |
| storage_free_mb | Int | 剩余存储（MB） | 不变 |
| screen_locked | Boolean | 是否锁屏 | 不变 |
| status | Enum | ONLINE/OFFLINE/BUSY/DISABLED | 不变 |
| current_transaction_id | String | 当前占用事务 | 不变 |
| **adb_status** | **Enum** | **ADB 连接状态（V1.2 新增；CONNECTED / DISCONNECTED / RECONNECTING）** | **新增** |
| last_seen_at | DateTime | 最后一次状态上报时间（V1.1 新增） | 不变 |

#### Flow（流程定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| flow_id | String PK | Flow ID |
| flow_name | String(64) | Flow 名称 |
| business_type | Enum | NEW/RENEWAL |
| current_version | String | 当前已发布版本号（指向 FlowVersion.version） |
| schema | JSON | 输入校验 Schema |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

#### FlowVersion（流程版本）

| 字段 | 类型 | 说明 |
|------|------|------|
| version_id | String PK | 版本记录 ID（UUID） |
| flow_id | String FK | 所属 Flow |
| version | String | 版本号（semver，如 1.0.0） |
| script_path | String | 脚本包存储路径（**V1.3 起通过 `StorageBackend` 存储**；V1.3 默认 `local://flows/{flow_id}/{version}/script.zip`） |
| script_md5 | String(32) | 脚本包 MD5 |
| params_schema | JSON | 流程参数 Schema（描述预期参数结构） |
| params_example | JSON | 参数示例值 |
| changelog | String(512) | 版本变更说明 |
| status | Enum | DRAFT/PUBLISHED/DEPRECATED |
| created_by | String | 创建人 User ID |
| created_at | DateTime | 创建时间 |
| published_at | DateTime | 发布时间（DRAFT 时为空） |

#### Step（步骤定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| step_id | String PK | Step ID |
| flow_id | String FK | 所属 Flow |
| order | Int | 执行顺序 |
| step_name | String(64) | 步骤名称 |
| action_type | Enum | OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/CONFIRM/WAIT（**V1.2 调整**：执行位置由 Device 迁至 Worker，类型不变但语义明确为"Worker Airtest API 触发"） |
| params | JSON | 步骤参数 |
| retry_policy | JSON | 重试策略 |
| timeout_ms | Int | 超时时间 |
| ~~confirm_timeout_ms~~ | ~~Int~~ | **DEPRECATED (V1.1)**：CONFIRM Step 移除后无意义。保留字段不删除以兼容历史数据。 |
| ~~confirm_prompt~~ | ~~String(256)~~ | **DEPRECATED (V1.1)**：同上。 |

#### StepExecution（步骤执行记录，V1.2 增 `executor`）

| 字段 | 类型 | 说明 |
|------|------|------|
| execution_id | String PK | 执行记录 ID |
| transaction_id | String FK | 关联事务 |
| step_id | String FK | 关联 Step |
| attempt | Int | 第几次尝试 |
| status | Enum | RUNNING/SUCCESS/FAIL/TIMEOUT |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 完成时间 |
| duration_ms | Long | 耗时 |
| screenshot_url | String | 截图存储路径 |
| **executor** | **Enum** | **执行者（V1.2 新增；WORKER / DEVICE）；V1.2 起固定为 WORKER** | **新增** |
| error_message | Text | 错误信息 |
| ~~confirm_status~~ | ~~Enum~~ | **DEPRECATED (V1.1)**：PENDING/CONFIRMED/REJECTED/TIMEOUT。CONFIRM Step 移除后无意义。保留字段不删除以兼容历史数据。 |
| ~~confirm_screenshot_url~~ | ~~String~~ | **DEPRECATED (V1.1)**：同上。V1.1 起失败截图统一由 FR-SVR-018 异常截图推送处理。 |
| ~~confirmed_by~~ | ~~String~~ | **DEPRECATED (V1.1)**：同上。 |
| ~~confirmed_at~~ | ~~DateTime~~ | **DEPRECATED (V1.1)**：同上。 |

#### Attachment（附件，V1.3 调整）

| 字段 | 类型 | 说明 | 变更 |
|------|------|------|------|
| attachment_id | String PK | 附件 ID | 不变 |
| transaction_id | String FK | 关联事务 | 不变 |
| file_type | Enum | ID_CARD/DRIVING_LICENSE/CERTIFICATE/INVOICE/OTHER | 不变 |
| description | String(128) | 用户对文件的描述/标签（如"身份证正反面合一"） | 不变 |
| file_format | Enum | JPG/PNG/PDF | 不变 |
| file_size | Long | 文件大小（字节） | 不变 |
| **storage_backend** | **Enum** | **存储后端类型（V1.3 新增；`local` / `oss` / `minio`；V1.3 MVP 默认 `local`）** | **新增** |
| **storage_path** | **String(512)** | **存储后端路径（V1.3 新增；如 `local://attachments/ATT-xxx/idcard.jpg` 或 `oss://bucket/key`）** | **新增（重命名自 storage_url）** |
| ~~storage_url~~ | ~~String~~ | **DEPRECATED (V1.3)**：V1.1/V1.2 用"OSS 路径"语义；V1.3 起被 `storage_backend` + `storage_path` 替代；保留字段以兼容历史数据 | **DEPRECATED** |
| md5 | String(32) | 文件 MD5 | 不变 |
| uploaded_at | DateTime | 上传时间（V1.3 起：事务提交时间 + 文件落地时间） | 不变 |

#### DownloadUrl（V1.3 新增，取代 OssSignedUrl）

| 字段 | 类型 | 说明 |
|------|------|------|
| url_id | String PK | 下载 URL 记录 ID（UUID） |
| transaction_id | String FK | 关联事务 |
| attachment_id | String FK | 关联附件（指向具体存储后端对象） |
| **signed_url** | **String(1024)** | **签名 URL（V1.3 通用化）：V1.3 默认 `LocalStorageBackend` 时指向 Backend 自身的 `GET /api/v1/downloads/{url_id}`；V1.4+ 切换 `OssStorageBackend` 时指向 OSS 签名 URL。Device 不感知差异。** |
| expires_at | DateTime | 过期时间（生成时 + 5min） |
| created_at | DateTime | 创建时间 |
| consumed_at | DateTime | 消费时间（Device 下载完成时间，可空） |
| refresh_count | Int | 续签次数（默认 0，超过 3 该事务置 FAIL） |
| **storage_backend** | **Enum** | **生成此 URL 的存储后端（V1.3 新增；`local` / `oss` / `minio`）** |

#### OssSignedUrl（V1.1 新增，V1.3 DEPRECATED）

| 字段 | 类型 | 说明 |
|------|------|------|
| signed_url_id | String PK | 签名 URL 记录 ID（UUID） |
| transaction_id | String FK | 关联事务 |
| attachment_id | String FK | 关联附件（指向具体 OSS 对象） |
| url | String(1024) | OSS 签名 URL（含签名参数） |
| expires_at | DateTime | 过期时间（生成时 + 5min） |
| created_at | DateTime | 创建时间 |
| consumed_at | DateTime | 消费时间（Device 下载完成时间，可空） |
| refresh_count | Int | 续签次数（默认 0，超过 3 该事务置 FAIL） |

**【DEPRECATED，V1.3 起】** 整张表由 `DownloadUrl` 实体替代。V1.3 起所有下载凭证通过 `DownloadUrl` 记录。`OssSignedUrl` 保留不删除以兼容 V1.1/V1.2 历史数据，新实现不得参考。

#### AuditLog（审计日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| log_id | String PK | 日志 ID |
| transaction_id | String FK | 关联事务（可空） |
| actor_type | Enum | USER/WORKER/DEVICE/SYSTEM |
| actor_id | String | 操作者 ID |
| action | String(64) | 操作类型 |
| target | String | 操作对象 |
| details | JSON | 详细信息 |
| created_at | DateTime | 时间戳 |

#### RouteRule（路由规则）

| 字段 | 类型 | 说明 |
|------|------|------|
| rule_id | String PK | 规则 ID |
| transaction_type | String(64) | 事务类型（如 RENEWAL/NEW），与用户提交时一致 |
| flow_id | String FK | 分配的 Flow |
| flow_version | String | 指定 Flow 版本（为空则使用 current_version） |
| weight | Int | 权重百分比（1-100），同 transaction_type 下所有规则权重之和应为 100 |
| ~~priority~~ | ~~Int~~ | **DEPRECATED (V1.1)**：V1.0 用 priority 排序再按 weight 分配，逻辑重复。V1.1 简化为仅按 weight 随机分配，不再需要 priority 字段。保留字段不删除以兼容历史数据。 |
| is_active | Boolean | 是否启用 |
| created_by | String | 创建人 User ID |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### StateTransition（状态变更记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| transition_id | String PK | 变更 ID |
| transaction_id | String FK | 关联事务 |
| from_state | Enum | 原状态 |
| to_state | Enum | 新状态 |
| triggered_by | String | 触发者 |
| reason | String | 变更原因 |
| occurred_at | DateTime | 变更时间 |

#### OssSignedUrl（V1.1 新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| signed_url_id | String PK | 签名 URL 记录 ID（UUID） |
| transaction_id | String FK | 关联事务 |
| attachment_id | String FK | 关联附件（指向具体 OSS 对象） |
| url | String(1024) | OSS 签名 URL（含签名参数） |
| expires_at | DateTime | 过期时间（生成时 + 5min） |
| created_at | DateTime | 创建时间 |
| consumed_at | DateTime | 消费时间（Device 下载完成时间，可空） |
| refresh_count | Int | 续签次数（默认 0，超过 3 该事务置 FAIL） |

### 5.3 实体关系图

```
User ──N:1── Role
Transaction ──N:1── User (submitted_by)
Transaction ──N:1── Flow
Transaction ──N:1── RouteRule (via transaction_type)
RouteRule ──N:1── Flow
Transaction ──N:1── Worker (可空)
Transaction ──N:1── Device (可空)
Transaction ──1:N── Attachment
Transaction ──1:N── StepExecution
Transaction ──1:N── StateTransition
Transaction ──1:N── AuditLog
Transaction ──1:N── OssSignedUrl (V1.1 新增)
Flow ──1:N── FlowVersion
Flow ──1:N── Step
FlowVersion ──1:N── Step (via current_version binding on Step.flow_id+version)
StepExecution ──N:1── Step
Worker ──1:N── Device
```

**Mermaid 渲染版本（V1.1 新增，推荐使用）**：

```mermaid
erDiagram
    User ||--o{ Transaction : submits
    User }o--|| Role : has
    Transaction }o--|| Flow : uses
    Transaction }o--o| RouteRule : "routed by"
    RouteRule }o--|| Flow : targets
    Transaction }o--o| Worker : "assigned to"
    Transaction }o--o| Device : "assigned to"
    Transaction ||--o{ Attachment : has
    Transaction ||--o{ StepExecution : "executed by"
    Transaction ||--o{ StateTransition : tracks
    Transaction ||--o{ AuditLog : logs
    Transaction ||--o{ OssSignedUrl : "downloads via"
    Flow ||--o{ FlowVersion : versions
    Flow ||--o{ Step : contains
    Step ||--o{ StepExecution : "executed as"
    Worker ||--o{ Device : hosts
```

**V1.1 关系变化。**
- 新增 `Transaction ──1:N── OssSignedUrl`：每个事务可对应多个签名 URL（多文件场景）
- 原 `StepExecution ──N:1── Step` 保持不变（CONFIRM Step 字段在 Step 表中保留 DEPRECATED 标记）

**V1.2 关系变化。**
- `StepExecution.executor` 新增字段（V1.2 起固定为 WORKER）
- `Device.adb_status` 新增字段（ADB 连接状态机）
- `Worker.max_concurrent_devices` 与 `Worker.current_device_count` 新增字段
- 实体关系不变


---

## 6. 接口概要设计

### 6.1 接口分类

| 分类 | 用途 | 协议 |
|------|------|------|
| 业务接口 | 销售提交、查询事务 | HTTPS REST |
| 调度接口 | Worker 注册、心跳、任务领取 | HTTPS REST + WebSocket |
| 设备接口 | Device 文件下载、状态上报 | HTTPS REST |
| 管理接口 | 用户/角色/Flow/路由规则管理 | HTTPS REST |
| 监控接口 | Dashboard 数据查询 | HTTPS REST |

### 6.2 REST API 清单

#### 6.2.1 业务接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| POST | /api/v1/transactions | 单笔提交保单 | User Token |
| POST | /api/v1/transactions/batch | 批量提交保单 | API Token |
| GET | /api/v1/transactions/{id} | 查询事务详情 | User Token |
| GET | /api/v1/transactions | 查询事务列表（含筛选） | User Token |
| POST | /api/v1/transactions/{id}/retry | 手动重试事务（DLQ）| Admin Token |
| ~~GET \| /api/v1/transactions/{id}/confirms~~ | ~~查询待确认截图列表~~ | **DEPRECATED (V1.1)**：CONFIRM 移除 |
| ~~POST \| /api/v1/transactions/{id}/confirms/{step_exec_id}~~ | ~~用户确认/拒绝截图~~ | **DEPRECATED (V1.1)**：CONFIRM 移除 |
| **POST** | **/api/v1/transactions/{id}/oss-urls (V1.1 新增)** | **生成 OSS 签名 URL 列表** | **Worker Token** |
| **POST** | **/api/v1/oss-urls/{signed_url_id}/refresh (V1.1 新增)** | **续签过期的 OSS URL** | **Device Token** |
| **POST** | **/api/v1/transactions/{id}/download-urls (V1.3 新增，重命名自 oss-urls)** | **生成下载 URL 列表** | **Worker Token** |
| **POST** | **/api/v1/downloads/{url_id}/refresh (V1.3 新增)** | **续签过期的下载 URL** | **Device Token** |
| **GET** | **/api/v1/downloads/{url_id} (V1.3 新增)** | **Device 通过 token 直连下载文件** | **URL Token** |

**示例：POST /api/v1/transactions 请求体（V1.3 multipart/form-data）**

```
POST /api/v1/transactions
Content-Type: multipart/form-data; boundary=----FormBoundary123
Authorization: Bearer {user_token}

------FormBoundary123
Content-Disposition: form-data; name="transaction"
Content-Type: application/json

{
  "external_id": "BIZ-20260605-001",
  "business_type": "RENEWAL",
  "customer_phone": "138****1234",
  "customer_id_no": "310***********1234",
  "attachments_meta": [
    {
      "file_type": "ID_CARD",
      "description": "身份证正反面合一",
      "file_format": "JPG"
    },
    {
      "file_type": "DRIVING_LICENSE",
      "description": "行驶证",
      "file_format": "JPG"
    }
  ]
}
------FormBoundary123
Content-Disposition: form-data; name="file_0"; filename="idcard.jpg"
Content-Type: image/jpeg

<binary data>
------FormBoundary123
Content-Disposition: form-data; name="file_1"; filename="license.jpg"
Content-Type: image/jpeg

<binary data>
------FormBoundary123--
```

**响应体**

```json
{
  "code": 0,
  "data": {
    "transaction_id": "TXN-20260605-00001",
    "status": "PENDING",
    "submitted_at": "2026-06-05T10:00:00Z",
    "attachments": [
      {
        "attachment_id": "ATT-20260605-00001",
        "file_type": "ID_CARD",
        "description": "身份证正反面合一",
        "file_size": 1024000,
        "md5": "a1b2c3d4e5f6...",
        "storage_backend": "local",
        "storage_path": "/data/attachments/ATT-20260605-00001/idcard.jpg"
      },
      {
        "attachment_id": "ATT-20260605-00002",
        "file_type": "DRIVING_LICENSE",
        "description": "行驶证",
        "file_size": 2048000,
        "md5": "d4e5f6a1b2c3...",
        "storage_backend": "local",
        "storage_path": "/data/attachments/ATT-20260605-00002/license.jpg"
      }
    ]
  }
}
```

**示例：POST /api/v1/transactions/{id}/download-urls（V1.3 取代 V1.1 oss-urls）**

```http
POST /api/v1/transactions/TXN-20260605-00001/download-urls
Authorization: Bearer {worker_token}

响应:
{
  "code": 0,
  "data": {
    "transaction_id": "TXN-20260605-00001",
    "download_urls": [
      {
        "url_id": "DURL-20260605-00001",
        "attachment_id": "ATT-20260605-00001",
        "url": "https://api.example.com/api/v1/downloads/DURL-20260605-00001?token={sig}&expires=1749050700",
        "md5": "a1b2c3d4e5f6...",
        "expires_at": "2026-06-05T10:05:00Z",
        "storage_backend": "local"
      }
    ]
  }
}
```

**示例：GET /api/v1/downloads/{url_id}（V1.3 新增，Device 直连）**

```http
GET /api/v1/downloads/DURL-20260605-00001?token={sig}&expires=1749050700
Authorization: Bearer {device_token}  # 可选，URL 中的 token 即鉴权

响应:
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 1024000
Content-MD5: a1b2c3d4e5f6...

<binary file data>
```

#### 6.2.2 调度接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| POST | /api/v1/workers/register | Worker 注册 | 无（返回 Token） |
| POST | /api/v1/workers/heartbeat | Worker 心跳（含 CPU/内存/Device 数/ADB 状态，V1.2 增强） | Worker Token |
| GET | /api/v1/workers | 查询 Worker 列表 | Admin Token |
| GET | /api/v1/workers/{id} | 查询 Worker 详情 | Admin Token |
| DELETE | /api/v1/workers/{id} | 下线 Worker | Admin Token |
| GET | /api/v1/tasks/poll | 长轮询领取任务 | Worker Token |
| POST | /api/v1/tasks/{id}/ack | 确认任务接收 | Worker Token |
| POST | /api/v1/tasks/{id}/result | 上报任务结果 | Worker Token |
| GET | /api/v1/workers/scripts/versions | 查询本地 Flow 版本状态（与服务端校验） | Worker Token |
| GET | /api/v1/workers/scripts/download | 下载最新版本脚本包（仅返回有更新的） | Worker Token |
| GET | /api/v1/devices | 查询设备池 | Admin Token |
| PUT | /api/v1/devices/{id}/status | 更新设备状态（禁用等） | Admin Token |
| **POST** | **/api/v1/workers/{id}/adb-status (V1.2 新增)** | **上报 ADB 连接状态变更** | **Worker Token** |

#### 6.2.3 设备接口（V1.2 重写：移除 files / step-result；新增 download-ack）

| Method | Path | 描述 | 鉴权 | 变更 |
|--------|------|------|------|------|
| ~~GET~~ | ~~/api/v1/devices/{id}/files~~ | ~~获取事务附件下载链接~~ | ~~Device Token~~ | **DEPRECATED (V1.2)**：Device 不再主动获取文件，改由 Worker 通过 OSS 签名 URL 触发下载 |
| POST | /api/v1/devices/{id}/status | 上报设备状态 | Device Token | 不变 |
| POST | /api/v1/devices/{id}/ready | 上报就绪状态 | Device Token | 不变 |
| ~~POST~~ | ~~/api/v1/devices/{id}/step-result~~ | ~~上报 Step 执行结果~~ | ~~Device Token~~ | **DEPRECATED (V1.2)**：Step 由 Worker 端 Airtest 执行，Device 不再上报 Step 结果 |
| **POST** | **/api/v1/devices/{id}/download-ack** | **下载完成通知（V1.2 新增）** | **Device Token** | **新增** |

**新增接口详细说明（POST /api/v1/devices/{id}/download-ack）**：

```http
POST /api/v1/devices/{id}/download-ack
Content-Type: application/json
Authorization: Bearer {device_token}

{
  "transaction_id": "TXN-20260603-00001",
  "files": [
    {
      "md5": "a1b2c3d4e5f6...",
      "local_path": "/sdcard/sandbox/TXN-20260603-00001/idcard.jpg",
      "size_bytes": 1024000
    }
  ],
  "completed_at": "2026-06-03T10:00:25Z"
}
```

#### 6.2.4 管理接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| POST | /api/v1/users | 创建用户 | Admin Token |
| GET | /api/v1/users | 用户列表 | Admin Token |
| PUT | /api/v1/users/{id} | 更新用户 | Admin Token |
| DELETE | /api/v1/users/{id} | 禁用用户 | Admin Token |
| POST | /api/v1/roles | 创建角色 | Admin Token |
| GET | /api/v1/roles | 角色列表 | Admin Token |
| GET | /api/v1/flows | Flow 列表 | Admin Token |
| POST | /api/v1/flows | 创建/更新 Flow | Admin Token |
| GET | /api/v1/flows/{id} | 查询 Flow 详情（含当前版本） | Admin Token |
| GET | /api/v1/flows/{id}/versions | 查询 Flow 版本列表 | Admin Token |
| POST | /api/v1/flows/{id}/versions | 上传新版本脚本包 | Admin Token |
| POST | /api/v1/flows/{id}/versions/{version}/publish | 发布版本（置为已发布） | Admin Token |
| POST | /api/v1/flows/{id}/versions/{version}/rollback | 回滚到指定版本 | Admin Token |
| PUT | /api/v1/flows/{id}/versions/{version}/deprecate | 停用指定版本 | Admin Token |
| GET | /api/v1/flows/{id}/versions/{version}/download | 下载脚本包（Worker 用） | Worker Token |
| GET | /api/v1/flows/{id}/steps | Flow 步骤详情 | Admin Token |
| PUT | /api/v1/flows/{id}/schema | 更新校验 Schema | Admin Token |
| GET | /api/v1/routes | 路由规则列表 | Admin Token |
| POST | /api/v1/routes | 创建/更新路由规则 | Admin Token |
| PUT | /api/v1/routes/{rule_id} | 更新路由规则（含权重调整） | Admin Token |
| DELETE | /api/v1/routes/{rule_id} | 删除路由规则 | Admin Token |

#### 6.2.5 监控接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| GET | /api/v1/dashboard/overview | 总览指标 | Admin Token |
| GET | /api/v1/dashboard/transactions | 事务统计（按时间/状态） | Admin Token |
| GET | /api/v1/dashboard/workers | Worker 负载统计 | Admin Token |
| GET | /api/v1/dashboard/devices | 设备在线率统计 | Admin Token |
| GET | /api/v1/dashboard/dlq | 死信队列列表 | Admin Token |
| GET | /api/v1/audit-logs | 审计日志查询 | Admin Token |

### 6.3 通信协议概要

#### WebSocket 通道

| 通道 | 方向 | 用途 |
|------|------|------|
| /ws/v1/dispatch | Server → Worker | 实时推送任务指令 |
| /ws/v1/status | Worker → Server | 实时状态变更上报 |

**消息格式：**

```json
{
  "type": "TASK_DISPATCH",
  "payload": {
    "transaction_id": "TXN-20260602-00001",
    "flow_id": "FLOW-RENEWAL-001",
    "device_id": "DEV-SN12345"
  },
  "timestamp": "2026-06-02T10:00:01Z"
}
```

#### Socket 通道（Android ↔ Worker，V1.2 精简，V1.3 通用化）

| 方向 | 用途 |
|------|------|
| Worker → Device | **V1.2 仅保留**：下发下载指令（DOWNLOAD_FILES）；**V1.3 起**：`download_urls` 字段名替换 `oss_urls`（URL 指向后端/OSS 对 Device 透明） |
| Device → Worker | **V1.2 仅保留**：上报下载完成（DOWNLOAD_COMPLETE）、OSS URL 过期（**V1.3 改名为** URL 过期） |

**消息格式（V1.3 通用化）：**

```json
// Worker → Device (LAN Socket :8765) — V1.3 唯一保留的指令
{
  "cmd": "DOWNLOAD_FILES",
  "params": {
    "transaction_id": "TXN-20260605-00001",
    "download_urls": [
      {
        "file_type": "ID_CARD",
        "url": "https://api.example.com/api/v1/downloads/DURL-xxx?token={sig}&expires={ts}",
        "md5": "a1b2c3d4e5f6...",
        "expires_at": "2026-06-05T10:05:00Z",
        "storage_backend": "local"
      }
    ]
  }
}

// Device → Worker
{
  "event": "DOWNLOAD_COMPLETE",
  "transaction_id": "TXN-20260605-00001",
  "files": [...]
}

{
  "event": "URL_EXPIRED",
  "url_id": "DURL-xxx"
}
```

**V1.3 关键变化。**
- `oss_urls` 字段重命名为 `download_urls`（V1.3 通用化术语）
- URL 字符串值在不同后端下指向不同：V1.3 默认 `local` → `https://api.example.com/...`；V1.4+ `oss` → `https://oss.example.com/...`
- `storage_backend` 字段随 URL 一起下发（Device 可记录但不强制使用）
- 事件 `OSS_URL_EXPIRED` 重命名为 `URL_EXPIRED`（与术语解耦）

**【DEPRECATED，V1.2 起】** Socket 通道原包含的 `EXECUTE_STEP` 指令与 `STEP_RESULT` 事件已完全移除。Device 不再接收 Step 执行指令、不再上报 Step 结果——所有 Step 在 Worker 端 Airtest runtime 中执行。

### 6.4 通用约定

| 项目 | 规范 |
|------|------|
| 鉴权 | Bearer Token（JWT），payload 含 role/worker_id/device_id |
| 错误格式 | `{"code": <int>, "message": "<string>", "details": <object>}` |
| 分页 | `?page=1&page_size=20`，响应含 `total`/`items` |
| 限流 | 按角色限流：**销售 40次/min**（V1.2 调整：原 60/min，因 ATT 延长 50% 调降），API Token 600次/min |
| 版本 | URL 路径版本 `/api/v1/` |
| **幂等键（V1.1 新增）** | **所有 POST 接受 `Idempotency-Key` 请求头**（UUID v4），同一 Key 24h 内仅生效一次；用于事务提交、回调等场景防重复 |
| **白名单 IP（V1.1 新增）** | **Device 接口（§6.2.3）仅接受白名单 IP 连接**，白名单由运维维护；非法连接 403 |
| **安全组规则（V1.1 新增）** | **云端 Backend SLB 仅开放 443（公网）/ 5432（DB 内网）/ 6379（Redis 内网）；Worker 仅出站连接（443），无需入站规则** |
| **ADB 物理连接（V1.2 新增）** | **Worker 通过 USB ADB 连接 Device，每台 Worker 同时挂载 ≤ 3 台 Device**（CPU 瓶颈约束） |

---


## 7. 部署架构

### 7.1 逻辑架构图（V1.2 更新：Worker 端 Airtest runtime，V1.3 更新：Server-first 存储）

```
┌─────────────────────────────────────────────────────┐
│                    用户层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Web 门户  │  │REST API  │  │  Dashboard       │  │
│  └─────┬────┘  └─────┬────┘  └────────┬─────────┘  │
└────────┼─────────────┼────────────────┼────────────┘
         │             │                │
         ▼             ▼                ▼
┌─────────────────────────────────────────────────────────┐
│              云端 (阿里云 / 腾讯云 / ...)                 │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │            Backend 服务 (K8s / Docker)             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐         │  │
│  │  │ 事务接入  │ │ 调度中心  │ │ 资产管理   │         │  │
│  │  │ & 路由    │ │Dispatcher│ │ & 监控     │         │  │
│  │  └──────────┘ └──────────┘ └───────────┘         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐         │  │
│  │  │ 用户管理  │ │ 审计日志  │ │ Dashboard │         │  │
│  │  └──────────┘ └──────────┘ └───────────┘         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ PostgreSQL   │  │    Redis     │  │ RabbitMQ /   │  │
│  │ (RDS 主从)   │  │ (Sentinel)   │  │ Redis Stream │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ┌────────────────────────────────────────────┐    │  │
│  │  │ 文件存储 (V1.3: LocalStorageBackend 本地 SSD;     │    │  │
│  │  │        V1.4+ 可选 OssStorageBackend / MinIO)      │    │  │
│  │  └────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │            负载均衡 (SLB / CLB)                     │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │
                    公网 / 专线 / VPN
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  本地站点 A     │ │  本地站点 B     │ │  本地站点 N     │
│  (办公室/门店)  │ │  (办公室/门店)  │ │  (办公室/门店)  │
│                │ │                │ │                │
│ ┌────────────┐ │ │ ┌────────────┐ │ │ ┌────────────┐ │
│ │ Worker#1   │ │ │ │ Worker#3   │ │ │ │ Worker#N   │ │
│ │ (Desktop)  │ │ │ │ (Desktop)  │ │ │ │ (Desktop)  │ │
│ │            │ │ │ │            │ │ │ │            │ │
│ │ Airtest    │ │ │ │ Airtest    │ │ │ │ Airtest    │ │
│ │ Runtime池  │ │ │ │ Runtime池  │ │ │ │ Runtime池  │ │
│ │  ↑         │ │ │ │  ↑         │ │ │ │  ↑         │ │
│ │  │ USB ADB │ │ │ │  │ USB ADB │ │ │ │  │ USB ADB │ │
│ │  ↓         │ │ │ │  ↓         │ │ │ │  ↓         │ │
│ │ ┌──┐ ┌──┐ │ │ │ │ ┌──┐ ┌──┐ │ │ │ │ ┌──┐ ┌──┐ │ │
│ │ │A │ │B │ │ │ │ │ │C │ │D │ │ │ │ │ │E │ │F │ │ │
│ │ └──┘ └──┘ │ │ │ │ └──┘ └──┘ │ │ │ │ └──┘ └──┘ │ │
│ │ (极简Agent)│ │ │ │(极简Agent)│ │ │ │(极简Agent)│ │
│ └────────────┘ │ │ └────────────┘ │ │ └────────────┘ │
│  N≤3 Device   │ │  N≤3 Device   │ │  N≤3 Device   │
└────────────────┘ └────────────────┘ └────────────────┘
```

**V1.2 关键变化。** Worker 端新增 Airtest Runtime 池（V1.1 不存在）；Device Agent 极简化（无 Airtest runtime，包大小从 ~50MB 降至 ~5MB）。

### 7.2 部署拓扑

#### 云端部署

| 节点类型 | 部署方式 | 说明 |
|----------|----------|------|
| Backend 服务 | K8s Pod / Docker 容器 | 2+ 实例，通过 SLB/CLB 负载均衡 |
| 数据库 | 云 RDS（PostgreSQL） | 主从同步复制，自动备份 |
| Redis（可选） | 云 Redis（Sentinel 模式） | 高可用，持久化；前期可省略 |
| 消息队列（可选） | 云 MQ / 自建 RabbitMQ | 持久化队列；前期可省略 |
| 对象存储 | 云 OSS/COS | 存储影像附件，CDN 加速下载 |
| 负载均衡 | 云 SLB/CLB | HTTPS 卸载，WebSocket 支持 |

#### 本地部署（V1.2 调整）

| 节点类型 | 部署方式 | 说明 |
|----------|----------|------|
| **Worker 节点** | **本地桌面电脑（Linux/Windows）** | **V1.2 升级**：除 Python 环境外需安装 Airtest + pocoui 依赖；通过 USB 物理连接挂载 Device |
| **Worker 硬件（V1.2 上调）** | **8C 16GB 100GB SSD** | **V1.2 由 4C 8GB 上调**：Airtest 进程 + 图像识别吃 CPU/内存 |
| Android 设备 | USB 挂载于 Worker | **V1.2 简化**：中低端机型可（无 Airtest runtime 需求） |

### 7.3 网络架构（V1.2 调整：增加 USB ADB 段）

```
云端                                     本地站点
┌─────────────┐     公网/VPN      ┌─────────────────┐
│  SLB/CLB    │◄────────────────►│  Worker (NAT)    │
│  (443/WSS)  │   HTTPS / WSS    │  (出站访问云端)    │
└──────┬──────┘                  └────────┬────────┘
       │                                  │ USB ADB (V1.2 新增)
       │                                  │ Socket :8765 (LAN)
┌──────┴──────┐                  ┌────────┴────────┐
│  Backend    │                  │  Android Agent   │
│  集群       │                  │  (极简化)        │
└──────┬──────┘                  └─────────────────┘
       │
┌──────┴──────┐
│ RDS / Redis │
│ / MQ / OSS  │
└─────────────┘
```

### 7.4 网络要求

| 通道 | 协议 | 端口 | 方向 | 说明 |
|------|------|------|------|------|
| Web/API → SLB | HTTPS | 443 | 入站 | TLS 1.2+ |
| Worker → SLB | HTTPS + WSS | 443 | 出站 | Worker 主动连云端，无需开放入站端口 |
| Device → OSS | HTTPS | 443 | 出站 | Device 直接从 OSS 下载文件（V1.2 仍由 Device 直连，不经 Worker） |
| Device → Worker | TCP Socket | 8765 | 局域网 | 本地指令通道（**V1.2 仅用于下载控制**） |
| **Worker → Device** | **USB ADB** | **-** | **物理连接** | **V1.2 新增**：Worker 通过 USB ADB 驱动 Device UI 操作 |
| Backend → RDS | TCP | 5432 | 内网 | 云内网通信 |
| Backend → Redis | TCP | 6379 | 内网 | 云内网通信 |
| Backend → MQ | TCP | 5672 | 内网 | 云内网通信 |
| Backend → OSS | HTTPS | 443 | 内网 | 云内网通信 |

**关键设计决策：** Worker 采用出站连接模式，主动向云端发起 HTTPS/WSS 连接，本地无需开放公网入站端口，降低安全风险。设备文件下载走 OSS 直链（签名 URL），不经 Backend 中转，减轻服务端带宽压力。**V1.2 新增**：Worker 与 Device 通过 USB ADB 物理连接，每根 USB 线绑定 1 台 Device，单 Worker 限制挂载 2-3 台 Device。

**安全组/防火墙策略（V1.1 新增，V1.2 保留）：**
- **Backend SLB 安全组**：仅开放 443（公网入站）；其他端口全关
- **Backend ECS 安全组**：仅允许来自 SLB 内网段的 443 流量；DB/Redis/OSS 走云内网
- **RDS 安全组**：仅允许 Backend ECS 安全组访问 5432
- **Redis 安全组**：仅允许 Backend ECS 安全组访问 6379
- **OSS Bucket Policy**：仅允许 Backend ECS RAM Role + Device 签名 URL（公开读禁用）
- **Worker 本地网络**：无入站规则（出站 HTTPS/WSS 即可）
- **白名单 IP**（V1.1 新增）：Device Socket 接口（8765）仅接受白名单 IP（站点固定 IP 段）

### 7.5 硬件建议（V1.2 上调 Worker 规格、下调 Device 规格，V1.3 调整存储）

#### 云端资源（最小配置）

| 节点 | 规格 | 数量 | 说明 |
|------|------|------|------|
| Backend (ECS) | 4C 8GB **+ 1TB SSD 数据盘（V1.3 新增）** | 2 | K8s Worker 节点；**V1.3 起**：1TB SSD 用于 `LocalStorageBackend` 文件存储（每 Backend 实例 500GB 配额） |
| RDS | 4C 16GB 200GB SSD | 1 | 主实例 |
| ~~OSS~~ | ~~按量付费~~ | ~~-~~ | **V1.3 调整**：OSS 不再为 MVP 必需；未来切 `OssStorageBackend` 时再启用 |
| SLB | 标准版 | 1 | HTTPS 卸载 |

#### 本地站点资源（单站点最小配置，V1.2 调整）

| 节点 | 规格 | 数量 | 说明 |
|------|------|------|------|
| **Worker 电脑** | **8C 16GB 100GB SSD**（V1.2 上调，原 4C 8GB） | **2-3**（V1.2 新增） | 每台 Worker 限挂载 2-3 Device |
| **Android 设备** | **中低端可**（V1.2 下调，原中高端） | **4-9**（2-3 Worker × 2-3 Device） | 无 Airtest runtime 需求，硬件要求降低 |
| USB 数据线 | 优质（V1.2 强调） | 4-9 | 每台 Device 1 根；接触不良会导致 ADB 断开 |
| 网络带宽 | ≥ 20Mbps 上行 | 1 | 确保文件上传和 WSS 通信稳定 |

### 7.6 云服务选型参考

| 组件 | 阿里云 | 腾讯云 | 华为云 |
|------|--------|--------|--------|
| 计算 | ECS + ACK | CVM + TKE | ECS + CCE |
| 数据库 | RDS PostgreSQL | TDSQL PostgreSQL | RDS PostgreSQL |
| 缓存 | Redis | TCR | DCS Redis |
| 消息队列 | RabbitMQ / RocketMQ | TDMQ | DMS |
| 对象存储 | OSS | COS | OBS |
| 负载均衡 | SLB | CLB | ELB |
| CDN | CDN | CDN | CDN |

### 7.7 演进路径

#### 前期（MVP / 试运行阶段，V1.1 调整，V1.2 扩展）

适用场景：≤ 5 个本地站点、≤ 50 台 Android 设备（V1.2 由 20 台上调）、日处理 ≤ 500 笔事务

| 组件 | 是否必需 | 说明 |
|------|----------|------|
| Backend 服务 | 必需 | 单实例或双实例 |
| PostgreSQL | 必需 | 主存储（V1.1 起不再承担任务队列角色） |
| **Redis Stream** | **必需（V1.1 升级）** | **任务队列 + 缓存**；Consumer Group 多副本调度中心天然支持 |
| 对象存储 OSS | **V1.3 调整**：V1.3 MVP 不必需 | **V1.3 起**：MVP 阶段使用 `LocalStorageBackend`（Backend 主机本地 SSD），OSS 留作 V1.4+ 扩展后端；**V1.1 关键决策**（OSS-first 时代）已废止：原"OSS 桶需公网可访问"约束由"V1.3 Backend 服务需公网可访问（暴露 `/api/v1/downloads`）"替代 |
| 负载均衡 SLB | 必需 | HTTPS 卸载 + WSS |
| MQ | 可省略 | 暂用 Redis Stream 替代 |
| **Airtest + pocoui（V1.2 新增）** | **Worker 端必需** | **Python ≥3.14 + airtest + pocoui 依赖** |

**V1.1 关键变化：** Redis Stream 从"中期可选"前移到"MVP 必需"。理由：
- 避免原"DB 轮询 + 多副本调度"导致的事务重复分配事故
- 调度延迟 P95 从 2s 降到 < 200ms
- 多副本调度中心天然支持（Consumer Group）
- 削峰能力强（突发 10× 流量不爆）
- 增加 1 个云组件，月费增加 30-40%，但规避 P0 事故

**V1.2 关键变化：** Worker 端必须安装 Airtest 运行时（airtest + pocoui + airtest.core.android.adb）。理由：
- RPA 步骤执行从 Device 端迁至 Worker 端，Worker 需具备 UI 自动化能力
- Airtest 原生设计哲学为"桌面 Python 控制手机"，无需 Android 端 runtime
- 带来调试便利（桌面 IDE 断点调试）+ 脚本热更新（Worker 重启即生效）

**架构简化收益：**
- 减少 DB 轮询压力（释放 DB CPU 给事务持久化）
- 调度中心无状态化可扩展
- 减少隐性故障点（DB 行锁竞争）
- **V1.2 新增**：Device Agent 简化（无 Airtest runtime，包大小 -90%）；脚本集中管理（Device 不再持有 Flow）

#### 中期（业务扩展阶段）

适用场景：≥ 10 个本地站点、≥ 50 台设备、日处理 ≥ 2000 笔事务

| 触发条件 | 引入组件 |
|----------|----------|
| Redis Stream 内存压力（> 70%） | 引入 Redis Cluster；将历史事务迁回 DB |
| Backend 实例 ≥ 3 副本 | 启用 WebSocket 粘性会话（SLB 配 cookie）或改用前端轮询 |
| 需要异步事件总线（短信通知、外部系统对接） | 引入 MQ（RabbitMQ），与 Redis Stream 分工：Stream 任务队列、MQ 事件总线 |
| 多 Backend 实例间需要共享限流状态 | Redis 升级（已有则无需） |
| **单 Worker 满载仍不足（V1.2 新增）** | **按需扩容 Worker 数量；每站点 ≥ 4 个 Worker** |

#### 后期（规模化阶段）

适用场景：≥ 50 个站点、≥ 200 台设备、日处理 ≥ 1 万笔事务

| 组件 | 部署方式 |
|------|----------|
| Redis | Sentinel / Cluster 模式 |
| MQ | RabbitMQ 集群 / RocketMQ |
| Backend | K8s 多副本 + HPA 自动扩缩容 |
| RDS | 读写分离 + 分库分表 |
| OSS | 跨地域复制 + CDN 加速 |

### 7.8 灾备设计（V1.1 新增，V1.2 扩展）

| 层级 | 灾备策略 | RPO | RTO |
|------|----------|-----|-----|
| 数据库 PostgreSQL | 主从同步复制 + 异地只读副本 | ≤ 1s | ≤ 5min |
| Redis | AOF 持久化 + Sentinel 主从切换 | ≤ 5s（最近 5s 数据可能丢失） | ≤ 1min |
| OSS 对象存储 | 跨可用区复制 + 异地只读副本 | 0（同步复制） | ≤ 1min |
| Backend 服务 | K8s 多副本 + SLB 切流 | 0（无状态） | ≤ 30s |
| KMS | 跨地域主备 | 0（实时同步） | ≤ 5min |
| Worker 节点 | 本地状态可重建 | 0（任务由 Redis Stream 重投） | ≤ 5min |
| **Worker 进程崩溃（V1.2 新增）** | **该 Worker 挂载的所有 Device 当前事务回退 PENDING** | 0 | **≤ 60s** |

**异地容灾方案。** 单可用区故障时切换到同城备可用区（自动，< 5min）；城市级灾难时切换到异地只读副本（手动，< 1h）。**MVP 阶段**仅实施同城可用区方案，异地容灾进入 V1.3 规划。

---


## 8. 非功能性需求

### 8.1 性能（V1.2 调整）

| 指标 | 目标值 |
|------|--------|
| 单笔事务提交响应时间 | ≤ 500ms（**P95 ≤ 500ms，P99 ≤ 1s**，V1.1 加 P99） |
| 任务调度延迟（PENDING → DISPATCHED） | ≤ 200ms（V1.1 调整） |
| **ADB 握手延迟（V1.2 新增）** | **≤ 30s（DISPATCHED → ADB_CONNECTING → DOWNLOADING）** |
| 文件下载速率（Device → OSS） | ≥ 5MB/s（局域网） |
| 单 Step 执行超时 | 默认 60s，可配置 |
| **单事务全流程 ATT** | **≤ 8min（V1.2 调整：原 ≤ 5min；仅 RUNNING 阶段，V1.1 明确）** |
| 系统并发事务处理能力 | ≥ 50 笔/分钟（单 Backend 实例） |
| **单 Worker 并发 Device（V1.2 新增）** | **≤ 3 Device / Worker（CPU 瓶颈约束）** |
| **单站点容量（V1.2 新增）** | **2-3 Worker × 2-3 Device = 4-9 Device/站点** |
| **API 限流阈值（V1.2 调整）** | **销售 40次/min**（原 60/min，因 ATT 延长 50% 调降），API Token 600次/min |

### 8.2 可用性

| 指标 | 目标值 |
|------|--------|
| Backend 服务可用性 | ≥ 99.9%（年停机 ≤ 8.76h） |
| Worker 故障切换时间 | ≤ 60s（心跳超时检测 + 事务重新调度） |
| **Worker 进程崩溃恢复（V1.2 新增）** | **≤ 60s（该 Worker 所有 Device 事务回退 PENDING）** |
| 数据库 RPO | ≤ 1s（主从同步复制） |
| 数据库 RTO | ≤ 5min |
| 文件下载断点续传恢复 | 网络恢复后自动续传，无需人工干预 |
| **ADB 断开重连（V1.2 新增）** | **≤ 10s（`adb reconnect offline` 自动重连）** |

### 8.3 安全性

| 需求项 | 描述 |
|--------|------|
| 传输加密 | 全链路 HTTPS/TLS 1.2+，WebSocket 使用 WSS |
| 存储加密 | 敏感字段（手机号、身份证号）AES-256 加密存储，**密钥由 KMS 托管（V1.1 新增）** |
| 数据脱敏 | API 响应中手机号显示为 `138****1234`，身份证号显示为 `310***********1234` |
| 鉴权 | 所有 API 携带 Bearer Token（JWT），Token 有效期 24h |
| 客户端沙箱 | Worker 侧脚本包存储 AES-256 加密存储，权限 700（V1.1 起影像文件不在 Worker 沙箱） |
| **Worker 本地沙箱（V1.2 新增）** | **`~/.3is-auto/sandbox/{txn_id}/screenshots/`，仅存 Airtest 截图，权限 700** |
| API 防刷 | 按角色限流 + IP 黑名单机制 |
| 日志脱敏 | 审计日志中敏感字段自动脱敏 |
| 文件清理 | 事务终态后自动清理 Device 端影像文件（SUCCESS 立即清理，FAIL 保留 24h）；**V1.2 由 Worker 触发清理** |
| **OSS 地域约束（V1.1 新增）** | **OSS 桶固定在客户指定地域，禁跨地域复制** |
| **白名单 IP（V1.1 新增）** | **Device Socket 接口仅接受白名单 IP** |
| **幂等键（V1.1 新增）** | **所有 POST 接受 Idempotency-Key，防重复提交** |

### 8.4 可观测性（V1.1 重写，V1.2 扩展）

**技术选型。**
- **指标：** Prometheus（拉模式）
- **日志：** Loki（标签索引 + 对象存储后端）
- **链路追踪：** Tempo（兼容 OpenTelemetry）
- **SDK：** OpenTelemetry SDK（统一 instrumentation）
- **可视化：** Grafana（指标 + 日志 + Trace 联动）
- **告警：** Alertmanager（路由到企业微信 / 钉钉 / 邮件）

**指标体系（RED/USE）。**

| 维度 | 指标 | 说明 |
|------|------|------|
| **R**ate（请求速率） | `transactions_submitted_total` | 每分钟事务提交数 |
| | `transactions_completed_total{status}` | 每分钟事务完成数（按状态分组） |
| | `dispatch_latency_seconds` | 调度延迟分布 |
| **E**rror（错误率） | `transaction_failure_rate` | 事务失败率（按 Flow 分组） |
| | `step_failure_rate{step_name}` | 步骤失败率（按 Step 分组） |
| **D**uration（时延） | `transaction_duration_seconds` | 事务执行时长分布 |
| | `step_duration_seconds{step_name}` | 步骤执行时长分布 |
| **U**tilization（利用率） | `worker_cpu_usage` | Worker CPU 使用率（**V1.2 重点监控**：单 Worker 多 Device 负载） |
| | `worker_memory_usage` | Worker 内存使用率 |
| | `device_battery_level` | Device 电量 |
| **S**aturation（饱和度） | `redis_stream_pending_count` | Redis Stream 待处理数 |
| | `dispatcher_queue_depth` | 调度队列深度 |
| | `db_connection_pool_in_use` | DB 连接池使用率 |
| **V1.2 新增指标** | `worker_adb_connected_count` | Worker 当前 ADB 连接成功的 Device 数 |
| | `airtest_step_duration_seconds` | Airtest 步骤执行时长（区别于原有 step_duration） |
| | `adb_reconnect_total` | ADB 重连累计次数 |
| **V1.3 新增指标** | `storage_backend_total_bytes{backend}` | 存储后端总容量（按后端标签） |
| | `storage_backend_used_bytes{backend}` | 存储后端已用容量 |
| | `storage_backend_used_ratio{backend}` | 存储后端使用率（0-1） |
| | `storage_put_duration_seconds{backend}` | 存储后端 put 操作耗时 |
| | `storage_get_duration_seconds{backend}` | 存储后端 get / 签名 URL 读取耗时 |
| | `download_url_generated_total{backend}` | 生成的下载 URL 数（按后端标签） |

**Trace 规范。**
- **TraceID：** 使用 Transaction ID 作为 TraceID，贯穿全链路
- **Span 划分：** API 网关 → 调度中心 → Worker（**V1.2 扩展**：包含 Airtest runtime 调用）→ Device → 步骤执行
- **关键属性：** transaction_id, business_type, flow_id, step_id, worker_id, device_id
- **采样率：** 100%（生产初期）；后期可降至 50%

**初始告警规则集（V1.2 扩展）。**

| 级别 | 告警条件 | 通知 |
|------|----------|------|
| P1 | Backend 不可用（健康检查连续 3 次失败） | 立即 |
| P1 | Redis Stream 阻塞（待处理数 > 1000 持续 5min） | 立即 |
| P1 | 数据库主从切换 | 立即 |
| P2 | 事务积压 > 100 持续 10min | 5min 内 |
| P2 | 设备在线率 < 80% | 5min 内 |
| P2 | 事务失败率 > 10%（滑动 1h） | 5min 内 |
| P3 | 调度延迟 P95 > 1s 持续 10min | 30min 内 |
| P3 | Worker 心跳超时（>3 次） | 30min 内 |
| P3 | OSS 签名 URL 续签失败率 > 5% | 30min 内 |
| **P1（V1.2 新增）** | **Worker CPU 使用率 > 80% 持续 5min** | **立即** |
| **P2（V1.2 新增）** | **单 Worker ADB 断开次数 > 5 次/小时** | **5min 内** |
| **P2（V1.2 新增）** | **单事务 ATT 超过 10 分钟** | **5min 内** |
| **P1（V1.3 新增）** | **存储后端使用率 > 90% 持续 5min** | **立即** |
| **P1（V1.3 新增）** | **`StorageBackend` 调用连续失败 3 次（put/get 不可用）** | **立即** |
| **P3（V1.3 新增）** | **下载 URL 续签失败率 > 5%** | **30min 内**（**V1.3 由 OSS 续签升级为通用续签**） |

**Dashboard 面板。**
- 实时概览（事务积压、设备在线率、成功率、ATT）
- Worker 负载（CPU/内存/活跃事务，**V1.2 重点**：CPU 监控 + Device 挂载数）
- 设备池（电量/存储/锁屏状态，**V1.2 新增**：ADB 连接状态）
- 调度中心（队列深度/消费速率）
- DLQ 列表（按失败原因分组）
- 异常截图流（FR-SVR-018 推送）

**日志规范。**
- 格式：JSON（统一 snake_case 字段命名）
- 必含字段：timestamp, level, transaction_id, trace_id, span_id, module, message
- 敏感字段：手机号、身份证号自动脱敏（不允许打印完整值）
- 保留期：180 天（PIPL 推荐）

### 8.5 容错性

| 需求项 | 描述 |
|--------|------|
| Step 级重试 | 默认 3 次，指数退避（1s/2s/4s） |
| 事务级重试 | 连续失败 ≥3 次进入 DLQ |
| **事务级超时（V1.1 新增）** | **单事务从 PENDING 起 30 分钟未到终态强制进 DLQ** |
| Worker 崩溃恢复 | 心跳超时检测 → 事务回退至 PENDING → 重新调度 |
| Device 离线处理 | 调度跳过离线设备，事务重新分配 |
| 死信队列 | DLQ 事务不自动重试，运维手动处理 |
| 客户端自恢复 | Worker 进程崩溃后自动重启，恢复未完成任务 |
| OSS 签名 URL 过期 | Device 端自动续签；连续 3 次失败该事务置 FAIL |
| **ADB 断开重连（V1.2 新增）** | **`adb reconnect offline` 自动重连，≤ 10s；失败则事务回退 PENDING** |
| **Airtest 步骤重试（V1.2 新增）** | **Step 失败自动重试 3 次（指数退避 1s/2s/4s）；耗尽后 Step FAIL** |
| **Worker 进程崩溃恢复（V1.2 新增）** | **心跳超时 → 该 Worker 所有 Device 事务回退 PENDING** |
| **USB 物理断开（V1.2 新增）** | **触发运维告警；事务回退 PENDING** |

### 8.6 扩展性

| 需求项 | 描述 |
|--------|------|
| 横向扩展 | Worker 节点即插即用，新增 Worker 自动注册并参与调度 |
| **Worker 数量扩展（V1.2 调整）** | **单 Worker 受 CPU 限制 2-3 Device；横向扩展通过增加 Worker 数量实现** |
| Flow 可配置 | 新增保险产品流程只需定义 Flow + Steps，无需改代码 |
| Schema 热更新 | 校验规则变更无需重启服务 |
| 设备类型扩展 | 预留 iOS 设备接入能力（Device Controller 接口抽象） |
| 多保险产品 | 通过 Flow 定义支持不同保险公司的 APP 操作流程 |

### 8.7 容量规划模型（V1.1 新增，V1.2 调整）

**四维容量曲线。**

| 维度 | 公式 | MVP 目标 | 中期阈值 | 后期阈值 |
|------|------|----------|----------|----------|
| **用户数** | 销售账号数 + 运维账号数 | ≤ 50 | ≤ 200 | ≤ 1000 |
| **事务量** | 日提交事务数 | ≤ 500 | ≤ 2000 | ≤ 10000 |
| **设备数** | 挂载 Android 设备数 | **≤ 50（V1.2 上调，原 ≤ 20）** | ≤ 100 | ≤ 200 |
| **存储增长** | 影像文件累计 | ≤ 500 GB | ≤ 2 TB | ≤ 20 TB |

**资源-容量映射（V1.2 MVP 阶段）。**

| 资源 | 容量上限 | 扩容触发 | 扩容动作 |
|------|----------|----------|----------|
| Backend ECS（4C 8GB） | 50 笔/分 | CPU > 70% 持续 10min | 加副本（K8s HPA） |
| PostgreSQL（4C 16GB 200GB SSD） | 100 笔/分 | CPU > 60% 或连接池 > 80% | 升级规格或加只读 |
| Redis（4GB） | 200 笔/分 | 内存 > 70% 或 Stream 待处理 > 1000 | 升级内存或 Cluster |
| OSS | 按量付费 | 无硬上限 | - |
| SLB | 无硬上限 | 带宽 > 80% | 升级带宽 |
| **Worker（8C 16GB，V1.2 新增）** | **3 Device/Worker** | **CPU > 80% 持续 5min** | **新增 Worker 节点** |
| **单站点容量（V1.2 新增）** | **2-3 Worker × 2-3 Device = 4-9 Device/站点** | **单 Worker CPU 持续 > 80%** | **新增 Worker 节点** |
| **单事务 ATT（V1.2 新增）** | **5-8 分钟** | **持续 > 10 分钟** | **检查 Airtest 脚本 / 增加 Worker** |

**性能与容量的预算。** MVP 阶段在峰值时刻（早 9-10 点、午 2-3 点）需保证 50 笔/分 × 30min = 1500 笔事务可持续。资源-容量映射在峰值时刻留 30% 冗余。**V1.2 新增**：单事务 ATT 5-8 分钟（原 3-5 分钟），峰值时刻单 Worker 负载 ≤ 3 Device 时 CPU < 80%。

---

## 9. 技术约束

| 约束项 | 规范 |
|--------|------|
| 核心语言 | Python ≥ 3.14，严格使用 UV 进行依赖管理与虚拟环境隔离 |
| **自动化框架（V1.2 调整）** | **Airtest 作为核心图像识别与设备控制框架（**Worker 端执行**，V1.2 调整）**；封装统一 Device Controller 接口，屏蔽 Android 设备差异 |
| **POCO 库（V1.2 新增）** | **`pocoui`（≥ 1.0）— Airtest 配套 UI 控件识别库，Worker 端使用** |
| **ADB 库（V1.2 新增）** | **`airtest.core.android.adb` — Airtest 封装的 ADB 客户端，用于 USB 设备连接、Shell 命令、文件传输** |
| 通信协议 | 全链路 HTTPS/TLS 加密，API 携带 Token 鉴权 |
| **USB ADB（V1.2 新增）** | **Worker 与 Device 间通过 USB ADB 物理连接；ADB 工具 ≥ 1.0.41** |
| 配置管理 | 客户端与移动端配置（服务器地址、存储路径等）支持 YAML/JSON 文件配置，禁止硬编码 |
| 数据库 | PostgreSQL（主存储）；Redis（可选，按业务规模引入） |
| 消息队列 | RabbitMQ 或 Redis Stream（可选，按业务规模引入） |
| 对象存储 | **V1.3 通用化**：`StorageBackend` 抽象接口；V1.3 MVP 默认 `LocalStorageBackend`（本地文件系统）；V1.4+ 可选 `OssStorageBackend`（阿里云 OSS）、`MinioStorageBackend`（S3 兼容 MinIO）；影像附件 + 流程脚本包都通过 `StorageBackend` 存储 |
| **StorageBackend 接口（V1.3 新增）** | **`put(key, data, content_type) -> str` / `get(key) -> bytes` / `generate_signed_url(key, ttl_seconds) -> str` / `delete(key) -> None` / `exists(key) -> bool`；所有业务代码通过此接口访问存储，不感知具体后端** |
| 脚本存储规范 | 流程脚本包（.py/.zip）通过 `StorageBackend` 存储；V1.3 默认路径 `local://flows/{flow_id}/{version}/script.zip`；本地缓存于 **Worker（V1.2 强调）**：`~/.3is-auto/flows/{flow_id}/{version}/` |
| **沙箱路径（V1.2 新增，V1.3 调整）** | **Worker 本地：`~/.3is-auto/sandbox/{txn_id}/screenshots/`（Airtest 截图）；Device：`/sdcard/sandbox/{txn_id}/`（**Device 直连 Backend 下载的输入影像**）** |
| 容器化 | Backend 服务 Docker 化，支持 K8s 编排；**V1.3 新增**：`LocalStorageBackend` 需挂载数据卷（如 `/data/attachments`），K8s StatefulSet + PVC |
| 日志格式 | 结构化 JSON，统一字段命名（snake_case） |
| API 规范 | RESTful，OpenAPI 3.0 文档自动生成；**V1.3 新增**：`POST /api/v1/transactions` 支持 multipart/form-data |
| 版本管理 | Git，分支策略：main（生产）、develop（开发）、feature/*（功能） |
| **成本上限（V1.1 新增，V1.2 调整，V1.3 调整）** | **MVP 阶段月成本 ≤ ¥12000**（**V1.3 调整**：原 OSS 按量费被 1TB SSD 替代）：含 ECS 2x（**+1TB SSD/台，V1.3 新增**）、RDS、Redis 4GB、**LocalStorageBackend（无 OSS 费，V1.3 调整）**、SLB、KMS、**Worker 2-3 台 × ¥600/月 = ¥1200-1800** |
| **脚本调试（V1.2 新增）** | **Worker 端脚本支持 PyCharm/VSCode 断点调试（标准 Python 进程）** |

---

## 10. 验收标准

### 10.1 功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| AC-001 | 单笔新保提交 | 提交成功返回 Transaction ID，状态 PENDING |
| AC-002 | 单笔续保提交 | 提交成功返回 Transaction ID，状态 PENDING |
| AC-003 | 批量提交 | 100 条批量提交，部分成功部分失败均可正确返回 |
| AC-004 | 智能路由 | 新保/续保正确识别，绑定对应 Flow |
| AC-005 | Schema 校验 | 缺失必填项时拒绝提交并返回明确错误 |
| AC-006 | 调度分配 | 事务分配至负载最低的 Worker+Device（**V1.2 新增**：不超过 `max_concurrent_devices`） |
| AC-007 | 设备亲和性 | 正常情况下事务全程不切换设备 |
| **AC-008（V1.2 调整）** | **RPA 执行** | **Flow 按 Step 顺序在 Worker 端 Airtest runtime 中执行，截图证据可查** |
| AC-009 | Step 重试 | 单 Step 失败后自动重试，重试次数符合配置（**V1.2 新增**：在 Worker 端控制） |
| AC-010 | 状态流转 | 状态变更 100% 符合状态机定义（**V1.2 新增**：`ADB_CONNECTING` / `READY` 子状态） |
| AC-011 | 文件同步 | Device 完整下载所有影像文件，MD5 校验通过 |
| AC-012 | 断点续传 | 网络中断后恢复下载，文件完整 |
| AC-013 | DLQ 处理 | 连续失败 3 次事务进入 DLQ，运维可重新提交 |
| **AC-014（V1.2 调整）** | **文件清理** | **SUCCESS 事务 Device 沙箱文件立即清理（由 Worker 触发）** |
| AC-015 | Dashboard | 关键指标可视化，数据刷新 ≤30s |
| AC-016 | 审计追溯 | 任一事务可还原完整生命周期 |
| ~~AC-017~~ | ~~用户确认通知~~ | **DEPRECATED (V1.1)**：CONFIRM 流程移除 |
| ~~AC-018~~ | ~~用户确认通过~~ | **DEPRECATED (V1.1)**：同上 |
| ~~AC-019~~ | ~~用户确认拒绝~~ | **DEPRECATED (V1.1)**：同上 |
| ~~AC-020~~ | ~~确认超时自动继续~~ | **DEPRECATED (V1.1)**：同上 |
| AC-017-OSS-URL | **OSS 签名 URL 生成（V1.1 新增，V1.3 调整为下载 URL 通用版本）** | Worker 调用 `/download-urls`（V1.3 重命名自 `/oss-urls`）接口在 200ms 内拿到完整 URL 列表，URL 有效期 5min；V1.3 默认 URL 指向后端自身 |
| AC-018-Direct-OSS | **Device 直连 OSS（V1.1 新增）** | Device 端通过签名 URL 100% 完成下载，**不经** Worker 中转字节流 |
| AC-019-Fail-Audit | **异常截图推送（V1.1 新增）** | 失败事务的截图 30s 内出现在 Dashboard（**V1.2 调整**：截图来源为 Worker 端 Airtest） |
| AC-020-Trans-Timeout | **事务级超时（V1.1 新增）** | 单事务 30 分钟未到终态强制进 DLQ |
| AC-021-Redis-Stream | **Redis Stream 调度（V1.1 新增）** | 调度延迟 P95 ≤ 200ms，事务无重复分配 |
| AC-022-OSS-URL-Refresh | **OSS URL 续签（V1.1 新增）** | 签名 URL 过期前自动续签成功；连续 3 次失败该事务置 FAIL |
| AC-023-Compliance | **数据合规（V1.1 新增）** | 提交时未勾选"单独同意"返回 400；KMS 密钥不可被业务代码导出 |
| AC-021 | 流程脚本上传 | 管理员可上传 .py/.zip 脚本包，上传成功返回版本号；语法错误拒绝 |
| AC-022 | 流程版本管理 | 支持发布、回滚、停用；已发布版本可被 Worker 拉取 |
| AC-023 | 脚本同步 | Worker 启动时校验版本，有新版本时下载并更新本地脚本 |
| AC-024 | 版本更新提示 | Worker 检测到新版本后日志输出更新提示，不阻塞当前任务 |
| AC-025 | 路由规则配置 | 管理员可为每种事务类型配置多个路由规则（含权重百分比） |
| AC-026 | 按百分比分配 | 相同事务类型的大量事务按权重百分比分配到对应 Flow，偏差 ≤5% |
| **AC-NEW-001（V1.2 新增）** | **Worker 端 Airtest 执行** | **Step 100% 在 Worker 端 Airtest runtime 中执行，Device 不再执行 RPA** |
| **AC-NEW-002（V1.2 新增）** | **Device Agent 极简化** | **Device Agent App 包大小 ≤ 5MB（不含 Airtest runtime）** |
| **AC-NEW-003（V1.2 新增）** | **USB ADB 连接** | **Worker 通过 `adb devices` 自动发现并连接 USB Device** |
| **AC-NEW-004（V1.2 新增）** | **ADB 握手状态** | **状态机新增 `ADB_CONNECTING` 子状态可见** |
| **AC-NEW-005（V1.2 新增）** | **沙箱数据流** | **输入影像：OSS → Device（直连，不经 Worker）；Airtest 截图：Worker Airtest → Worker 本地沙箱** |
| **AC-NEW-006（V1.2 新增）** | **Device 下载通知** | **Device 通过 `POST /devices/{id}/download-ack` 通知 Worker** |
| **AC-NEW-007（V1.2 新增）** | **Step 执行** | **Worker Airtest 按 Step.action_type 映射到 Airtest API（OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/WAIT）** |
| **AC-NEW-008（V1.2 新增）** | **单 Worker 负载** | **单 Worker 同时跑 ≤ 3 Device，CPU 使用率 ≤ 80%** |
| **AC-NEW-009（V1.2 新增）** | **沙箱清理** | **事务完成后 Worker + Device 两侧沙箱均清理** |
| **AC-NEW-010（V1.2 新增）** | **Step 重试（Worker 端）** | **Step 失败重试 3 次（指数退避）由 Worker 端控制** |
| **AC-NEW-011（V1.2 新增）** | **Worker 进程崩溃恢复** | **Worker 进程崩溃后该 Worker 所有 Device 事务 60s 内回退 PENDING** |
| **AC-NEW-012（V1.2 新增）** | **桌面 IDE 调试** | **Worker 端脚本可用 PyCharm/VSCode 断点调试** |
| **AC-NEW-013（V1.2 新增）** | **脚本热更新** | **Worker 重启 → 立即可用新脚本（无需下发到 Device）** |
| **AC-NEW-V13-001（V1.3 新增）** | **multipart 事务提交** | **`POST /api/v1/transactions` 接受 multipart/form-data，事务 + 多文件原子提交；服务端成功落地所有文件并返回 `attachment_id` 列表** |
| **AC-NEW-V13-002（V1.3 新增）** | **LocalStorageBackend 默认** | **V1.3 默认后端为 `LocalStorageBackend`，文件落地到 `/data/attachments/{attachment_id}/{filename}`** |
| **AC-NEW-V13-003（V1.3 新增）** | **下载 URL API** | **`POST /transactions/{id}/download-urls` 返回 5min TTL 的签名 URL，V1.3 默认指向 Backend 自身 `GET /api/v1/downloads/{url_id}`** |
| **AC-NEW-V13-004（V1.3 新增）** | **Device 直连下载** | **Device 通过签名 URL 100% 完成下载，URL 指向对 Device 透明** |
| **AC-NEW-V13-005（V1.3 新增）** | **下载 URL 续签** | **URL 过期前自动续签成功；连续 3 次失败该事务置 FAIL（接口路径从 `oss-urls` 改为 `downloads/{url_id}`）** |
| **AC-NEW-V13-006（V1.3 新增）** | **StorageBackend 抽象** | **业务代码通过 `StorageBackend` 接口访问存储；切换后端实现不影响业务代码（需重写单测验证）** |
| **AC-NEW-V13-007（V1.3 新增）** | **存储故障隔离** | **`LocalStorageBackend` 磁盘满时新事务返回 507（Insufficient Storage），不影响其他事务执行** |
| **AC-NEW-V13-008（V1.3 新增）** | **`OssSignedUrl` 标 DEPRECATED** | **新事务不创建 `OssSignedUrl` 记录，仅创建 `DownloadUrl` 记录；旧数据保留可查** |

### 10.2 非功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| NAC-001 | **并发性能（V1.2 调整）** | **50 笔/分钟持续 30 分钟，无异常**（V1.2 保持并发数；ATT 延长 50%） |
| NAC-002 | API 响应 | **P95 ≤ 500ms，** P99 ≤ 1s（V1.1 加 P99） |
| **NAC-003（V1.2 调整）** | **ATT** | **正常事务 RUNNING 阶段 ≤ 8min**（V1.2 由 5min 调整） |
| NAC-004 | 安全审计 | 敏感字段在日志和 API 响应中均脱敏 |
| NAC-005 | 容错恢复 | Worker 宕机后事务 60s 内重新调度 |
| NAC-006 | 扩展验证 | 新增 Worker 自动注册并参与调度 |
| NAC-007 | 可观测性 | 关键指标 Prometheus 拉取成功；Trace 可还原事务完整调用链（**V1.2 扩展**：含 Airtest runtime Span） |
| NAC-008 | 灾备 | DB 主从切换 RTO ≤ 5min；Backend SLB 切流 RTO ≤ 30s |
| **NAC-009（V1.2 新增）** | **单 Worker 并发** | **单 Worker 同时挂载 ≤ 3 Device，CPU < 80%** |
| **NAC-010（V1.2 新增）** | **单站点容量** | **2-3 Worker × 2-3 Device = 4-9 Device/站点** |
| **NAC-011（V1.2 新增）** | **ADB 断开重连** | **ADB 断开后 10s 内自动重连** |
| **NAC-012（V1.2 新增）** | **USB 物理断开检测** | **USB 断开 30s 内 Dashboard 可见告警** |
| **NAC-V13-001（V1.3 新增）** | **存储容量** | **`LocalStorageBackend` 单 Backend 实例支持 ≥ 500GB 影像文件存储；磁盘使用率监控阈值 80%** |
| **NAC-V13-002（V1.3 新增）** | **下载延迟** | **`GET /api/v1/downloads/{url_id}` P95 ≤ 200ms（Backend 服务静态文件）** |
| **NAC-V13-003（V1.3 新增）** | **存储故障 RTO** | **`LocalStorageBackend` 主机故障 RTO ≤ 30min（通过 Backend 双实例 + 文件同步 / DRBD 保障）** |

### 10.3 测试策略（V1.1 新增，V1.2 强化）

**四层测试矩阵。**

| 层级 | 覆盖范围 | 工具 | 通过率要求 | 执行时机 |
|------|----------|------|-----------|----------|
| **L1 单元测试** | 业务逻辑、工具类、Schema 校验、KMS 加解密、**Airtest Step 映射（V1.2 新增）** | pytest | ≥ 80% 行覆盖 | 每次 commit |
| **L2 契约测试** | API 接口契约（OpenAPI）、Worker 设备协议、**Socket 协议（V1.2 简化版）** | schemathesis + pact-python | 100% 契约通过 | 每次 PR |
| **L3 端到端测试** | 完整事务流程（提交 → 调度 → **Worker Airtest 执行（V1.2 强调）** → 审计） | pytest + 真实 Worker/Device 模拟 | 100% 关键路径 | 每次 release |
| **L4 录屏回归** | RPA 脚本在真实 Android 设备上的执行录屏对比 | Airtest 录屏 + 图像 diff | 100% 关键步骤 | 每次 Flow 版本发布 |

**L4 录屏回归是 RPA 系统的关键。** 保险 APP 任何 UI 变更都会导致脚本失活，**没有录屏回归测试 = 在黑暗中飞行**。每次 Flow 版本发布前必须回放至少 100 条历史事务的录屏，与基线对比，差异 > 阈值则阻止发布。

**V1.2 L4 录屏回归权重提升。** 由于脚本执行位置由 Device 端迁至 Worker 端 Airtest runtime：
- 录屏采集点改为 Worker 端（通过 `airtest.core.android.adb` screen record）
- 录屏回归对比基线更容易维护（脚本在桌面 Python 进程，可直接复现）
- L4 测试从 5% 提升至 **10%**（V1.2 强化）

**桌面 IDE 调试便利（V1.2 新增）。** Worker 端脚本为标准 Python 进程，开发者可用 PyCharm/VSCode 断点调试：
- 在 IDE 中设置断点 → 启动 Worker 进程 → 触发事务 → 断点命中
- 单步执行 Airtest API 调用，查看 UI 控件树
- 此能力是 V1.1 Device 端 Airtest 架构无法实现的（Device 端没有 IDE）

**测试金字塔比例。**
- L1 单元测试：65%（**V1.2 由 70% 调整**，因 L4 占比上升）（覆盖各 FR 的核心逻辑 + Airtest 映射）
- L2 契约测试：15%（API 兼容性 + Worker/Device 协议 + 简化版 Socket）
- L3 端到端测试：10%（关键流程穿越）
- **L4 录屏回归：10%（V1.2 由 5% 上调）**（每 Flow 100 条样本）

**测试环境。**
- 开发环境：单机 docker-compose，包含 Backend + DB + Redis + Mock Device
- 预发环境：1 套 MVP 规模部署，真实 Worker + 真机（用于 L4）
- 生产环境：1% 流量灰度（用于 A/B 验证）

---


## 11. 风险与依赖

### 11.1 已知风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 保险 APP UI 变更导致 RPA 脚本失效 | 事务执行 FAIL | 高 | Step 级重试+截图对比检测；Flow 版本化管理，快速更新；**L4 录屏回归（V1.2 权重提升至 10%）** |
| Android 系统升级导致 Airtest 兼容问题 | Device 不可用 | 中 | Device Controller 抽象层；预留多版本 ADB 兼容 |
| 大量并发事务导致调度瓶颈 | 事务积压 | 中 | **V1.1 已用 Redis Stream 缓解**；后续 MQ 削峰 |
| **业务类型误选（V1.1 新增）** | 事务路由到错误 Flow，提交后才发现 | 中 | 用户提交时强制二次确认；提交后状态可见 |
| 影像文件体积过大导致下载超时 | Device 下载 FAIL | 低 | 文件压缩；分片下载；超时熔断 |
| **OSS 签名 URL 泄漏（V1.1 新增，V1.3 移除）** | ~~影像文件被未授权访问~~ | ~~低~~ | ~~V1.3 起 OSS 签名 URL 不再被 Device 直接使用，V1.3 默认 `LocalStorageBackend` 由 Backend 自身服务签名；OSS 仅作为 V1.4+ 扩展后端，此风险随 OSS 启用时重新评估~~ |
| **KMS 不可用（V1.1 新增）** | 事务提交/查询全 FAIL | 低 | 多区域 KMS 备份；本地缓存非敏感数据 |
| ~~**ADB 反检测（V1.1 风险，V1.2 移除）**~~ | ~~事务 FAIL~~ | ~~中~~ | ~~**已 PoC 验证**：目标保险 APP 对 ADB 注入无检测反应，风险移除~~ |
| **Worker CPU 瓶颈（V1.2 新增）** | **单 Worker 仅 2-3 Device，并发能力下降** | **高** | **接受限制；按需扩容 Worker 数量；监控 CPU 阈值（> 80% 告警）** |
| **单事务 ATT 延长 50%（V1.2 新增）** | **从 3-5min 到 5-8min** | **高** | **业务方接受；优化 Airtest 脚本；ADB 性能调优** |
| **Worker 进程崩溃影响扩大（V1.2 新增）** | **1 Worker 故障 = 2-3 Device 事务中断** | **中** | **限制单 Worker 负载；快速故障检测（心跳 30s）；事务自动回退 PENDING** |
| **USB 物理连接不稳定（V1.2 新增）** | **接触不良导致 ADB 断开，事务中断** | **中** | **优质 USB 线材；ADB 自动重连（≤ 10s）；事务回退 PENDING** |
| **Airtest 截图/图像识别失败（V1.2 新增）** | **UI 变化导致 Step 失败** | **中** | **L4 录屏回归（V1.2 提升权重）；Step 重试机制；快速脚本更新** |
| **本地存储容量风险（V1.3 新增）** | **`LocalStorageBackend` 单机磁盘写满 → 新事务提交失败 507** | **中** | **监控磁盘使用率 > 80% 告警；定期清理过期附件（事务完成后 > 7 天）；中期切换 `OssStorageBackend` 扩展** |
| **Backend 单点存储（V1.3 新增）** | **`LocalStorageBackend` Backend 主机故障 → 文件不可访问、事务 FAIL** | **中** | **Backend 双实例 + 文件同步（如 DRBD / rsync / 共享存储）；RTO 取决于同步策略；中期切换 `OssStorageBackend` 消除单点** |
| **存储后端切换兼容性（V1.3 新增）** | **`LocalStorageBackend` → `OssStorageBackend` 切换时历史事务的 URL 失效** | **中** | **切换前批量预热新后端 URL；历史事务在切换后 7 天内允许强制重新生成 URL** |

### 11.2 外部依赖

| 依赖项 | 说明 | 风险 |
|--------|------|------|
| 保险 APP | RPA 操作的目标应用，需保持版本稳定 | APP 更新可能导致脚本失效 |
| **Android USB 连接（V1.2 强调）** | **Worker 与 Device 的物理连接（V1.2 升级为强依赖）** | **USB 线材/接口老化导致 ADB 断开** |
| 网络 | Worker/Device 与 Backend 通信 | 网络抖动影响任务下发和文件下载 |
| **KMS 服务（V1.1 新增）** | 敏感字段加解密 | 服务不可用导致全事务 FAIL；需多区域备份 |
| **Redis 服务（V1.1 新增）** | 任务队列 + 缓存 | 服务不可用导致任务无法调度；需 Sentinel 高可用 |
| **OSS 地域（V1.1 新增）** | 影像文件存储 | 地域故障导致文件不可访问；需异地只读副本（V1.3 规划） |
| **Airtest + pocoui 依赖（V1.2 新增）** | **Worker 端 UI 自动化框架** | **依赖版本升级可能引入兼容问题；需固定版本 + 锁依赖** |
| **ADB 工具（V1.2 新增）** | **Worker 与 Device 通信** | **ADB 版本差异可能导致连接异常；需在 Worker 端固定 ADB 版本** |

**V1.1 移除的依赖：**
- ~~OCR 服务~~：业务类型由用户提交时显式指定，不再需要 OCR 识别
- ~~callback_url 字段~~：CONFIRM 流程移除后不再需要

### 11.3 假设前提

| 编号 | 假设 |
|------|------|
| AS-001 | 保险 APP 在 Android 设备上可正常安装和运行 |
| AS-002 | Worker 桌面端为 Linux/Windows 系统，可稳定运行 Python 环境 |
| AS-003 | **业务类型由用户在提交时显式指定**（V1.1 重写） |
| AS-004 | 所有 Android 设备已开启 USB 调试和开发者模式 |
| AS-005 | Worker 与 Device 通过 USB 稳定连接，局域网网络通畅 |
| AS-006 | 对象存储服务可用（MinIO 或 S3 兼容） |
| AS-007（V1.1 新增，V1.3 调整为 AS-013） | ~~OSS 桶域名需公网可访问（Device 直连下载前提）~~ | **V1.3 起移除**：V1.3 不再依赖 OSS 直连，下载 URL 指向 Backend 自身；原 AS-007 由 AS-013 替代 |
| AS-008（V1.1 新增） | **KMS 服务跨地域高可用**（任一区域故障不影响业务） |
| AS-009（V1.1 新增） | **客户已确认 OSS 存储地域在合规范围内**（无跨境合规问题） |
| **AS-010（V1.2 新增）** | **Worker 与 Device 间 USB 物理连接稳定（ADB 不断开）；单 Worker 限挂载 2-3 Device** |
| **AS-011（V1.2 新增）** | **目标保险 APP 对 ADB 注入无检测反应（已 PoC 验证）** |
| **AS-012（V1.2 新增）** | **Airtest 框架对目标保险 APP 的 UI 操作可识别（图像/POCO）** |
| **AS-013（V1.3 新增）** | **Backend 服务可对外暴露 `GET /api/v1/downloads/{url_id}` 端点（公网或局域网均可，Device 需能直连）** |

### 11.4 决策记录（V1.2 新增）

本节记录 V1.2 架构调整的关键决策点。

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| RPA 引擎位置 | Device 端 / Worker 端 | **Worker 端** | 脚本集中、调试便利、Device 简化 |
| 控制链路 | USB / WiFi ADB | **USB**（MVP） | 稳定、低延迟、MVP 推荐 |
| ADB 反检测风险 | 接受 / 不接受 | **已 PoC 验证接受** | 目标保险 APP 无检测反应 |
| 单 Worker 负载 | 高 / 中 / 低 | **低（2-3 Device）** | CPU 瓶颈 + 业务方接受 |
| 交付物 | 设计文档 / 直接改 PRD | **先架构设计文档，再更新 PRD（V1.2）** | 先评审后落地 |
| Device 端 Airtest runtime | 保留 / 移除 | **移除** | 极简 Device Agent |
| 沙箱位置 | Device 端 / Worker 端 | **Device 端（输入影像）+ Worker 端（Airtest 截图），分离存储** | 输入影像不经 Worker 中转 |
| 单站点 Worker 数 | 1 / 2-3 / 4+ | **2-3**（MVP） | 平衡成本与扩展性 |
| 销售 API 限流 | 60/min / 40/min / 30/min | **40/min** | ATT 延长 50% 后的容量平衡 |
| 月成本上限 | ¥8000 / ¥12000 / ¥15000 | **¥12000** | 含 2-3 台 Worker × ¥600/月 |

### 11.5 决策记录（V1.3 新增）

本节记录 V1.3 存储架构调整的关键决策点。

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| 存储后端默认 | OSS-first（V1.1/V1.2） / Server-first（V1.3） | **Server-first（V1.3）** | MVP 简单、低成本、运维自主；未来可扩展 OSS |
| 客户端上传方式 | JSON + file_url / multipart/form-data | **multipart/form-data（一步上传）** | 事务+文件原子性、UX 简单 |
| Device 下载源 | 直连 OSS / 直连 Backend / Worker 中转 | **直连 Backend（V1.3）** | 保留 "Device 直连" 架构优点；URL 来源由后端决定 |
| StorageBackend 抽象 | 仅存储 / 存储 + 签名 URL | **存储 + 签名 URL 统一抽象** | 业务代码完全无感；切换后端零成本 |
| OssSignedUrl 实体 | 保留 / 替换 | **替换为 DownloadUrl**（通用后端无关） | V1.3 抽象更彻底；OssSignedUrl 标 DEPRECATED |
| 单 Backend 磁盘 | 500GB / 1TB / 2TB | **1TB SSD × 2 实例** | 500 笔/日 × 5MB × 30 天 ≈ 75GB/月，预留 8 个月 + 80% 冗余 |
| V1.2 → V1.3 迁移策略 | 一次性切换 / 渐进式双轨 / 历史数据迁回 | **渐进式双轨 3 个月** | 不影响在途事务；新事务强制 multipart；3 个月后清空旧接口 |

---

## 12. 发布与变更管理（V1.1 新增，V1.2 扩展）

| 项 | 规范 |
|------|------|
| **发布节奏** | Backend 服务：2 周一次（周二发布窗口）；Flow 脚本：业务方按需申请（≤ 1 次/周）；**V1.2 新增**：Worker 客户端发布节奏可与 Backend 解耦（独立发布） |
| **灰度策略** | 新版本 Backend 先发布 1 个 Pod，10% 流量验证 30min，再扩到 50%、100% |
| **回滚 SLA** | Backend：≤ 5min（K8s 滚动回滚）；Flow 脚本：≤ 1min（修改 current_version 指向旧版本）；**V1.2 新增**：Worker 客户端回滚 ≤ 5min（Worker 进程重启） |
| **强制升级** | Worker/Device 端版本低于 N-2 时拒绝注册（必须升级） |
| **变更窗口** | 生产环境变更窗口：周二/周四 14:00-17:00（业务低峰期） |
| **变更通知** | 提前 24h 在运维群通知；变更后 1h 内发布变更报告 |
| **回滚流程** | 触发条件：5xx 错误率 > 5% 持续 5min / P1 告警 / 业务方紧急请求；执行：K8s `kubectl rollout undo` |
| **客户端兼容性** | Backend API 保持前 2 个版本兼容；强制升级时仅弃用 v(N-2) |
| **架构变更发布（V1.2 新增，V1.3 扩展）** | **V1.1 → V1.2 升级采用双轨并行（V1.1 架构保留为 Plan B），3 个月观察期后切流到 V1.2**；**V1.3 新增**：V1.2 → V1.3 升级采用"渐进式迁移"——Backend 部署 V1.3 代码后，旧 `POST /transactions`（带 `file_url`）仍可作为过渡期兼容接口运行 3 个月；3 个月后强制要求 multipart 上传；存储层 V1.3 默认 `LocalStorageBackend`，历史 OSS 附件保留可读 |

---

## 13. 运营手册索引（V1.1 新增，V1.2 扩展）

**详细操作 Runbook 维护在独立文档 `docs/superpowers/runbooks/`。本节仅提供索引。**

| 场景 | Runbook | 链接 |
|------|---------|------|
| 新增 Worker 节点 | RB-WORKER-ONBOARD | `runbooks/worker-onboard.md` |
| **Worker 端 Airtest 部署（V1.2 新增）** | **RB-WORKER-AIRTEST-DEPLOY** | `runbooks/worker-airtest-deploy.md` |
| 新增 Android 设备 | RB-DEVICE-ONBOARD | `runbooks/device-onboard.md` |
| **ADB 连接问题排查（V1.2 新增）** | **RB-ADB-CONNECT-ISSUE** | `runbooks/adb-connect-issue.md` |
| **Worker 进程崩溃恢复（V1.2 新增）** | **RB-WORKER-CRASH-RECOVER** | `runbooks/worker-crash-recover.md` |
| Worker 离线恢复 | RB-WORKER-OFFLINE | `runbooks/worker-offline.md` |
| 事务积压告警 | RB-TRANS-BACKLOG | `runbooks/trans-backlog.md` |
| DLQ 事务处理 | RB-DLQ-HANDLING | `runbooks/dlq-handling.md` |
| Flow 脚本发布 | RB-FLOW-RELEASE | `runbooks/flow-release.md` |
| **桌面 IDE 调试脚本（V1.2 新增）** | **RB-FLOW-DEBUG-IDEA** | `runbooks/flow-debug-idea.md` |
| 数据库主从切换 | RB-DB-FAILOVER | `runbooks/db-failover.md` |
| Redis 主从切换 | RB-REDIS-FAILOVER | `runbooks/redis-failover.md` |
| OSS 桶切换 | RB-OSS-SWITCH | `runbooks/oss-switch.md` |
| KMS 不可用 | RB-KMS-DOWN | `runbooks/kms-down.md` |
| 全自动失败率突增 | RB-AUTO-FAIL-SURGE | `runbooks/auto-fail-surge.md` |
| 客户合规审计准备 | RB-COMPLIANCE-AUDIT | `runbooks/compliance-audit.md` |
| **存储后端切换（V1.3 新增）** | **RB-STORAGE-BACKEND-SWITCH** | `runbooks/storage-backend-switch.md` |
| **本地存储磁盘满（V1.3 新增）** | **RB-STORAGE-DISK-FULL** | `runbooks/storage-disk-full.md` |
| **存储后端故障恢复（V1.3 新增）** | **RB-STORAGE-BACKEND-RECOVER** | `runbooks/storage-backend-recover.md` |
| **V1.2 → V1.3 渐进式迁移（V1.3 新增）** | **RB-V13-MIGRATION** | `runbooks/v13-migration.md` |

---

## 14. 开放问题（V1.1 新增，V1.2 扩展）

需要在 V1.2 进入 `Review` / `Approved` 状态前与业务方/合规方/运维方确认：

### V1.1 遗留开放问题

- **Q1.** 销售团队能接受"机器人提交后无法撤回"吗？（影响 V1.x CONFIRM 移除是否可逆）
- **Q2.** 当前保险 APP 的 UI 稳定性？最近半年更新频次？（影响 AS-001 假设）
- **Q3.** 业务类型误选的事务事后如何处理？回退 + 重新提交？人工干预？（影响 AC 误选事务的回收流程）
- **Q4.** 客户对数据存储地域有要求吗？（影响 OSS 选型与 §2.5 合规）
- **Q5.** 是否需要支持"中途人工接管"（机器人失败时人继续填）？（影响 FR-MOB 是否新增"接管"接口）
- **Q6.** DPoP（数据主体权利）API 的访问控制是单独的 DPoP 角色还是复用"数据主体"角色？身份认证用手机号 + 验证码还是其他方式？（影响 §2.5 的 DPoP 实现细节）

### V1.2 架构调整新增开放问题（引用架构设计文档）

以下 5 项为 V1.2 架构调整引入的开放问题，详见 `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` §12。

- **Q7.** 业务方是否接受"5-8 分钟 ATT + 单 Worker 2-3 Device"？（决定 MVP 范围，引用架构设计文档 Q1）
- **Q8.** 单站点月成本从 ¥300 升至 ¥1200-1800 是否在预算内？（影响 §9 成本上限，引用架构设计文档 Q2）
- **Q9.** 多站点推广时，是否有运维能力支撑每站点 2-3 Worker 的维护？（影响 SLA，引用架构设计文档 Q3）
- **Q10.** Airtest 脚本编写规范是否需要统一？（影响 FR-SVR-016 流程脚本上传，引用架构设计文档 Q4）
- **Q11.** 是否需要 WiFi ADB 支持（除 USB 外）作为扩展能力？（影响 §6 接口，引用架构设计文档 Q5）

### V1.3 存储架构调整新增开放问题

以下 4 项为 V1.3 存储架构调整引入的开放问题。

- **Q12.** Backend 单实例磁盘 1TB 是否足够 MVP 阶段？（500 笔/日 × 平均 5MB/笔 × 30 天 ≈ 75GB/月，预留 80% 冗余约 1TB 满足 8 个月容量；影响 §7.5 硬件规格）
- **Q13.** `LocalStorageBackend` 主机故障时是否需要立即切换 `OssStorageBackend` 作为灾备？还是采用 Backend 双实例 + DRBD 文件同步即可？（影响 §11 风险缓解策略）
- **Q14.** V1.2 → V1.3 渐进式迁移期 3 个月是否足够清空 V1.2 历史 `file_url` 事务？（影响 §12 双轨并行时长；需结合客户实际业务回看周期）
- **Q15.** 未来切换 `OssStorageBackend` 时，是否需要支持"事务中"切换（即事务进行中也能无缝跨后端）？（影响 `StorageBackend` 接口是否需引入"事务性"约束；当前实现按事务级隔离，事务内不切换）

---

## 15. 关联文档（V1.2 新增，V1.3 扩展）

| 文档 | 路径 | 关系 |
|------|------|------|
| **架构设计文档（V1.2 依据）** | `docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md` | V1.2 的技术决策来源 |
| 前一版本 PRD | `docs/superpowers/specs/2026-06-02-prd-design.md`（V1.1） | V1.2 / V1.3 的修订基础 |
| V1.2 PRD | `docs/superpowers/specs/2026-06-04-prd-design.md` | V1.3 的直接修订基础；V1.3 沿用 V1.2 架构 + 应用存储调整 |
| PRD 评审意见 | `docs/superpowers/specs/2026-06-02-prd-review.md` | V1.1 评审结论 |
| Airtest 选型对比 | `docs/superpowers/specs/2026-06-03-airtest-vs-autoxjs-comparison.md` | Airtest 选型依据 |
| Android 设备 Airtest 架构（旧） | `docs/superpowers/specs/2026-06-03-android-device-airtest-architecture-design.md` | V1.1 架构，V1.2 保留为 Plan B |
| Android 设备 AutoXjs 架构 | `docs/superpowers/specs/2026-06-03-android-device-autoxjs-architecture-design.md` | 备选方案 |

---

**文档状态推进路径**：

`Draft`（当前）→ `Review`（业务方/合规方/运维方签字）→ `Approved` → `Frozen`

**V1.2 评审重点**：

1. **架构级偏移的接受度**：业务方是否接受"5-8 分钟 ATT + 单 Worker 2-3 Device"？（引用架构文档 Q1）
2. **成本上升的预算**：单站点月成本 ¥1200-1800 是否在预算内？（引用架构文档 Q2）
3. **运维能力匹配**：多站点推广时 2-3 Worker/站点的运维能力是否具备？（引用架构文档 Q3）
4. **Airtest 脚本规范**：是否需要统一的脚本编写规范？（引用架构文档 Q4）
5. **WiFi ADB 扩展性**：除 USB 外是否需要 WiFi ADB 支持？（引用架构文档 Q5）

**V1.3 评审重点**（在 V1.2 评审基础上增加）：

6. **存储后端 Server-first 接受度**：业务方是否接受"文件存储在后端本地 SSD"？是否要求数据物理隔离要求必须在对象存储？（Q12）
7. **Backend 磁盘容量规划**：单 Backend 实例 1TB SSD 是否满足业务量？（Q12）
8. **存储后端灾备策略**：是 Backend 双实例 + DRBD，还是切 `OssStorageBackend` 灾备？（Q13）
9. **V1.2 → V1.3 迁移期长度**：3 个月渐进式迁移期是否足够？（Q14）
10. **历史 OSS 附件处理**：V1.2 历史的 OSS 附件是否需要在 V1.3 部署时批量迁回 Backend？

