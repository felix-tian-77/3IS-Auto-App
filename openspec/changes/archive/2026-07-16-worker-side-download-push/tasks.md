## 1. Worker 端新增 FileDownloader 模块

- [ ] 1.1 创建 `worker/file_downloader.py`，实现 `FileDownloader` 类
  - `download(url, attachment_id, transaction_id) -> local_path`：用 `requests.get` 流式下载到 `{config.WORKER_TMP_DIR}/{transaction_id}/{attachment_id}.{ext}.part`
  - `verify_md5(file_path, expected_md5) -> bool`：用 `hashlib.md5` 8KB 缓冲流式校验
  - 下载完成后 `.part` 原子重命名为 `{attachment_id}.{ext}` 正式文件
  - HTTP 403/410 检测 -> 抛出 `URLExpiredError` 异常
- [ ] 1.2 实现 `download_all(signed_urls, transaction_id) -> List[DownloadedFile]` 批量下载方法
  - 串行下载（附件通常 2-5 个）
  - 每个文件下载后立即校验 MD5，失败则删除 `.part` 并标记错误
  - 返回 `[{attachment_id, local_path, md5_ok}]` 列表
- [ ] 1.3 实现 URL 过期续签逻辑
  - 捕获 `URLExpiredError` -> 重新调用 `fetch_download_urls(txn_id)`（复用现有 `POST /transactions/{id}/download-urls`）
  - 用新 URL 重试下载（最多 2 次续签）

## 2. Worker 端新增 DevicePusher 模块

- [ ] 2.1 创建 `worker/device_pusher.py`，实现 `DevicePusher` 类
  - 构造接收 `DeviceController` 实例
  - `push_files(transaction_id, downloaded_files) -> List[PushedFile]`
    - `adb shell mkdir -p /sdcard/3is/{transaction_id}/`
    - 对每个文件 `device.push(local_path, /sdcard/3is/{txn_id}/{att_id}.{ext})`
    - 返回 `[{attachment_id, local_path}]` 列表
- [ ] 2.2 实现 `cleanup(transaction_id)` 方法
  - `adb shell rm -rf /sdcard/3is/{transaction_id}/`
- [ ] 2.3 实现本地临时文件清理
  - `rm -rf {config.WORKER_TMP_DIR}/{transaction_id}/`

## 3. Worker 端新增 DeviceStatusReporter 模块

- [ ] 3.1 创建 `worker/device_status_reporter.py`，实现 `DeviceStatusReporter` 类
  - 构造接收 `DeviceController` 和 Backend URL/token
- [ ] 3.2 实现 `report_ready(device_id)` 方法
  - 调用 `POST /api/v1/devices/{device_id}/ready`，body `{"status": "READY"}`
- [ ] 3.3 实现 `report_status(device_id)` 方法
  - 通过 `DeviceController.get_status()` 采集：电量、存储、锁屏、型号、Android 版本
  - 调用 `POST /api/v1/devices/{device_id}/status` 上报
- [ ] 3.4 在 `DeviceController` 中扩展 `get_status()` 方法
  - `adb shell dumpsys battery | grep level` -> 电量
  - `adb shell df /sdcard` -> 存储剩余
  - `adb shell dumpsys power | grep mWakefulness` -> 锁屏状态

## 4. Worker main.py 重写

- [ ] 4.1 重写 `dispatch_to_device(task)` 方法
  - 调用 `fetch_download_urls(txn_id)` 获取签名 URL
  - 调用 `FileDownloader.download_all()` 下载到本地
  - 调用 `DevicePusher.push_files()` 推送到设备
  - 调用 `POST /transactions/{id}/attachments-delivered` 回写 local_path
  - 返回成功/失败
- [ ] 4.2 修改 `run()` 主循环
  - 心跳周期内增加 `DeviceStatusReporter.report_status()` 调用
  - 移除 `DeviceDispatcher` 导入和 Socket 监听逻辑
  - 启动时调用 `report_ready()`
