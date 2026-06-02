# 3IS-Auto-App 产品需求说明书（PRD）

## 文档信息

| 字段 | 内容 |
|------|------|
| 产品名称 | 3IS-Auto-App（车险保单自动生成 RPA 系统） |
| 文档版本 | V1.0 |
| 创建日期 | 2026-06-02 |
| 文档状态 | Draft |

### 修订记录

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-02 | 初始版本 | - |

### 术语表

| 术语 | 定义 |
|------|------|
| Transaction | 一次完整的保单录入事务，从资料提交到结果回传的全过程 |
| Worker | 安装在桌面端的客户端代理，负责接收调度指令并编排 RPA 执行 |
| Device | 挂载在 Worker 上的 Android 设备，执行实际的保单录入操作 |
| Flow | 一个完整的 RPA 流程定义，由多个有序 Step 组成 |
| Step | Flow 中的单个操作步骤，如"打开APP"、"填写表单"、"上传照片"、"等待用户确认" |
| CONFIRM Step | 一种特殊 Step 类型，执行时截取屏幕截图推送至用户确认，确认后继续执行 |
| DLQ | Dead Letter Queue，死信队列，用于隔离连续失败的事务 |
| ATT | Average Transaction Time，事务平均执行时长 |
| SN/UDID | Android 设备序列号/唯一设备标识 |
| Attachment | 事务关联的影像文件，数量不限，用户可自由上传 |
| SLB/CLB | 云负载均衡服务（阿里云 SLB / 腾讯云 CLB） |
| OSS/COS | 云对象存储服务（阿里云 OSS / 腾讯云 COS） |

---

## 1. 产品概述

### 1.1 背景

车险投保流程涉及大量影像资料的人工录入（身份证、行驶证、合格证、发票等），耗时长、易出错、人力成本高。

### 1.2 目标

构建分布式、高可用的 RPA 编排平台，实现投保资料的自动化录入与处理，覆盖新保单和续保单两种场景。

### 1.3 价值主张

- 将单笔保单录入时间从人工 15-20 分钟降至自动化 3-5 分钟
- 消除人工录入的格式错误和遗漏
- 支持多设备并行处理，线性扩展吞吐量
- 全流程可审计、可追溯

### 1.4 范围边界

| In Scope | Out of Scope |
|----------|-------------|
| 新保单/续保单的智能识别与路由 | 保单核保与定价逻辑 |
| 影像资料的上传、校验、分发 | 保险公司核心业务系统 |
| 多设备集群调度与负载均衡 | OCR 识别能力（假设外部服务提供） |
| RPA 流程编排与步骤级重试 | iOS 设备支持（未来扩展） |
| 全链路状态监控与审计日志 | 支付/出单环节 |

---

## 2. 用户角色与权限

### 2.1 角色定义

| 角色 | 描述 | 核心操作 |
|------|------|----------|
| 销售人员 | 提交投保资料的业务人员 | 提交保单资料（Web/API）、查看事务状态 |
| 运维管理员 | 监控系统运行状态的运维人员 | 查看 Dashboard、管理设备池、处理 DLQ 事务 |
| 系统管理员 | 系统配置与权限管理 | 管理用户/角色、配置校验规则、管理 Flow 定义 |
| Worker 节点 | 桌面端客户端代理（系统角色） | 注册/心跳、接收任务、编排 RPA 执行、上报结果 |
| Android 设备 | 移动端执行代理（系统角色） | 下载影像资料、执行 RPA 脚本、上报执行状态 |

### 2.2 权限矩阵

| 操作 | 销售人员 | 运维管理员 | 系统管理员 | Worker | Device |
|------|:--------:|:----------:|:----------:|:------:|:------:|
| 提交保单资料 | Y | Y | Y | - | - |
| 查看事务状态（自有） | Y | - | - | - | - |
| 查看所有事务 | - | Y | Y | - | - |
| 管理设备池 | - | Y | Y | - | - |
| 处理 DLQ 事务 | - | Y | Y | - | - |
| 管理用户/角色 | - | - | Y | - | - |
| 配置校验规则 | - | - | Y | - | - |
| 管理 Flow 定义 | - | - | Y | - | - |
| 注册/心跳 | - | - | - | Y | - |
| 接收/执行任务 | - | - | - | Y | Y |
| 下载影像资料 | - | - | - | - | Y |
| 查看 Dashboard | - | Y | Y | - | - |

---

## 3. 业务流程

### 3.1 主流程（端到端）

```
销售人员提交资料 → [事务接入] → 智能路由(新保/续保) → Schema校验
    → 生成Transaction ID → [调度中心] → 选择Worker+Device
    → 状态: DISPATCHED → Worker接收任务 → 通知Device下载资料
    → Device下载影像 → 状态: DOWNLOADING → 下载完成 → 状态: RUNNING
    → RPA脚本执行(多Step) → 执行完成 → 结果回传
    → 状态: SUCCESS/FAIL → 销售人员查看结果
```

### 3.2 新保单流程

输入资料：影像文件（不限制数量和张数，可能包含身份证、车辆合格证、发票等）、手机号码

