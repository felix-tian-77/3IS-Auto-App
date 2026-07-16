# Proposal: Worker 端保存 Transaction JSON 元数据

## Summary

在 Worker 下载附件图片的同时，将 transaction 的基本信息（手机号码、投保类型、免税投保、转保）以 JSON 文件形式保存到与图片相同的目录中，供后续 Airtest 自动化流程读取使用。

## Motivation

当前 Worker 下载附件后，Airtest 自动化脚本需要知道 transaction 的业务属性才能执行不同的操作流程（例如：免税投保需要额外处理免税证明，转保需要输入原保险公司信息）。但目前 Worker 仅下载图片文件，不保存任何 transaction 元数据，导致：

1. **Airtest 脚本无法获知业务上下文**：不知道投保类型（新车/旧车）、是否免税、是否转保等关键信息
2. **手机号码无法传递到设备端**：Airtest 需要手机号码来填写表单，但目前 poll 响应中的 `customer_phone_encrypted` 是加密的，且缺少可读的 `holder_phone`
3. **缺少结构化元数据**：图片文件名仅包含 `attachment_id`，无法推断业务属性

## User Impact

- **Airtest 自动化流程**：可通过读取 JSON 文件获取手机号码、投保类型、免税/转保标志，自动选择对应流程
- **运维调试**：可在 Worker 本地文件系统中直接查看每个 transaction 的元数据，无需查询数据库

## Scope

### In Scope

- 修改 backend `GET /api/v1/tasks/poll` 响应，增加 `tax_exempt`、`is_transfer`、`holder_phone` 三个字段
- Worker 下载附件完成后，将 transaction 元数据写入 `{WORKER_TMP_DIR}/{transaction_id}/transaction_meta.json`
- JSON 文件包含：`transaction_id`、`holder_phone`、`business_type`、`tax_exempt`、`is_transfer`

### Out of Scope

- 不修改前端代码
- 不修改数据库 schema（字段已存在于 Transaction 模型）
- 不修改 Airtest 脚本读取逻辑（由后续 change 处理）
- 不修改 attachment 下载流程

## Success Criteria

1. `GET /api/v1/tasks/poll` 响应中包含 `tax_exempt`、`is_transfer`、`holder_phone`
2. Worker 完成附件下载后，`{WORKER_TMP_DIR}/{transaction_id}/` 目录下存在 `transaction_meta.json`
3. JSON 文件内容正确包含上述 5 个字段
4. `cleanup()` 时 JSON 文件随目录一起被清除

## Non-Goals

- 不解密 `customer_phone_encrypted`（使用 `holder_phone` 明文字段替代）
- 不修改 Worker 与 backend 的认证/授权机制
- 不为 JSON 文件添加校验或签名
- 不修改 Airtest 执行器读取 JSON 的逻辑
