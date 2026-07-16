## Context

### 当前 Worker 流程

`worker/main.py:129-182` `dispatch_to_device()` 当前流程：

1. 从 `task["task"]` 提取 `transaction_id` 和 `attachments`
2. 调用 `fetch_download_urls()` 获取签名 URL
3. 调用 `_download_with_refresh()` 下载文件
4. 调用 `FileDownloader.save_transaction_meta()` 写 JSON 元数据
5. 调用 `device_pusher.push_files()` 推送到设备
6. 调用 `report_attachments_delivered()` 回报 backend（line 179）
7. `logger.info("Dispatch complete...")` 输出成功日志（line 181）— **未触发 Airtest 自动化**

**插入点**：line 180（在 `report_attachments_delivered()` 与 `logger.info("Dispatch complete...")` 之间）

### Airtest 脚本执行

Airtest 提供 `airtest.cli.runner.run_script()` API：

```python
from airtest.cli.runner import run_script, AirtestCase
```

`run_script()` 会加载 `.air` 文件并执行其中的 Airtest 语句（如 `touch`、`text`、`assert_exists` 等）。

### AirtestExecutor 当前实现

`worker/airtest_executor.py` 已有 `AirtestExecutor` 类，提供：

- `connect()` - 连接 Android 设备
- `execute_step(action_type, params)` - 执行单步动作（OPEN_APP/INPUT/CLICK/SCREENSHOT/WAIT）
- `disconnect()` - 断开连接

**注意**：当前 `execute_step()` 是动作级别（step-based），不支持直接运行 `.air` 脚本。

`AirtestExecutor` 在 `Worker.__init__` 中初始化为 `None`，仅在 `Worker.run()` 中实例化（`main.py:219-220`）：
```python
self.airtest_executor = AirtestExecutor(self.adb_serial)
self.airtest_executor.connect()
```

正常流程下，`dispatch_to_device()` 只会在 `run()` 主循环中被调用，`airtest_executor` 已可用。但需要在脚本执行前做防御性检查（`is not None`），避免测试或异常路径下出现 `AttributeError`。

### worker/scripts 目录

`worker/scripts/` 目录已存在。当前结构：

```
worker/scripts/
└── renew/
    └── renew_01.air/        # .air 是一个目录
        ├── renew_01.py      # 主脚本
        └── tpl*.png         # 模板图片（auto_setup 用）
```

Airtest 的 `.air` 脚本本质是一个目录，包含同名的 `.py` 主文件和模板图片。`run_script(args)` 的 `args.script` 应传入 `.air` 目录路径（如 `worker/scripts/renew/renew_01.air`），不是单个文件。

因此 `SCRIPT_MAP` 的 value 应是相对于 `worker/scripts/` 的目录路径（含 `.air` 后缀），例如：

```
SCRIPT_MAP={"OLD_VEHICLE": "renew/renew_01.air"}
```

### 配置机制

`worker/config.py` 当前基于 `os.getenv()` 读取环境变量。需要新增 `SCRIPT_MAP` 配置项。

## Goals / Non-Goals

**Goals:**
- `SCRIPT_MAP` 配置项支持 JSON 格式映射 `business_type → 脚本文件名`
- `AirtestExecutor.run_script(script_path)` 通过 Airtest `run_script` API 执行脚本
- `dispatch_to_device()` 在推送后查表执行脚本
- 未匹配到脚本时静默跳过（不报错）

**Non-Goals:**
- 不实现脚本内容（仅执行框架）
- 不修改 backend
- 不修改 `transaction_meta.json`
- 不实现超时/并发控制

## Decisions

### 1. SCRIPT_MAP 配置格式：JSON 字符串

**选择：** 环境变量 `SCRIPT_MAP` 接收 JSON 字符串：

```
SCRIPT_MAP={"NEW_VEHICLE": "new_vehicle.air", "OLD_VEHICLE": "old_vehicle.air"}
```

**理由：**
- JSON 格式易于解析（Python 内置 `json.loads`）
- 清晰表达键值映射
- 默认值 `{}`（空 dict）表示不执行任何脚本

**备选方案：** 逗号分隔（`NEW_VEHICLE:new_vehicle.air,OLD_VEHICLE:old_vehicle.air`）— 解析逻辑简单但嵌套或特殊字符支持差

### 2. 脚本路径：`worker/scripts/{SCRIPT_MAP_value}`

**选择：** `SCRIPT_MAP` 的 value 是相对于 `worker/scripts/` 的路径（含 `.air` 后缀），由 SCRIPT_MAP 完整配置