```
提交资料 → 校验(至少1份影像+手机号) → 路由至新保Flow
→ Step1: 打开保险APP → Step2: 选择新保入口
→ Step3: 填写手机号 → Step4~StepN: 逐张上传影像资料
→ StepN+1: 提交表单 → StepN+2: 截图等待用户确认(CONFIRM)
→ StepN+3: 确认后提交/完成
```

### 3.3 续保单流程

输入资料：影像文件（不限制数量和张数，可能包含身份证、行驶证等）、手机号码

```
提交资料 → 校验(至少1份影像+手机号) → 路由至续保Flow
→ Step1: 打开保险APP → Step2: 选择续保入口
→ Step3: 填写手机号 → Step4~StepN: 逐张上传影像资料
→ StepN+1: 提交表单 → StepN+2: 截图等待用户确认(CONFIRM)
→ StepN+3: 确认后提交/完成
```

### 3.4 状态机

```
PENDING → DISPATCHED → DOWNLOADING → RUNNING → SUCCESS
                                              → FAIL
                                                  → RETRY → RUNNING (最多N次)
                                                  → DLQ (终态失败)
RUNNING → WAITING_CONFIRM → RUNNING (用户确认后继续)
                            → RUNNING (超时自动继续)
```

| 状态 | 触发条件 | 说明 |
|------|----------|------|
| PENDING | 事务创建，校验通过 | 等待调度 |
| DISPATCHED | 调度中心分配 Worker+Device | 任务已下发 |
| DOWNLOADING | Device 开始下载影像资料 | 资料传输中 |
| RUNNING | 下载完成，RPA 脚本开始执行 | 自动化操作中 |
| WAITING_CONFIRM | 执行到 CONFIRM 类型 Step，截图已推送用户 | 等待用户确认 |
| SUCCESS | RPA 执行完成，结果验证通过 | 正常终态 |
| FAIL | 执行异常/超时/校验失败 | 可重试 |
| DLQ | 连续失败超过阈值 | 死信队列，需人工介入 |

### 3.5 异常分支

- **文件下载失败**：Device 侧断点续传，超过重试次数后状态置为 FAIL
- **RPA 步骤失败**：Step 级重试（按 Retry Policy），全部重试耗尽后事务 FAIL
- **Worker 宕机**：服务端心跳超时检测，事务回退至 PENDING 重新调度
- **Device 离线**：调度中心跳过该设备，重新选择可用设备
- **用户确认超时**：超过 confirm_timeout_ms 未确认，自动视为通过，继续执行后续 Step

---

## 4. 功能需求

### 4.1 服务端功能（FR-SVR-xxx）

#### FR-SVR-001 销售人员 Web 门户提交

| 字段 | 内容 |
|------|------|
| 描述 | 销售人员通过 Web 表单手动提交单笔保单资料 |
| 输入 | 业务类型（新保/续保）、手机号、身份证号、影像文件（image/pdf，数量不限） |
| 输出 | Transaction ID、提交时间戳、初始状态 PENDING |
| 规则 | 文件大小单张 ≤10MB；图片格式 jpg/png/jpeg；PDF 单文件 ≤20MB |
| 验收 | 提交成功返回 Transaction ID；缺失必填项返回 400 错误且提示具体字段 |

#### FR-SVR-002 REST API 批量推送

| 字段 | 内容 |
|------|------|
| 描述 | 第三方系统通过 REST API 批量推送保险人信息 |
| 输入 | 数组形式的保单数据（每条含业务类型、客户信息、影像URL或base64） |
| 输出 | 每条记录对应的 Transaction ID 列表、失败明细 |
| 规则 | 单次批量 ≤100 条；API 需携带 Bearer Token；幂等性通过外部业务ID保障 |
| 验收 | 批量提交支持部分成功；失败条目返回原因码；重复 externalId 不重复创建事务 |

#### FR-SVR-003 智能业务路由

| 字段 | 内容 |
|------|------|
| 描述 | 系统自动判别"新保/续保"类型并动态加载校验规则 |
| 输入 | 提交的资料元数据（含业务类型字段或资料组合） |
| 输出 | 路由后的事务（绑定对应 Flow ID） |
| 规则 | 新保：至少包含 1 份影像资料+手机号；续保：至少包含 1 份影像资料+手机号；不限制上传文件数量 |
| 验收 | 影像数量 ≥1 即可路由；0 份影像资料时事务置为 FAIL 并提示缺项 |

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
| 规则 | 算法：最小连接数 + 权重轮询；不分配给负载>80%的 Worker |
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
| 规则 | 禁止非法状态跳转（如 PENDING 直接到 SUCCESS）；变更操作幂等 |
| 验收 | 状态流转 100% 符合定义；非法变更被拒绝并记录告警 |

#### FR-SVR-009 客户端注册中心

| 字段 | 内容 |
|------|------|
| 描述 | 管理 Worker 节点的注册、心跳、版本、能力标签 |
| 输入 | Worker 注册请求（含本机指纹、版本号、Tag）、心跳包 |
| 输出 | 注册确认、Worker 列表查询接口 |
| 规则 | 心跳周期 ≤30s；连续 3 次未收到心跳标记为 OFFLINE |
| 验收 | Worker 上下线状态实时更新；OFFLINE 后任务自动回收 |

#### FR-SVR-010 设备池管理

