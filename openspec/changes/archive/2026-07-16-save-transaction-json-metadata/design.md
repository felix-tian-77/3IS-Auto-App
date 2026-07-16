## Context

### 当前数据流

Worker 通过 `GET /api/v1/tasks/poll` 获取任务。当前 poll 响应（`backend/api/v1/tasks.py:55-65`）返回的字段：

```python
{
    "task": {
        "transaction_id": "...",
        "business_type": "NEW_VEHICLE|OLD_VEHICLE",
        "flow_id": "...",
        "device_id": "...",
        "customer_phone_encrypted": "...",   # 加密，Worker 无法直接使用
        "customer_id_no_encrypted": "...",
        "retry_count": 0,
        "attachments": [...]
    }
}
```

### Transaction 模型已有的字段

`backend/models/transaction.py` 中 Transaction 模型已包含但**未在 poll 响应中返回**的字段：

- `tax_exempt = Column(Boolean, default=False, nullable=False)` - 免税投保
- `is_transfer = Column(Boolean, default=False, nullable=False)` - 转保
- `holder_phone = Column(String(20), nullable=True)` - 持有人手机号（明文）

### Worker 文件保存机制

`worker/file_downloader.py:26-29` - `_txn_dir()` 创建并返回 `{tmp_dir}/{transaction_id}` 目录：

```python
def _txn_dir(self, transaction_id: str) -> Path:
    d = Path(self.tmp_dir) / transaction_id
    d.mkdir(parents=True, exist_ok=True)
    return d
```

附件文件保存为 `{attachment_id}.{ext}`（如 `A-20260715-a1b2c3d4.jpg`）。`cleanup()` 方法（`file_downloader.py:88-92`）删除整个 transaction 目录。

### Worker 调度流程

`worker/main.py:129-173` - `dispatch_to_device()` 方法：
1. 从 `task["task"]` 提取 `transaction_id` 和 `attachments`
2. 调用 `fetch_download_urls()` 获取签名 URL
3. 调用 `_download_with_refresh()` 下载文件
4. 调用 `device_pusher.push_files()` 推送到设备
5. 调用 `report_attachments_delivered()` 回报

## Goals / Non-Goals

**Goals:**
- Poll 响应增加 `tax_exempt`、`is_transfer`、`holder_phone` 三个字段
- Worker 在附件下载完成后、推送到设备前，将 transaction 元数据写入 `transaction_meta.json`
- JSON 文件与附件文件位于同一目录

**Non-Goals:**
- 不修改数据库 schema
- 不修改前端
- 不修改 Airtest 读取逻辑
- 不为 JSON 添加加密或签名

## Decisions

### 1. 使用 `holder_phone` 而非 `customer_phone_encrypted`

**选择：** 在 poll 响应中新增 `holder_phone` 字段

**理由：**
- `customer_phone_encrypted` 是加密的，Worker 无法解密使用
- `holder_phone` 是明文手机号，已在 Transaction 模型中存在
- Airtest 需要明文手机号填写设备端表单

**备选方案：** 在 Worker 端解密 - 但 Worker 没有解密密钥，不现实

### 2. JSON 写入时机：下载完成后、推送前

**选择：** 在 `dispatch_to_device()` 中，`_download_with_refresh()` 成功后、`push_files()` 前写入

**理由：**
- 此时附件已确认完整下载（MD5 校验通过）
- JSON 文件可与附件一起推送到设备（如果需要）
- 若下载失败则不会生成 JSON，避免产生不完整的元数据

**备选方案：** 在 poll 后立即写入 - 但此时附件尚未下载，JSON 存在但图片不存在会造成不一致

### 3. JSON 写入位置：FileDownloader 而非 Worker 主类

**选择：** 在 `FileDownloader` 类中新增 `save_transaction_meta()` 方法

**理由：**
- `FileDownloader` 已管理 `{transaction_id}` 目录（`_txn_dir`）
- JSON 文件与附件文件属于同一存储层
- `cleanup()` 统一处理目录删除，无需额外清理逻辑

**备选方案：** 在 Worker 类中直接写文件 - 但会破坏 FileDownloader 的封装，且 cleanup 需要额外处理

### 4. JSON 文件名：`transaction_meta.json`

**选择：** 固定文件名 `transaction_meta.json`

**理由：**
- 固定文件名便于 Airtest 脚本查找
- 与附件文件（`{attachment_id}.{ext}`）不冲突
- 语义清晰

### 5. JSON 内容结构

```json
{
    "transaction_id": "T-20260715-a1b2c3d4",
    "holder_phone": "13800138000",
    "business_type": "NEW_VEHICLE",
    "tax_exempt": false,
    "is_transfer": false
}
```

**理由：**
- 5 个字段满足业务需求：手机号填表、投保类型路由、免税/转保标志决定流程分支
- 字段名与后端模型一致，减少映射成本

## Risks / Trade-offs

- **[风险] `holder_phone` 可能为 null** -> 旧数据可能没有此字段。JSON 中 `holder_phone` 为 `null` 时 Airtest 脚本需处理空值情况，不影响 Worker 写入逻辑
- **[权衡] JSON 文件不推送到设备** -> 当前设计中 `transaction_meta.json` 仅保存在 Worker 本地。若 Airtest 需要，可通过 `push_files` 机制后续添加。当前 design 不涉及推送到设备

## Architecture Changes

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| tasks.poll_task | `backend/api/v1/tasks.py:55-65` | 响应 dict 增加 `tax_exempt`、`is_transfer`、`holder_phone` |
| FileDownloader.save_transaction_meta | `worker/file_downloader.py`（新增方法） | 将 transaction 元数据写入 JSON 文件 |
| Worker.dispatch_to_device | `worker/main.py:129-173` | 下载成功后调用 `save_transaction_meta()` |

### 不修改的组件

| 组件 | 位置 | 原因 |
|------|------|------|
| Transaction model | `backend/models/transaction.py` | 字段已存在 |
| 前端 | `frontend/...` | 不消费 poll 响应 |
| DB schema | - | 无需 migration |
| Airtest executor | `worker/airtest_executor.py` | 读取逻辑由后续 change 处理 |
