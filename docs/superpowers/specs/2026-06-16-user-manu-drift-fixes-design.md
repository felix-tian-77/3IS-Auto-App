# user-manu Drift Fixes (post-T17 sync) — Design

**Goal:** Bring `docs/user-manu.md` in line with 6 post-T17 code commits that landed after T17 (the original docs sync). Five concrete drift items; five atomic commits; no code changes.

**Scope:** Documentation only. No Kotlin, Python, or build changes.

**Tech Stack:** Markdown, Git, openspec not used (this is a superpowers flow, not openspec experimental).

---

## Background

The Android Device Agent implementation followed an 18-task plan. T17 (`docs: sync user-manu and 2026-06-03 worker spec for Android Device Agent`, commit `7e034ed`) updated `docs/user-manu.md` for the Android rollout. **However, 6 more commits landed AFTER T17:**

| Commit | What changed |
|--------|--------------|
| `7cac59f` (T14.2) | SocketClient became bidirectional: Device sends `DOWNLOAD_COMPLETE` back to Worker over the same TCP socket after the Backend ack |
| `a866e72` (T15.2) | `DeviceAgentService.onDestroy` calls `stopForeground(STOP_FOREGROUND_REMOVE)`; `onStartCommand` honors `ACTION_STOP` |
| `ebf9d7c` (T15.2) | `MainActivity.btnStopService` sends `ACTION_STOP` intent to Service |
| `5d27f67` (T15.3) | `MainActivity` requests `POST_NOTIFICATIONS` at runtime on Android 13+ |
| `2f987fb` (T15.3) | Two new strings in `strings.xml` (toast text for the runtime permission result) |
| `f095652` (T18.2) | Doc fix only (not in user-manu) |

After these 6 commits, `user-manu.md` has 4 documentation gaps and 1 documentation inaccuracy:

- §5.1 doesn't mention the Android 13+ notification permission prompt
- §5.5 describes the Socket as one-way (Device only receives); reality is bidirectional with `DOWNLOAD_COMPLETE` ack
- §5.5 doesn't document the Stop button flow
- §7.5 references a "Start button" that doesn't exist in the UI (the Service auto-starts from `Application.onCreate`)
- No section covers end-to-end testing with `android/scripts/mock_worker.py` (T16's deliverable)

This spec fixes all 5 items.

---

## Per-Item Specifications

### Item 1: §5.1 — Add Android 13+ notification permission step

**File / line:** `docs/user-manu.md:473-510` (section §5.1 "APK 安装")

**Current state (excerpt, line 487):**
> 脚本会自动完成四件事:① `./gradlew :app:assembleDebug` 构建 APK;② `adb install -r app-debug.apk` 安装/覆盖安装;③ `adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow` 授予全盘存储权限;④ `adb reverse tcp:8765 tcp:8765` ...

**Target:** Mention the **5th thing** that happens post-script (a permission dialog the user must tap on the device screen). The script itself doesn't grant this; it's a runtime OS dialog.

**Change:** Insert one new bullet "⑤" after the existing "④" describing the post-launch notification permission prompt. Applies to **both** 方式 1 (script) and 方式 2 (manual). Update the count from "四件事" to "四步 + 一项设备端确认".

**Acceptance:** A reader who follows §5.1 knows to expect and accept a "Allow notifications" dialog on the device.

### Item 2: §5.5 — Document Socket bidirectional protocol

**File / line:** `docs/user-manu.md:550-563` (section §5.5 "Device Socket 连接说明")

**Current state (excerpt, line 552):**
> Device 通过 TCP Socket 连接到 Worker,链路为 `adb reverse` 反向通道:
> ```
> Device (Android)  ──adb reverse──►  Worker (Desktop) :8765
>        SocketClient 连 127.0.0.1:8765 即等于连 Worker
> ```

**Target:** Replace the one-way description with the bidirectional protocol:
- Worker → Device: `DOWNLOAD_FILES` (push)
- Device → Worker: `DOWNLOAD_COMPLETE` (ack, after Backend ack)
- One short paragraph explaining the ack flow, with reference to spec §3.4

**Change:** Rewrite the opening paragraph of §5.5. Add a new paragraph or callout:
> **Socket 协议是双向的:**
> - Worker → Device: 任务到达时推 `DOWNLOAD_FILES` JSON(每行一条,以 `\n` 结束)
> - Device → Worker: 下载完成 + Backend ack 之后,Device 回送 `DOWNLOAD_COMPLETE` 事件(同样以 `\n` 结束)
> - Worker 在 `worker/device_dispatcher.py:send_and_await_ack` 处阻塞等 ack,最多 120 秒;超时则记为 `No ack from device`

**Acceptance:** A reader understands the Device writes to the socket, not just reads.

### Item 3: §5.5 — Add "停止 Device" paragraph

**File / line:** `docs/user-manu.md:550-563` end of section (after current content)

**Current state:** No mention of how to stop the Device Agent.

**Target:** Add a new subsection or paragraph at the end of §5.5:
> **停止 Device Agent:**
> 在 `MainActivity` 点「停止」按钮 → Service 收到 `ACTION_STOP` intent → `onStartCommand` 调 `stopSelf()` → `onDestroy` 调 `stopForeground(STOP_FOREGROUND_REMOVE)` → 通知栏消失。
>
> 重新启动只需要 `am start` 一次(脚本或手工),Service 会重新拉起并执行 `Application.onCreate` 中的初始化流程。

**Acceptance:** A reader knows the Stop button exists, what it does, and how to restart.

### Item 4: §7.5 — Remove the "启动" button reference

**File / line:** `docs/user-manu.md:756` (last sentence of §7.5)

**Current state (line 756):**
> 启动后 `MainActivity` 会显示 4 个配置输入框(Worker host/port/Backend URL/Device ID),按需修改后点击「保存」即可。最后点击「启动」按钮拉起 Foreground Service(通知栏出现 "3IS Device Agent" 常驻通知即表示已就绪)。

**Target:** Remove the "click Start button" sentence; rewrite to reflect the actual behavior.

**Change:** Replace the last clause with:
> 启动后 `MainActivity` 会显示 4 个配置输入框(Worker host/port/Backend URL/Device ID),按需修改后点击「保存」即可。`Foreground Service` 由 `Application.onCreate` 自动拉起,无需手动点启动按钮;通知栏出现 "3IS Device Agent" 常驻通知即表示已就绪。

**Acceptance:** A reader doesn't look for a Start button that doesn't exist.

### Item 5: §10.4 (NEW) — End-to-end testing with `mock_worker.py`

**File / line:** `docs/user-manu.md` (insert after the existing §10.3 "相关文档" subsection, before the `## Changelog` section)

**Current state:** No end-to-end testing section exists.

**Target:** New section explaining how to use `android/scripts/mock_worker.py` to validate the Device Agent end-to-end without a real transaction.

**Content outline:**
- §10.4 端到端测试(mock_worker)
  - 简介:`android/scripts/mock_worker.py` 是一个 59 行 Python TCP server,模拟 Worker 推送 `DOWNLOAD_FILES`,并等待 Device 回送 `DOWNLOAD_COMPLETE`
  - 适用场景:在没有真实 Backend 业务事务的情况下,验证 Device Agent 的下载/校验/回送 ack 链路
  - 步骤:
    1. 启动一个本地 HTTP server 模拟文件源(`python3 -m http.server 9000 --directory /tmp/sample`)
    2. 计算 MD5(`md5sum /tmp/sample.jpg`)
    3. 在桌面端跑 `python3 android/scripts/mock_worker.py "http://<host>:9000/sample.jpg" "<md5>"`
    4. 设备端接收 `DOWNLOAD_FILES` → 下载 → MD5 校验 → 写 `/sdcard/3is/att_mock0001.jpg` → 回送 ack
    5. 在 mock worker 的 stdout 看到 `ack: {...all_success: true...}`
    6. 在设备端 `adb shell ls /sdcard/3is/` 看到 `att_mock0001.jpg`
  - 错误注入:把 MD5 改错,验证 Device 返回 `MD5_MISMATCH`;把 URL 改 404,验证 `NETWORK_ERROR`

**Acceptance:** A reader can run an end-to-end smoke test of the Device Agent without involving the Backend.

---

## Changelog Entry (V1.4)

Add a new entry at the top of the `## Changelog` section (after the existing V1.3 entry):

```
**V1.4 (2026-06-16)**
- §5.1 APK 安装补充 Android 13+ 通知权限运行时授权说明
- §5.5 Socket 连接说明改写为双向协议(Worker→Device 推 DOWNLOAD_FILES,Device→Worker 回送 DOWNLOAD_COMPLETE)
- §5.5 末尾新增"停止 Device Agent"小节(ACTION_STOP 流程)
- §7.5 删除虚构的"启动"按钮说法,改为说明 Service 由 Application.onCreate 自启
- §10.4 新增"端到端测试(mock_worker)"章节
```

---

## Out of Scope

- No code changes (no Kotlin, no Python)
- No new test coverage
- No spec changes (the spec at `docs/superpowers/specs/2026-06-12-device-android-app-design.md` is correct — the drift is in user-manu only)
- No changes to other doc files (user-manu.md only)
- No new subagent dispatch (5 small deterministic edits)
- No `writing-plans` ceremony (this 5-item spec is small enough to execute directly after user approval)

---

## Self-Review Checklist

Before committing, verify:

- [ ] §5.1 mentions "5th thing" (notification permission prompt) for both 方式 1 and 方式 2
- [ ] §5.5 opening paragraph says "双向" with both directions documented
- [ ] §5.5 has a "停止 Device Agent" paragraph at the end
- [ ] §7.5 no longer mentions a "Start button"
- [ ] §10.4 exists with all 6 steps of the end-to-end test
- [ ] V1.4 changelog entry lists all 5 items
- [ ] 5 atomic commits, each with `docs(user-manu): ...` prefix
- [ ] `git grep "click 「启动」" docs/user-manu.md` returns no matches
- [ ] `git grep "Device 通过 TCP Socket 连接到 Worker" docs/user-manu.md` returns no matches (the old wording is replaced)
- [ ] `git grep "四件事" docs/user-manu.md` returns no matches (the count is updated)