| 字段 | 内容 |
|------|------|
| 描述 | 维护 Android 设备的唯一标识、在线状态、占用情况 |
| 输入 | Worker 上报的设备列表（含 SN/UDID、电量、存储） |
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
| 规则 | 数据刷新间隔 ≤30s；支持按时间范围/Worker/Device 筛选 |
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

| 字段 | 内容 |
|------|------|
| 描述 | RPA 执行到 CONFIRM 类型 Step 时，将截图推送至提交用户进行确认 |
| 输入 | Transaction ID、Step execution ID、截图 URL、确认提示文案 |
| 输出 | 用户确认结果（通过/拒绝）或超时自动通过 |
| 规则 | 通知渠道：Web 页面通知 + API 回调（如有配置 callback_url）；事务状态变更为 WAITING_CONFIRM；超时时间可配置（默认 30min），超时自动视为通过并继续执行 |
| 验收 | 截图在 3s 内送达用户；用户确认后事务立即恢复 RUNNING；超时后自动继续并记录日志 |

#### FR-SVR-015 用户确认回调

| 字段 | 内容 |
|------|------|
| 描述 | 支持通过 API 回调通知第三方系统有待确认的截图 |
| 输入 | 事务提交时配置的 callback_url、确认请求体（含截图URL、事务信息） |
| 输出 | 回调响应 |
| 规则 | 回调失败重试 3 次（指数退避）；回调与 Web 通知并行发送；callback_url 在事务提交时可选配置 |
| 验收 | 回调在 5s 内送达；失败重试不影响 Web 通知通道 |

### 4.2 客户端功能（FR-CLI-xxx）

#### FR-CLI-001 自动注册

| 字段 | 内容 |
|------|------|
| 描述 | 客户端启动时向服务端注册 |
| 输入 | 本机指纹（MAC/主机名/CPU序列号哈希）、版本号、已连接 Android 设备列表 |
| 输出 | 服务端返回的 Worker ID、Token |
| 规则 | Token 有效期 24h，自动续期；注册失败重试 3 次后退出 |
| 验收 | 首次启动注册成功；重启后保持原 Worker ID |

#### FR-CLI-002 状态同步

| 字段 | 内容 |
|------|------|
| 描述 | 周期性上报本机及挂载设备的健康度 |
| 输入 | 本机 CPU/内存/磁盘、设备电量/存储/锁屏状态 |
| 输出 | 心跳包（含上述指标） |
| 规则 | 心跳间隔 30s；指标异常（如设备电量<20%）触发告警 |
| 验收 | 服务端 Dashboard 实时反映客户端状态 |

#### FR-CLI-003 指令监听

| 字段 | 内容 |
|------|------|
| 描述 | 实时接收服务端下发的任务指令 |
| 输入 | 服务端推送的任务消息 |
| 输出 | 任务接收确认 |
| 规则 | 优先使用 WebSocket；断线降级为长轮询；断线自动重连 |
| 验收 | 任务下发延迟 ≤1s；断网恢复后自动重新订阅 |

#### FR-CLI-004 数据拉取

| 字段 | 内容 |
|------|------|
| 描述 | 根据任务指令下载客户元数据及影像附件到本地加密沙箱 |
| 输入 | Transaction ID、元数据 URL、附件 URL 列表 |
| 输出 | 本地加密沙箱中的文件路径 |
| 规则 | 沙箱目录权限 700；文件 AES-256 加密；下载完成后通知 Device 同步 |
| 验收 | 文件下载完整；非本进程无法读取；事务结束后文件清理 |

#### FR-CLI-005 RPA 编排器

| 字段 | 内容 |
|------|------|
| 描述 | 编排 Flow → Steps 的执行流程 |
| 输入 | Flow 定义（含 Steps 顺序、参数、Retry Policy） |
| 输出 | 各 Step 的执行结果、最终事务结果 |
| 规则 | 支持 Step 级重试（默认 3 次，指数退避）；支持 Step 超时熔断（默认 60s/Step）；遇到 CONFIRM 类型 Step 时截取屏幕截图，上报服务端并暂停执行，等待用户确认或超时后继续 |
| 验收 | Flow 按定义顺序执行；任一 Step 失败触发重试；超时不阻塞整体流程；CONFIRM Step 正确暂停/恢复 |

#### FR-CLI-006 结果回传

| 字段 | 内容 |
|------|------|
| 描述 | 执行完毕后向服务端上报结果 |
| 输入 | 事务执行结果、截图证据、各 Step 耗时 |
| 输出 | 服务端确认回传 |
| 规则 | 回传失败重试 5 次；截图压缩后上传（JPEG quality 70） |
| 验收 | 服务端可查询到完整执行记录和截图；上报延迟 ≤5s |

### 4.3 移动端功能（FR-MOB-xxx）

#### FR-MOB-001 任务监听

| 字段 | 内容 |
|------|------|
| 描述 | Android Agent 监听桌面客户端或服务端的指令 |
| 输入 | 指令消息（Socket/HTTP） |
| 输出 | 指令接收确认 |
| 规则 | 监听端口可配置（默认 8765）；仅接受白名单 IP 连接 |
| 验收 | 指令接收延迟 ≤1s；非白名单连接被拒绝 |

#### FR-MOB-002 文件同步