- [ ] 4.3 移除 `worker/device_dispatcher.py`
- [ ] 4.4 更新 `worker/config.py`
  - 移除 `WORKER_LISTEN_HOST`、`PORT`、`DISPATCH_TIMEOUT`
  - 新增 `DEVICE_SANDBOX_ROOT`（默认 `/sdcard/3is/`）
  - 新增 `WORKER_TMP_DIR`（默认 `~/.3is-auto/tmp/`）

## 5. Backend 移除 download-ack 接口

- [ ] 5.1 移除 `backend/api/v1/devices.py` 中 `POST /devices/{device_id}/download-ack` 路由
- [ ] 5.2 移除 `backend/schemas/device.py` 中 `DeviceDownloadAckRequest`、`DeviceDownloadAckResponse`、`DownloadAckFile` schema
- [ ] 5.3 新增 `POST /api/v1/transactions/{id}/attachments-delivered` 接口
  - Body: `{device_id, files: [{attachment_id, local_path}]}`
  - 逻辑：回写 `attachment.local_path`；将事务状态推进至 `READY`（下载阶段完成）
  - **不设置 `finished_at`**（`finished_at` 留给事务终态 `SUCCESS`/`FAIL` 时由 task result 上报链路设置）
  - 返回 `{transaction_id, next_state: "READY"}`
- [ ] 5.4 为新接口编写后端测试（`tests/backend/test_attachments_delivered.py`）
- [ ] ~5.5~ 已决定复用现有 `POST /transactions/{id}/download-urls`（重新生成全套签名 URL），不再新增 `/oss-urls/refresh`
- [ ] ~5.6~ 同上，取消

## 6. 移除 Device Agent APK

- [ ] 6.1 删除 `android/app/src/main/java/com/threeis/deviceagent/` 目录及所有 Kotlin 源码
- [ ] 6.2 删除 `android/app/src/main/AndroidManifest.xml`
- [ ] 6.3 删除 `android/app/src/main/res/` 资源目录
- [ ] 6.4 删除 `android/app/build.gradle.kts`、`android/app/src/test/`
- [ ] 6.5 保留或移除 `android/scripts/` 目录
  - `adb_install.sh` 和 `adb_install.ps1` 不再需要（无 APK 安装）
  - `mock_worker.py` 不再需要（无 Socket 通信）
- [ ] 6.6 更新 `android/README.md`，说明 Device Agent APK 已移除，Worker 直接通过 ADB 操作设备
- [ ] 6.7 清理 `android/settings.gradle.kts`、`android/build.gradle.kts`、`android/gradle/` 等 Gradle 工程（如整个 android/ 不再需要）

## 7. 设备沙箱路径迁移

- [ ] 7.1 确认目标保险 APP 的文件选择器能访问子目录 `/sdcard/3is/{txn_id}/`
- [ ] 7.2 更新 Airtest 脚本中引用文件路径的地方（如有硬编码 `/sdcard/3is/` 平铺路径）

## 8. 集成测试与验证

- [ ] 8.1 Worker 端单元测试：`worker/tests/test_file_downloader.py`
  - 测试正常下载 + MD5 校验通过
  - 测试 MD5 不匹配时删除文件
  - 测试 URL 过期续签
- [ ] 8.2 Worker 端单元测试：`worker/tests/test_device_pusher.py`
  - 测试 push 路径生成（含 transaction_id 子目录）
  - 测试 cleanup 清理
- [ ] 8.3 端到端测试：Worker 启动 -> 心跳 -> 任务轮询 -> 下载 -> push -> Airtest 执行 -> 清理
- [ ] 8.4 验证移除 APK 后 `adb devices` 能发现设备、`adb push` 正常工作
- [ ] 8.5 验证并发事务沙箱隔离（两个事务的文件不互相干扰）
- [ ] 8.6 运行 `worker/tests/` 现有测试确保无回归
