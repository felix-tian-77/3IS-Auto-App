# Proposal: Worker 根据投保类型执行指定 Airtest 脚本

## Summary

在 Worker 完成图片推送到设备后，根据 transaction 的 `business_type` 字段，通过 Airtest 执行 `worker/scripts/` 目录下的对应 `.air` 脚本。脚本与业务类型的映射通过环境变量 `SCRIPT_MAP` 进行配置，无需修改代码即可调整执行逻辑。

## Motivation

当前 Worker 完成"推送图片 → 回报 backend"后即结束工作流，未触发任何 Airtest 自动化流程。新车投保和旧车投保的后续操作步骤完全不同（新车需要录入车辆信息，旧车需要续保校验），需要在 Worker 端自动执行对应流程：

1. **缺少自动化触发点**：Worker 没有调用 Airtest 脚本，依赖人工或外部调度介入
2. **无法按业务类型路由**：新车/旧车的后续流程差异大，无法用统一脚本处理
3. **配置不灵活**：如未来增加新车险种或调整脚本，需要改 Worker 代码并重新发布

## User Impact

- **运营/开发**：可通过修改环境变量 `SCRIPT_MAP` 将新业务类型路由到对应脚本，无需改 Worker 代码
- **RPA 流程**：每个业务类型对应一个 `.air` 脚本，便于维护和版本管理
- **Worker 流程**：图片推送完成后自动执行下一步操作，无需人工干预

## Scope

### In Scope

- Worker 配置增加 `SCRIPT_MAP` 环境变量（JSON 格式），映射 `business_type` → 脚本文件名
- `AirtestExecutor` 类新增 `run_script(script_path)` 方法，使用 Airtest `run_script` API 执行 `.air` 文件
- `Worker.dispatch_to_device()` 在 `report_attachments_delivered()` 之后，调用脚本执行器执行对应脚本
- `worker/scripts/` 目录存在但可为空（未配置时不执行任何脚本，保持向后兼容）
- 未匹配到脚本时不报错，仅记录日志

### Out of Scope

- 不实现脚本内容本身（仅提供执行框架）
- 不修改 backend API（脚本映射完全在 Worker 端配置）
- 不修改 `transaction_meta.json`（脚本元数据已在 JSON 中，可自行读取）
- 不实现脚本超时控制（依赖 Airtest 自身超时设置）
- 不实现脚本并发控制（一个 transaction 一个脚本，串行执行）

## Success Criteria

1. `worker/config.py` 增加 `SCRIPT_MAP` 配置项，默认值 `{}`（空映射）
2. `AirtestExecutor.run_script(script_path)` 方法可成功执行 `.air` 脚本
3. `Worker.dispatch_to_device()` 在推送完成后，根据 `transaction["business_type"]` 查表执行脚本
4. 未配置或未匹配时不报错，仅记录日志
5. `worker/scripts/` 目录存在并预留（即使为空也不影响 Worker 运行）

## Non-Goals

- 不实现脚本调度系统（如定时执行、队列）
- 不实现脚本版本管理
- 不实现脚本执行结果回报 backend（仅记录本地日志）
- 不修改 `dispatch_to_device()` 中已有的下载、推送、回报逻辑