| 字段 | 内容 |
|------|------|
| 描述 | 根据 Transaction ID 从服务端下载影像资料 |
| 输入 | Transaction ID、文件清单 |
| 输出 | 本地指定目录的文件 |
| 规则 | 支持断点续传；下载完成后做 MD5 校验；存储路径可配置 |
| 验收 | 文件 100% 完整下载；网络中断后可恢复；MD5 不匹配自动重新下载 |

#### FR-MOB-003 环境准备

| 字段 | 内容 |
|------|------|
| 描述 | 下载完成后唤醒 RPA 脚本执行环境 |
| 输入 | 下载完成事件 |
| 输出 | 状态上报"就绪"、RPA 脚本启动 |
| 规则 | 唤醒前检查屏幕状态、APP 安装状态 |
| 验收 | 状态变更可被服务端感知；脚本执行环境正确初始化 |

#### FR-MOB-004 沙箱机制

| 字段 | 内容 |
|------|------|
| 描述 | 影像文件仅存储在指定目录，支持目标 APP 访问 |
| 输入 | 文件存储请求 |
| 输出 | 受控目录中的文件 |
| 规则 | 目录权限按 Android 文件系统规范配置；其他应用通过 FileProvider 访问 |
| 验收 | 目标保险 APP 可正常读取；其他应用无权访问 |

#### FR-MOB-005 清理策略

| 字段 | 内容 |
|------|------|
| 描述 | 事务结束（成功或终态失败）后自动清理文件 |
| 输入 | 事务终态事件 |
| 输出 | 文件已删除确认 |
| 规则 | SUCCESS 后立即清理；FAIL 保留 24h 供排查后清理；DLQ 保留 7 天 |
| 验收 | 清理后磁盘空间释放；日志记录清理操作 |

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
| Step | Flow 中的步骤定义 |
| StepExecution | Step 执行记录 |
| Attachment | 影像附件 |
| AuditLog | 审计日志 |
| StateTransition | 状态变更记录 |

### 5.2 实体字段定义

#### Transaction（事务）

| 字段 | 类型 | 说明 |
|------|------|------|
| transaction_id | String(32) PK | 全局唯一 ID |
| external_id | String(64) | 外部业务 ID（幂等用） |
| business_type | Enum | NEW（新保）/ RENEWAL（续保）|
| status | Enum | PENDING/DISPATCHED/DOWNLOADING/RUNNING/SUCCESS/FAIL/DLQ |
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
| callback_url | String(512) | 确认回调通知 URL（可选） |

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

#### Worker（桌面节点）

| 字段 | 类型 | 说明 |
|------|------|------|
| worker_id | String PK | Worker 唯一 ID |
| fingerprint | String(64) UK | 本机指纹哈希 |
| hostname | String | 主机名 |
| ip_address | String | IP 地址 |
| version | String | 客户端版本 |
| tags | JSON | 能力标签 |
| cpu_usage | Float | CPU 使用率 |
| memory_usage | Float | 内存使用率 |
| status | Enum | ONLINE/OFFLINE/BUSY |
| last_heartbeat_at | DateTime | 最后心跳时间 |
| registered_at | DateTime | 注册时间 |

#### Device（Android 设备）

| 字段 | 类型 | 说明 |
|------|------|------|
| device_id | String PK | Device 唯一 ID |
| sn | String(64) UK | 设备 SN/UDID |
| worker_id | String FK | 挂载的 Worker |
| model | String | 设备型号 |
| android_version | String | Android 版本 |
| battery_level | Int | 电量（0-100） |
| storage_free_mb | Int | 剩余存储（MB） |
| screen_locked | Boolean | 是否锁屏 |
| status | Enum | ONLINE/OFFLINE/BUSY/DISABLED |
| current_transaction_id | String | 当前占用事务 |

#### Flow（流程定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| flow_id | String PK | Flow ID |
| flow_name | String(64) | Flow 名称 |
| business_type | Enum | NEW/RENEWAL |
| version | String | 版本号 |
| schema | JSON | 输入校验 Schema |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

#### Step（步骤定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| step_id | String PK | Step ID |
| flow_id | String FK | 所属 Flow |
| order | Int | 执行顺序 |
| step_name | String(64) | 步骤名称 |
| action_type | Enum | OPEN_APP/INPUT/UPLOAD/CLICK/SCREENSHOT/CONFIRM/WAIT |
| params | JSON | 步骤参数 |
| retry_policy | JSON | 重试策略 |
| timeout_ms | Int | 超时时间 |
| confirm_timeout_ms | Int | 确认超时时间（仅 CONFIRM 类型有效，默认 1800000 即 30min） |
| confirm_prompt | String(256) | 确认提示文案（仅 CONFIRM 类型有效，如"请确认保单信息是否正确"） |

#### StepExecution（步骤执行记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| execution_id | String PK | 执行记录 ID |
| transaction_id | String FK | 关联事务 |
| step_id | String FK | 关联 Step |
| attempt | Int | 第几次尝试 |
| status | Enum | RUNNING/SUCCESS/FAIL/TIMEOUT |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 结束时间 |
| duration_ms | Long | 耗时 |
| screenshot_url | String | 截图存储路径 |
| error_message | Text | 错误信息 |
| confirm_status | Enum | PENDING/CONFIRMED/REJECTED/TIMEOUT（仅 CONFIRM 类型 Step） |
| confirm_screenshot_url | String | 确认截图 URL（仅 CONFIRM 类型 Step） |
| confirmed_by | String | 确认人 User ID |
| confirmed_at | DateTime | 确认时间 |