**理由：**
- Airtest `.air` 是目录（含 `.py` + 模板图片），用相对路径而非固定文件名更灵活
- 不同业务类型可放在不同子目录下组织（如 `renew/renew_01.air`）
- 路径解析逻辑简单：`worker/scripts/{value}`

**实现：**
```python
scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
script_path = os.path.join(scripts_dir, config.SCRIPT_MAP[business_type])
```

### 3. 脚本执行 API：airtest.cli.runner.run_script（via argparse.Namespace）

**选择：** 使用 Airtest 内置 `run_script()` API，传入 `argparse.Namespace`

**理由：**
- Airtest 官方 API，稳定可靠
- 进程内调用，无需 subprocess 开销
- 自动处理设备连接、脚本日志、断言等

**API 真实签名**（来自 `airtest/cli/runner.py`）：
```python
def run_script(parsed_args, testcase_cls=AirtestCase):
```

`parsed_args` 是一个 `argparse.Namespace`，需要包含以下字段：
- `script` (str) — `.air` 脚本路径
- `device` (str) — 设备 URI，例如 `android:///<serial>`
- `log` (bool/str) — 是否记录日志（日志目录或 True）
- `recording` (str/None) — 录屏文件名
- `compress` (int/None) — 截图压缩质量
- `no_image` (bool) — 是否不保存图片

`run_script()` 内部通过 `AirtestCase.setUpClass()` 调用 `setup_by_args(args)`，再调用 `auto_setup()` 创建新的设备连接。**它不会复用调用方的 `self.device`**——这是 Airtest 的固有行为。

**正确实现：**
```python
import argparse
from airtest.cli.runner import run_script

def run_script(self, script_path: str) -> bool:
    args = argparse.Namespace(
        script=script_path,
        device=f"android:///{self.adb_serial}",
        log=True,
        recording=None,
        compress=None,
        no_image=False,
    )
    try:
        run_script(args)
        return True
    except SystemExit as e:
        return e.code == 0
    except Exception as e:
        logger.error("Script execution failed: %s", e)
        return False
```

**注意：** `run_script()` 在断言失败时调用 `sys.exit(20)`，其他失败 `sys.exit(-1)`。需要捕获 `SystemExit` 并根据 exit code 判断成功/失败。

### 4. 未匹配脚本的行为：静默跳过

**选择：** 若 `business_type` 未在 `SCRIPT_MAP` 中，或脚本文件不存在，仅记录日志，不影响 Worker 主流程

**理由：**
- 脚本执行是可选扩展点，缺失不应阻塞核心 dispatch 流程
- Worker 的成功判断基于"推送+回报"，脚本执行是后续步骤

**日志示例：**
```
No script mapped for business_type=NEW_VEHICLE, skipping
Script not found: worker/scripts/new_vehicle.air
```

### 5. 错误处理：异常捕获但不阻断

**选择：** 脚本执行失败（如 Airtest 断言失败）时，捕获异常并记录日志

**理由：**
- Worker 主循环不应被单个脚本异常中断
- 失败信息保留在 Airtest 日志目录（`log/`）

## Risks / Trade-offs

- **[风险] 脚本执行阻塞主循环** → 脚本运行时间可能很长，导致 Worker 心跳暂停。可通过异步执行缓解，但当前设计为同步（明确为后续优化点）
- **[权衡] 未实现超时控制** → 长脚本可能无限挂起。当前依赖 Airtest 自身机制（脚本可在 `.air` 内调用 `sleep()` 或退出）
- **[风险] SCRIPT_MAP 配置错误** → JSON 解析失败时，记录日志并使用空映射，Worker 继续运行

## Architecture Changes

### 修改的组件

| 组件 | 位置 | 修改内容 |
|------|------|----------|
| worker.config | `worker/config.py` | 新增 `SCRIPT_MAP` 配置项 |
| AirtestExecutor | `worker/airtest_executor.py` | 新增 `run_script(script_path)` 方法 |
| Worker.dispatch_to_device | `worker/main.py` | 在 `report_attachments_delivered()` 后调用脚本执行 |

### 不修改的组件

| 组件 | 位置 | 原因 |
|------|------|------|
| backend | - | 脚本映射完全在 Worker 端配置 |
| transaction_meta.json | `worker/file_downloader.py` | 脚本可自行读取 JSON |
| FileDownloader / DevicePusher | - | 职责不变 |
| Airtest 脚本本身 | `worker/scripts/*.air` | 由后续 change 实现 |