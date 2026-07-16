## 1. 在 worker/config.py 中新增 SCRIPT_MAP 配置

- [ ] 1.1 修改 `worker/config.py`
  - 在文件顶部添加 `import json`（当前仅 `import os`）
  - 在 `Config` 类中新增 `SCRIPT_MAP` 属性
  - 从 `os.getenv("SCRIPT_MAP", "{}")` 读取
  - 使用 `json.loads()` 解析为 dict
  - 解析失败时记录警告日志并使用空 dict

## 2. 在 AirtestExecutor 中新增 run_script 方法

- [ ] 2.1 修改 `worker/airtest_executor.py`
  - 添加 `import argparse` 和 `import os`（用于路径处理）
  - 在 `AirtestExecutor` 类中新增 `run_script(script_path: str) -> bool` 方法
  - 构造 `argparse.Namespace(script=..., device=f"android:///{self.adb_serial}", log=True, recording=None, compress=None, no_image=False)`
  - 调用 `from airtest.cli.runner import run_script`
  - 捕获 `SystemExit`（断言失败 `exit 20`，其他失败 `exit -1`）和其他异常，返回 `False`

## 3. 在 dispatch_to_device 中调用脚本执行

- [ ] 3.1 修改 `worker/main.py` 的 `dispatch_to_device()`
  - 插入点在 line 180（`report_attachments_delivered()` 之后、`logger.info("Dispatch complete...")` 之前）
  - 从 `txn["business_type"]` 读取业务类型
  - 查 `config.SCRIPT_MAP` 获取脚本文件名
  - 防御性检查：`if self.airtest_executor is not None`
  - 若未配置、脚本不存在或 `airtest_executor` 为 None，仅记录日志，跳过执行
  - 若配置存在，调用 `self.airtest_executor.run_script(script_path)`

## 4. 验证

- [ ] 4.1 启动 Worker，验证空配置（`SCRIPT_MAP` 未设置）时不执行脚本、不报错
- [ ] 4.2 设置 `SCRIPT_MAP={"NEW_VEHICLE": "test.air"}`，创建空 `worker/scripts/test.air`，验证记录"script loaded but no actions"日志
- [ ] 4.3 验证 `AirtestExecutor.run_script()` 对不存在的脚本路径返回 `False` 且不抛出异常
- [ ] 4.4 验证 JSON 配置错误（如 `SCRIPT_MAP=invalid_json`）时使用空 dict 并继续运行