#### Attachment（附件）

| 字段 | 类型 | 说明 |
|------|------|------|
| attachment_id | String PK | 附件 ID |
| transaction_id | String FK | 关联事务 |
| file_type | Enum | ID_CARD/DRIVING_LICENSE/CERTIFICATE/INVOICE/OTHER |
| description | String(128) | 用户对文件的描述/标签（如"身份证正反面合一"） |
| file_format | Enum | JPG/PNG/PDF |
| file_size | Long | 文件大小（字节） |
| storage_url | String | 服务端存储路径 |
| md5 | String(32) | 文件 MD5 |
| uploaded_at | DateTime | 上传时间 |

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

### 5.3 实体关系图

```
User ──N:1── Role
Transaction ──N:1── User (submitted_by)
Transaction ──N:1── Flow
Transaction ──N:1── Worker (可空)
Transaction ──N:1── Device (可空)
Transaction ──1:N── Attachment
Transaction ──1:N── StepExecution
Transaction ──1:N── StateTransition
Transaction ──1:N── AuditLog
Flow ──1:N── Step
StepExecution ──N:1── Step
Worker ──1:N── Device
```

---

## 6. 接口概要设计

### 6.1 接口分类

| 分类 | 用途 | 协议 |
|------|------|------|
| 业务接口 | 销售提交、查询事务 | HTTPS REST |
| 调度接口 | Worker 注册、心跳、任务领取 | HTTPS REST + WebSocket |
| 设备接口 | Device 文件下载、状态上报 | HTTPS REST |
| 管理接口 | 用户/角色/Flow 管理 | HTTPS REST |
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
| GET | /api/v1/transactions/{id}/confirms | 查询待确认截图列表 | User Token |
| POST | /api/v1/transactions/{id}/confirms/{step_exec_id} | 用户确认/拒绝截图 | User Token |

**示例：POST /api/v1/transactions 请求体**

```json
{
  "external_id": "BIZ-20260602-001",
  "business_type": "RENEWAL",
  "customer_phone": "138****1234",
  "customer_id_no": "310***********1234",
  "callback_url": "https://third-party.example.com/confirm-callback",
  "attachments": [
    {
      "file_type": "ID_CARD",
      "description": "身份证正反面合一",
      "file_url": "https://oss.example.com/xxx/idcard.jpg",
      "file_format": "JPG",
      "md5": "a1b2c3d4e5f6..."
    },
    {
      "file_type": "DRIVING_LICENSE",
      "description": "行驶证",
      "file_url": "https://oss.example.com/xxx/license.jpg",
      "file_format": "JPG",
      "md5": "d4e5f6a1b2c3..."
    }
  ]
}
```

**响应体**

```json
{
  "code": 0,
  "data": {
    "transaction_id": "TXN-20260602-00001",
    "status": "PENDING",
    "submitted_at": "2026-06-02T10:00:00Z"
  }
}
```

#### 6.2.2 调度接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| POST | /api/v1/workers/register | Worker 注册 | 无（返回 Token） |
| POST | /api/v1/workers/heartbeat | Worker 心跳 | Worker Token |
| GET | /api/v1/workers | 查询 Worker 列表 | Admin Token |
| GET | /api/v1/workers/{id} | 查询 Worker 详情 | Admin Token |
| DELETE | /api/v1/workers/{id} | 下线 Worker | Admin Token |
| GET | /api/v1/tasks/poll | 长轮询领取任务 | Worker Token |
| POST | /api/v1/tasks/{id}/ack | 确认任务接收 | Worker Token |
| POST | /api/v1/tasks/{id}/result | 上报任务结果 | Worker Token |
| GET | /api/v1/devices | 查询设备池 | Admin Token |
| PUT | /api/v1/devices/{id}/status | 更新设备状态（禁用等） | Admin Token |

#### 6.2.3 设备接口

| Method | Path | 描述 | 鉴权 |
|--------|------|------|------|
| GET | /api/v1/devices/{id}/files | 获取事务附件下载链接 | Device Token |
| POST | /api/v1/devices/{id}/status | 上报设备状态 | Device Token |
| POST | /api/v1/devices/{id}/ready | 上报就绪状态 | Device Token |
| POST | /api/v1/devices/{id}/step-result | 上报 Step 执行结果 | Device Token |

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
| GET | /api/v1/flows/{id}/steps | Flow 步骤详情 | Admin Token |
| PUT | /api/v1/flows/{id}/schema | 更新校验 Schema | Admin Token |

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

#### Socket 通道（Android ↔ Worker）

| 方向 | 用途 |
|------|------|
| Worker → Device | 下发下载指令、RPA 启动指令 |
| Device → Worker | 上报下载进度、Step 执行结果 |

**消息格式：**

```json
{
  "cmd": "DOWNLOAD_FILES",
  "params": {
    "transaction_id": "TXN-20260602-00001",
    "files": [
      {"file_type": "ID_CARD", "url": "https://...", "md5": "a1b2c3..."}
    ]
  }
}
```

### 6.4 通用约定

