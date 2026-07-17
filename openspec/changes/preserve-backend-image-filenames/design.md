## Context

Backend 当前将附件保存为 `file_type + ext` 的 basename，例如 `ID_CARD_FRONT.jpg`，但下载 URL 响应没有返回该文件名。Worker 目前使用 `attachment_id + ext` 生成临时文件和设备文件路径，导致本地文件、设备文件、交付回报和 Airtest 脚本之间出现命名漂移。

本变更跨越 Backend API、Worker 下载与设备推送流程以及 Airtest 脚本。Backend 文件名是唯一权威来源，已有 Backend 存储文件不做重命名或迁移。

## Goals / Non-Goals

**Goals:**

- 在下载 URL 元数据中提供稳定、明确的 `filename` 字段。
- 让 Worker 从下载响应接收并保留 Backend basename，贯穿临时保存、设备推送和交付回报。
- 统一事务目录和文件名规则，使 Airtest 脚本能够定位 Backend 返回的文件。
- 对文件名进行 basename 和路径安全校验，避免文件写入事务目录之外。
- 用测试覆盖 API 字段、下载保存、设备推送、交付回报和脚本文件名契约。

**Non-Goals:**

- 不改变 Backend 当前附件存储命名规则或迁移历史文件。
- 不恢复旧的 `transaction_id_NNN.ext` 命名方案。
- 不改变下载文件内容、校验和、URL 有效期或存储后端。
- 不扩展 Airtest 的业务流程；仅更新其文件定位所依赖的目录和文件名。

## Decisions

### 通过 API 显式传递 filename

下载 URL 列表中的每个附件项新增 `filename`，值取持久化存储路径的 basename，而不是让 Worker 从 URL、扩展名或 `file_type` 自行推导。

备选方案是让 Worker 从已有 `storage_path` 推导，或从 URL 路径解析文件名。前者使 Worker 依赖 poll 响应的内部字段，后者依赖 URL 编码和路由实现；显式字段能稳定表达跨服务契约，并允许 Backend 未来独立调整存储路径。

### Worker 以 filename 作为贯穿流程的标识

Worker 在任务分发时保留 `filename`，下载器使用 `{worker_tmp}/{transaction_id}/{filename}` 保存并在下载结果对象中携带该值；设备推送器使用 `/sdcard/3is/{transaction_id}/{filename}`。交付回报的 `local_path` 使用同一设备路径。

旧的 `attachment_id` 继续作为 API 关联和日志标识，但不再参与文件名生成。为了支持滚动发布，Worker 可在缺少 `filename` 的旧 Backend 响应时保留现有命名作为兼容回退；新契约测试必须验证带有 `filename` 时绝不使用 `attachment_id` 替代。

### 在写入前校验 basename

Worker 接收到的 `filename` 必须非空、仅代表单个 basename，不能包含目录分隔符、绝对路径、`.` 或 `..`。无效文件名的附件不得写入临时目录或设备路径，并按现有下载失败流程处理。

这比直接拼接字符串更能防止 API 数据异常导致路径穿越。Backend 同样应从存储路径中提取 basename，避免把内部目录暴露为可写入的相对路径。

### Airtest 脚本统一使用事务子目录和 Backend 文件名

所有涉及附件选择的脚本先进入 `{transaction_id}` 目录，再按 Backend 文件名选择文件，例如 `ID_CARD_FRONT.jpg`、`ID_CARD_BACK.jpg` 和 `DRIVING_LICENSE_FRONT.jpg`。脚本中的旧 `01.jpg`、`02.jpg`、`03.jpg` 引用全部替换。

## Risks / Trade-offs

- [滚动发布期间字段缺失] 新 Worker 可能收到旧 Backend 响应。→ 保留旧命名作为仅限兼容的回退，并通过日志和测试区分新旧路径。
- [API 文件名与实际对象不一致] Backend 返回错误 basename 会导致下载后校验或脚本定位失败。→ 从持久化存储路径统一生成 `filename`，并增加 API 响应测试。
- [特殊文件名导致路径问题] 不安全 basename 可能造成写入越界或设备命令异常。→ 在 Worker 写入前拒绝路径分隔符和特殊路径值。
- [设备端已有旧文件] 更新后同一事务目录下旧命名文件不会自动迁移。→ 仅对新下载任务使用新契约，失败重试时覆盖同名 Backend 文件；不做历史设备文件迁移。
- [现有测试和脚本夹具依赖旧路径] 改动可能暴露隐含的 attachment_id 命名假设。→ 同步更新相关单元测试、分发测试和用户文档，并执行完整测试集。

## Migration Plan

1. 先部署 Backend 的 `filename` 响应字段，新增字段对旧 Worker 兼容。
2. 部署 Worker 的 filename 透传、保存、推送、回报和安全校验逻辑。
3. 发布更新后的 Airtest 脚本及文档。
4. 验证新任务的 Backend basename 在 Worker 临时目录、设备目录和交付回报中保持一致。
5. 若需回滚，先回滚 Worker 和脚本；Backend 保留额外的 `filename` 字段不会影响旧 Worker。

## Open Questions

无。文件名以当前 Backend 存储 basename（`file_type + ext`）为准，并按端到端范围实施。