| 项目 | 规范 |
|------|------|
| 鉴权 | Bearer Token（JWT），payload 含 role/worker_id/device_id |
| 错误格式 | `{"code": <int>, "message": "<string>", "details": <object>}` |
| 分页 | `?page=1&page_size=20`，响应含 `total`/`items` |
| 限流 | 按角色限流：销售 60次/min，API Token 600次/min |
| 版本 | URL 路径版本 `/api/v1/` |

---

## 7. 部署架构

### 7.1 逻辑架构图

```
┌─────────────────────────────────────────────────────┐
│                    用户层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Web 门户  │  │REST API  │  │  Dashboard       │  │
│  └─────┬────┘  └─────┬────┘  └────────┬─────────┘  │
└────────┼─────────────┼────────────────┼─────────────┘
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
│  │            对象存储 (OSS / COS / MinIO)             │  │
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
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  本地站点 A   │ │  本地站点 B   │ │  本地站点 N   │
│  (办公室/门店) │ │  (办公室/门店) │ │  (办公室/门店) │
│              │ │              │ │              │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │ Worker#1 │ │ │ │ Worker#3 │ │ │ │ Worker#N │ │
│ │ (Desktop)│ │ │ │ (Desktop)│ │ │ │ (Desktop)│ │
│ │ ┌──────┐ │ │ │ │ ┌──────┐ │ │ │ │ ┌──────┐ │ │
│ │ │Dev-A │ │ │ │ │ │Dev-C │ │ │ │ │ │Dev-E │ │ │
│ │ │Dev-B │ │ │ │ │ │Dev-D │ │ │ │ │ │Dev-F │ │ │
│ │ └──────┘ │ │ │ │ └──────┘ │ │ │ │ └──────┘ │ │
│ │  Socket  │ │ │ │  Socket  │ │ │ │  Socket  │ │
│ │ ┌──────┐ │ │ │ │ ┌──────┐ │ │ │ │ ┌──────┐ │ │
│ │ │Agent │ │ │ │ │ │Agent │ │ │ │ │ │Agent │ │ │
│ │ │A  B  │ │ │ │ │ │C  D  │ │ │ │ │ │E  F  │ │ │
│ │ └──────┘ │ │ │ │ └──────┘ │ │ │ │ └──────┘ │ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
└──────────────┘ └──────────────┘ └──────────────┘
```

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

#### 本地部署

| 节点类型 | 部署方式 | 说明 |
|----------|----------|------|
| Worker 节点 | 本地桌面电脑（Linux/Windows） | 通过公网/VPN 连接云端 |
| Android 设备 | USB 挂载于 Worker | 物理设备，各站点独立管理 |

### 7.3 网络架构

```
云端                                     本地站点
┌─────────────┐     公网/VPN      ┌─────────────────┐
│  SLB/CLB    │◄────────────────►│  Worker (NAT)    │
│  (443/WSS)  │   HTTPS / WSS    │  (出站访问云端)    │
└──────┬──────┘                  └────────┬────────┘
       │                                  │ Socket (LAN)
┌──────┴──────┐                  ┌────────┴────────┐
│  Backend    │                  │  Android Agent   │
│  集群       │                  │  (局域网通信)     │
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
| Device → OSS | HTTPS | 443 | 出站 | Device 直接从 OSS 下载文件 |
| Device → Worker | TCP Socket | 8765 | 局域网 | 本地指令通道 |
| Backend → RDS | TCP | 5432 | 内网 | 云内网通信 |
| Backend → Redis | TCP | 6379 | 内网 | 云内网通信 |
| Backend → MQ | TCP | 5672 | 内网 | 云内网通信 |
| Backend → OSS | HTTPS | 443 | 内网 | 云内网通信 |

**关键设计决策：** Worker 采用出站连接模式，主动向云端发起 HTTPS/WSS 连接，本地无需开放公网入站端口，降低安全风险。设备文件下载走 OSS 直链（签名 URL），不经 Backend 中转，减轻服务端带宽压力。

### 7.5 硬件建议

#### 云端资源（最小配置）

| 节点 | 规格 | 数量 | 说明 |
|------|------|------|------|
| Backend (ECS) | 4C 8GB | 2 | K8s Worker 节点 |
| RDS | 4C 16GB 200GB SSD | 1 | 主实例 |
| OSS | 按量付费 | - | 影像存储 |
| SLB | 标准版 | 1 | HTTPS 卸载 |

#### 本地站点资源（单站点最小配置）

| 节点 | 规格 | 数量 | 说明 |
|------|------|------|------|
| Worker 电脑 | 4C 8GB 100GB SSD | 1 | 可按设备数扩展 |
| Android 设备 | - | 2 | 中高端机型，≥Android 10 |
| USB 数据线 | - | 2 | 支持数据传输+充电 |
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

#### 前期（MVP / 试运行阶段）

适用场景：≤ 5 个本地站点、≤ 20 台 Android 设备、日处理 ≤ 500 笔事务

| 组件 | 是否必需 | 说明 |
|------|----------|------|
| Backend 服务 | 必需 | 单实例或双实例 |
| PostgreSQL | 必需 | 主存储 + 任务队列（基于行级锁 SELECT FOR UPDATE SKIP LOCKED） |
| 对象存储 OSS | 必需 | 影像文件存储 |
| 负载均衡 SLB | 必需 | HTTPS 卸载 |
| Redis | 可省略 | JWT 无状态 Token + 数据库替代缓存和限流 |
| MQ | 可省略 | 数据库轮询调度（每 1-2s 扫描 PENDING 事务） |

**架构简化收益：**
- 减少云服务实例成本（约节省 30-40% 云资源费用）
- 减少运维复杂度（少 2 个组件的监控、备份、告警）
- 减少故障点

#### 中期（业务扩展阶段）

适用场景：≥ 10 个本地站点、≥ 50 台设备、日处理 ≥ 2000 笔事务

| 触发条件 | 引入组件 |
|----------|----------|
| 数据库轮询压力增大（CPU > 60%） | 引入 Redis 缓存 Worker 状态、Dashboard 指标 |
| 任务调度延迟 > 5s | 引入 MQ 作为任务队列，调度中心改为消费者模式 |
| 多 Backend 实例间需要共享会话/限流状态 | 引入 Redis |
| 需要异步事件总线（短信通知、外部系统对接） | 引入 MQ |

#### 后期（规模化阶段）

适用场景：≥ 50 个站点、≥ 200 台设备、日处理 ≥ 1 万笔事务

| 组件 | 部署方式 |
|------|----------|
| Redis | Sentinel / Cluster 模式 |
| MQ | RabbitMQ 集群 / RocketMQ |
| Backend | K8s 多副本 + HPA 自动扩缩容 |
| RDS | 读写分离 + 分库分表 |

---

## 8. 非功能性需求

### 8.1 性能

| 指标 | 目标值 |
|------|--------|
| 单笔事务提交响应时间 | ≤ 500ms（P95） |
| 任务调度延迟（PENDING → DISPATCHED） | ≤ 2s |
| 文件下载速率（Device → OSS） | ≥ 5MB/s（局域网） |
| 单 Step 执行超时 | 默认 60s，可配置 |
| 单事务全流程 ATT | ≤ 5min（正常情况） |
| 系统并发事务处理能力 | ≥ 50 笔/分钟（单 Backend 实例） |
| API 限流阈值 | 销售 60次/min，API Token 600次/min |

### 8.2 可用性

| 指标 | 目标值 |
|------|--------|
| Backend 服务可用性 | ≥ 99.9%（年停机 ≤ 8.76h） |
| Worker 故障切换时间 | ≤ 60s（心跳超时检测 + 事务重新调度） |
| 数据库 RPO | ≤ 1s（主从同步复制） |
| 数据库 RTO | ≤ 5min |
| 文件下载断点续传恢复 | 网络恢复后自动续传，无需人工干预 |

### 8.3 安全性

| 需求项 | 描述 |
|--------|------|
| 传输加密 | 全链路 HTTPS/TLS 1.2+，WebSocket 使用 WSS |
| 存储加密 | 敏感字段（手机号、身份证号）AES-256 加密存储 |
| 数据脱敏 | API 响应中手机号显示为 `138****1234`，身份证号显示为 `310***********1234` |
| 鉴权 | 所有 API 携带 Bearer Token（JWT），Token 有效期 24h |
| 客户端沙箱 | Worker 侧下载文件 AES-256 加密存储，权限 700 |
| API 防刷 | 按角色限流 + IP 黑名单机制 |
| 日志脱敏 | 审计日志中敏感字段自动脱敏 |
| 文件清理 | 事务终态后自动清理影像文件（SUCCESS 立即清理，FAIL 保留 24h） |

### 8.4 可观测性

| 需求项 | 描述 |
|--------|------|
| 指标监控 | 事务积压量、设备在线率、脚本成功率、ATT |
| 日志采集 | 结构化 JSON 日志，统一采集至日志平台 |
| 告警规则 | 事务积压 > 阈值、设备在线率 < 阈值、成功率下降 > 阈值时自动告警 |
| 链路追踪 | Transaction ID 贯穿全链路，可还原完整调用链 |
| Dashboard | 实时展示关键指标，刷新间隔 ≤ 30s |

### 8.5 容错性

| 需求项 | 描述 |
|--------|------|
| Step 级重试 | 默认 3 次，指数退避（1s/2s/4s） |
| 事务级重试 | 连续失败 ≥3 次进入 DLQ |
| Worker 崩溃恢复 | 心跳超时检测 → 事务回退至 PENDING → 重新调度 |
| Device 离线处理 | 调度跳过离线设备，事务重新分配 |
| 死信队列 | DLQ 事务不自动重试，运维手动处理 |
| 客户端自恢复 | Worker 进程崩溃后自动重启，恢复未完成任务 |
| 用户确认超时 | CONFIRM Step 超时（默认 30min）自动视为通过，继续执行并记录日志 |

### 8.6 扩展性

| 需求项 | 描述 |
|--------|------|
| 横向扩展 | Worker 节点即插即用，新增 Worker 自动注册并参与调度 |
| Flow 可配置 | 新增保险产品流程只需定义 Flow + Steps，无需改代码 |
| Schema 热更新 | 校验规则变更无需重启服务 |
| 设备类型扩展 | 预留 iOS 设备接入能力（Device Controller 接口抽象） |
| 多保险产品 | 通过 Flow 定义支持不同保险公司的 APP 操作流程 |

---

## 9. 技术约束

| 约束项 | 规范 |
|--------|------|
| 核心语言 | Python ≥ 3.14，严格使用 UV 进行依赖管理与虚拟环境隔离 |
| 自动化框架 | Airtest 作为核心图像识别与设备控制框架；封装统一 Device Controller 接口，屏蔽 Android 设备差异 |
| 通信协议 | 全链路 HTTPS/TLS 加密，API 携带 Token 鉴权 |
| 配置管理 | 客户端与移动端配置（服务器地址、存储路径等）支持 YAML/JSON 文件配置，禁止硬编码 |
| 数据库 | PostgreSQL（主存储）；Redis（可选，按业务规模引入） |
| 消息队列 | RabbitMQ 或 Redis Stream（可选，按业务规模引入） |
| 对象存储 | MinIO（自建）或 S3 兼容云存储 |
| 容器化 | Backend 服务 Docker 化，支持 K8s 编排 |
| 日志格式 | 结构化 JSON，统一字段命名（snake_case） |
| API 规范 | RESTful，OpenAPI 3.0 文档自动生成 |
| 版本管理 | Git，分支策略：main（生产）、develop（开发）、feature/*（功能） |

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
| AC-006 | 调度分配 | 事务分配至负载最低的 Worker+Device |
| AC-007 | 设备亲和性 | 正常情况下事务全程不切换设备 |
| AC-008 | RPA 执行 | Flow 按 Step 顺序执行，截图证据可查 |
| AC-009 | Step 重试 | 单 Step 失败后自动重试，重试次数符合配置 |
| AC-010 | 状态流转 | 状态变更 100% 符合状态机定义 |
| AC-011 | 文件同步 | Device 完整下载所有影像文件，MD5 校验通过 |
| AC-012 | 断点续传 | 网络中断后恢复下载，文件完整 |
| AC-013 | DLQ 处理 | 连续失败 3 次事务进入 DLQ，运维可重新提交 |
| AC-014 | 文件清理 | SUCCESS 事务影像文件立即清理 |
| AC-015 | Dashboard | 关键指标可视化，数据刷新 ≤30s |
| AC-016 | 审计追溯 | 任一事务可还原完整生命周期 |
| AC-017 | 用户确认通知 | CONFIRM Step 截图在 3s 内送达 Web 通知和回调 URL |
| AC-018 | 用户确认通过 | 用户确认后事务立即恢复 RUNNING，继续执行后续 Step |
| AC-019 | 用户确认拒绝 | 用户拒绝后事务 FAIL，记录拒绝原因 |
| AC-020 | 确认超时自动继续 | 超时后自动视为通过，继续执行并记录日志 |

### 10.2 非功能验收

| 编号 | 验收项 | 通过标准 |
|------|--------|----------|
| NAC-001 | 并发性能 | 50 笔/分钟持续 30 分钟，无异常 |
| NAC-002 | API 响应 | P95 ≤ 500ms |
| NAC-003 | ATT | 正常事务 ≤5min |
| NAC-004 | 安全审计 | 敏感字段在日志和 API 响应中均脱敏 |
| NAC-005 | 容错恢复 | Worker 宕机后事务 60s 内重新调度 |
| NAC-006 | 扩展验证 | 新增 Worker 自动注册并参与调度 |

---

## 11. 风险与依赖

### 11.1 已知风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 保险 APP UI 变更导致 RPA 脚本失效 | 事务执行 FAIL | 高 | Step 级重试+截图对比检测；Flow 版本化管理，快速更新 |
| Android 系统升级导致 Airtest 兼容问题 | Device 不可用 | 中 | Device Controller 抽象层；预留多版本 ADB 兼容 |
| 大量并发事务导致调度瓶颈 | 事务积压 | 中 | 调度中心无状态化横向扩展；引入 MQ 削峰 |
| OCR 识别准确率不足 | 新保/续保误判 | 中 | 路由逻辑以用户选择为主，OCR 为辅 |
| 影像文件体积过大导致下载超时 | Device 下载 FAIL | 低 | 文件压缩；分片下载；超时熔断 |

### 11.2 外部依赖

| 依赖项 | 说明 | 风险 |
|--------|------|------|
| 保险 APP | RPA 操作的目标应用，需保持版本稳定 | APP 更新可能导致脚本失效 |
| Android USB 连接 | Worker 与 Device 的物理连接 | USB 线材/接口老化 |
| OCR 服务 | 识别影像资料内容（假设外部提供） | 服务不可用影响路由判断 |
| 网络 | Worker/Device 与 Backend 通信 | 网络抖动影响任务下发和文件下载 |

### 11.3 假设前提

| 编号 | 假设 |
|------|------|
| AS-001 | 保险 APP 在 Android 设备上可正常安装和运行 |
| AS-002 | Worker 桌面端为 Linux/Windows 系统，可稳定运行 Python 环境 |
| AS-003 | OCR 识别服务由外部系统提供，本系统仅消费结果 |
| AS-004 | 所有 Android 设备已开启 USB 调试和开发者模式 |
| AS-005 | Worker 与 Device 通过 USB 稳定连接，局域网网络通畅 |
| AS-006 | 对象存储服务可用（MinIO 或 S3 兼容） |
