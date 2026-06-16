# user-manu V1.4 Drift Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply 5 documentation drift fixes to `docs/user-manu.md` to align it with the 6 post-T17 code commits. No code changes.

**Architecture:** Each drift item is one atomic commit. Each commit touches a specific section of `user-manu.md`. No subagents needed (deterministic doc edits, no judgment calls).

**Tech Stack:** Markdown, Git. No tests required (this is documentation).

---

## File Structure

```
docs/user-manu.md                   (modify: 5 sections; ~55 line net addition)
├── §5.1 APK 安装                  (modify: add ⑤ notification permission step)
├── §5.5 Device Socket 连接说明    (modify: rewrite as bidirectional protocol + new "停止 Device" paragraph)
├── §7.5 Step 4: 启动 Device       (modify: remove "click Start button" wording)
├── §10.4 端到端测试(mock_worker)  (NEW: ~30 lines)
└── ## Changelog                   (add V1.4 entry at top)

docs/superpowers/specs/2026-06-16-user-manu-drift-fixes-design.md   (exists: source of truth for this plan)
```

---

## Task Dependency Graph

```
T1 (§5.1)  ─┐
T2 (§5.5)  ─┤
T3 (§5.5 stop)  ─┤── all independent ──→ T6 (V1.4 changelog) ──→ end
T4 (§7.5)  ─┤
T5 (§10.4 NEW) ─┘
```

All 6 commits can be done in any order (they touch non-overlapping regions of one file). T6 should be LAST so the changelog reflects the completed changes.

---

### Task T1: §5.1 — Add Android 13+ notification permission step

**Files:**
- Modify: `docs/user-manu.md:480-510` (section §5.1 "APK 安装")

- [ ] **Step 1: Read current state**

```bash
cd /data/workspaces/3IS-Auto-App
sed -n '480,510p' docs/user-manu.md
```

- [ ] **Step 2: Update the "四件事" paragraph in 方式 1**

Find this text:
```
脚本会自动完成四件事:① `./gradlew :app:assembleDebug` 构建 APK;② `adb install -r app-debug.apk` 安装/覆盖安装;③ `adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow` 授予全盘存储权限;④ `adb reverse tcp:8765 tcp:8765` 把设备的 localhost:8765 反向到桌面 Worker,并 `am start` 拉起 `MainActivity`。
```

Replace with:
```
脚本会自动完成四件事(之后需在设备屏幕上手动点一次通知权限弹窗,见下方 ⑤):① `./gradlew :app:assembleDebug` 构建 APK;② `adb install -r app-debug.apk` 安装/覆盖安装;③ `adb shell appops set --uid com.threeis.deviceagent MANAGE_EXTERNAL_STORAGE allow` 授予全盘存储权限;④ `adb reverse tcp:8765 tcp:8765` 把设备的 localhost:8765 反向到桌面 Worker,并 `am start` 拉起 `MainActivity`。

⑤ **Android 13+ 设备:首次启动后,系统会弹出通知权限请求框,请在设备屏幕点「允许」**。该权限授权后,通知栏才会显示 Foreground Service 的 "3IS Device Agent" 常驻通知;若拒绝,可到 `设置 → 应用 → 3IS Device Agent → 通知` 手动开启。
```

- [ ] **Step 3: Add the same ⑤ hint to 方式 2 (manual)**

In the manual section, after the `am start ...` line (around line 506), add:
```
# Android 13+ 设备:首次启动后,系统会弹通知权限框,需在设备屏幕点「允许」。
```

- [ ] **Step 4: Verify the change**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "Android 13+" docs/user-manu.md
grep -n "四件事" docs/user-manu.md
```

Expected: 2 matches for "Android 13+" (in 方式 1 and 方式 2). 0 matches for "四件事" (it's been replaced, but actually wait — keep "四件事" because the bullet count is still 4; only added a post-script ⑤ hint).

Re-check: keep "四件事" (the 4 script steps are still 4), add "Android 13+" mentions (2 places).

- [ ] **Step 5: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): note Android 13+ notification permission prompt in §5.1

T15.3 added a runtime POST_NOTIFICATIONS request in MainActivity.
Without this doc note, a user following §5.1 install steps would be
confused by the permission dialog that pops up on the device.

§5.1 方式 1 (script): clarify the script does 4 things and the
notification permission is a separate device-side confirmation.
§5.1 方式 2 (manual): add the same hint after the am start step."
```

### Task T2: §5.5 — Document Socket bidirectional protocol

**Files:**
- Modify: `docs/user-manu.md:550-563` (section §5.5 "Device Socket 连接说明")

- [ ] **Step 1: Read current state**

```bash
cd /data/workspaces/3IS-Auto-App
sed -n '550,565p' docs/user-manu.md
```

- [ ] **Step 2: Replace the opening paragraph and diagram**

Find this text (lines 552-557):
```
Device 通过 TCP Socket 连接到 Worker,链路为 `adb reverse` 反向通道:

\`\`\`
Device (Android)  ──adb reverse──►  Worker (Desktop) :8765
       SocketClient 连 127.0.0.1:8765 即等于连 Worker
\`\`\`
```

Replace with:
```
Device 与 Worker 之间是 **TCP Socket 双向通信**,链路为 `adb reverse` 反向通道:

\`\`\`
Worker (Desktop) :8765  ◄──adb reverse──  Device (Android) 127.0.0.1:8765
        │                                          ▲
        └── 推 DOWNLOAD_FILES(JSON) ──────────────┘
        ◄────────────────── 推 DOWNLOAD_COMPLETE(JSON) ──┘
\`\`\`

- **Worker → Device**:任务到达时推 `DOWNLOAD_FILES` 指令(每行一条 JSON,以 `\\n` 结束)
- **Device → Worker**:下载完成 + 上报 Backend `download-ack` 之后,Device 回送 `DOWNLOAD_COMPLETE` 事件(同样以 `\\n` 结束)
- Worker 在 `worker/device_dispatcher.py:send_and_await_ack` 处阻塞等 ack,最多 120 秒;超时则记为 `No ack from device`,该事务最终标记为 `RETRY_REQUIRED`

> **排错提示:** 若 mock worker 看到 `No ack from device`,先确认 `adb reverse tcp:8765 tcp:8765` 是否仍有效(USB 断开重连后会失效),再确认 Device 的 `MainActivity` 是否在运行。
```

- [ ] **Step 3: Verify the change**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "双向\|DOWNLOAD_COMPLETE" docs/user-manu.md
```

Expected: 1+ matches for "双向" and 2+ matches for "DOWNLOAD_COMPLETE" (one in the diagram, one in the bullets).

- [ ] **Step 4: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): rewrite §5.5 to document Socket bidirectional protocol

T14.2 made SocketClient bidirectional: Device sends DOWNLOAD_COMPLETE
back to Worker after the Backend ack. The previous §5.5 described
the socket as one-way (Worker pushes, Device receives), which was
the original pre-T14.2 design.

The new wording covers both directions, the JSON-line protocol,
the 120s ack timeout, and a troubleshooting hint for ack loss."
```

### Task T3: §5.5 — Add "停止 Device" paragraph

**Files:**
- Modify: `docs/user-manu.md` (insert at end of §5.5, after the modified content from T2)

- [ ] **Step 1: Read current state of §5.5 end**

```bash
cd /data/workspaces/3IS-Auto-App
sed -n '590,615p' docs/user-manu.md
```

Find the end of §5.5 (currently ends around line 612 where §5.6 starts).

- [ ] **Step 2: Insert "停止 Device Agent" subsection**

Before the `### 5.6 Device 目录结构与设备端沙箱` heading, insert a new subsection:

```
### 5.5.1 停止 Device Agent

在 `MainActivity` 点「停止」按钮:

1. 按钮发送 `ACTION_STOP` intent 给 `DeviceAgentService`
2. `Service.onStartCommand` 收到 action,调用 `stopSelf()` 触发 `onDestroy`
3. `Service.onDestroy` 依次:
   - `socket?.stop()` 关闭 Socket 客户端
   - `scope.cancel()` 取消所有协程
   - `stopForeground(STOP_FOREGROUND_REMOVE)` 移除通知栏的常驻通知
4. 通知栏 "3IS Device Agent" 通知消失

**重新启动:** 在设备桌面点应用图标,或执行 `am start -n com.threeis.deviceagent/.MainActivity`。`Application.onCreate` 会自动拉起新的 `Service`。
```

- [ ] **Step 3: Verify the change**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "5.5.1\|停止 Device\|ACTION_STOP" docs/user-manu.md
```

Expected: matches for all three.

- [ ] **Step 4: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): add §5.5.1 停止 Device Agent (ACTION_STOP flow)

T15.2 wired ACTION_STOP into MainActivity.btnStopService and
DeviceAgentService.onStartCommand, plus onDestroy now calls
stopForeground(STOP_FOREGROUND_REMOVE). Document the new flow
so users know what 'Stop' does and how to restart."
```

### Task T4: §7.5 — Remove the "启动" button reference

**Files:**
- Modify: `docs/user-manu.md:756` (last sentence of §7.5)

- [ ] **Step 1: Read current state**

```bash
cd /data/workspaces/3IS-Auto-App
sed -n '748,758p' docs/user-manu.md
```

- [ ] **Step 2: Replace the last sentence**

Find this text (line 756):
```
启动后 `MainActivity` 会显示 4 个配置输入框(Worker host/port/Backend URL/Device ID),按需修改后点击「保存」即可。最后点击「启动」按钮拉起 Foreground Service(通知栏出现 "3IS Device Agent" 常驻通知即表示已就绪)。
```

Replace with:
```
启动后 `MainActivity` 会显示 4 个配置输入框(Worker host/port/Backend URL/Device ID),按需修改后点击「保存」即可。`Foreground Service` 由 `Application.onCreate` 自动拉起(无单独的"启动"按钮),通知栏出现 "3IS Device Agent" 常驻通知即表示已就绪。
```

- [ ] **Step 3: Verify**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "点击「启动」按钮" docs/user-manu.md
```

Expected: 0 matches.

- [ ] **Step 4: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): remove fictitious 'Start button' in §7.5

The Device Agent UI (activity_main.xml) has 3 buttons: btnGrant,
btnSave, btnStopService. There is no btnStart. The Service is
auto-launched from DeviceAgentApplication.onCreate.

This drift was introduced by T17's docs sync. The current §7.5
incorrectly says 'click Start button', which leads users on a
wild-goose chase looking for a button that doesn't exist."
```

### Task T5: §10.4 (NEW) — End-to-end testing with mock_worker

**Files:**
- Modify: `docs/user-manu.md` (insert new section after §10.3, before `## Changelog`)

- [ ] **Step 1: Find the insertion point**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "^### 10\.\|^## Changelog" docs/user-manu.md
```

- [ ] **Step 2: Insert §10.4 before `## Changelog`**

Find the last `### 10.3` subsection and the `## Changelog` heading. Insert between them:

```
### 10.4 端到端测试(mock_worker)

在没有真实 Backend 业务事务的情况下,可以使用 `android/scripts/mock_worker.py` 验证 Device Agent 的下载/校验/回送 ack 链路。

#### 适用场景

- 调试 Device Agent 而不想拉起整个 Backend/Worker 链路
- 验证下载后文件落在 `/sdcard/3is/` 的正确位置
- 验证 MD5 校验失败、URL 404 等错误路径

#### 步骤

1. **准备一个测试文件**(本机或局域网可达即可):
   ```bash
   echo -n "hello-3is" > /tmp/sample.jpg
   python3 -m http.server 9000 --directory /tmp &
   # 在另一台机器访问,IP 替换为 http server 所在机器
   ```

2. **计算 MD5**:
   ```bash
   MD5=$(md5sum /tmp/sample.jpg | awk '{print $1}')
   echo "MD5=$MD5"
   ```

3. **运行 mock worker**(监听 :8765,接受一个 Device 连接,推一条 `DOWNLOAD_FILES`,等 Device 回 ack):
   ```bash
   python3 android/scripts/mock_worker.py "http://<host>:9000/sample.jpg" "$MD5"
   ```
   mock worker 会在 stdout 打印:
   ```
   Mock worker listening on :8765
   device connected: ('127.0.0.1', NNNNN)
   ack: {"event": "DOWNLOAD_COMPLETE", "transaction_id": "TXN-MOCK-0001", "all_success": true, "files": [...]}
   ```

4. **设备端验证**(在连接的 Android 设备 / 模拟器):
   ```bash
   adb shell ls -la /sdcard/3is/
   # 预期: att_mock0001.jpg,大小 9 字节("hello-3is")
   ```

#### 错误路径注入

- **MD5 不匹配**:把 mock_worker 的第三个参数改成错误的 MD5(任意 32 位 hex),Device 会返回 `success=false, errorReason=MD5_MISMATCH`,**不会**回写文件
- **URL 404**:把 URL 改成不存在的路径,Device 返回 `NETWORK_ERROR`
- **Sandbox clear 失败**:在 mock_worker 跑前,先 `adb push foo.bin /sdcard/3is/` 塞一个 Device Agent 创建不了的文件,触发 clear() 抛 SecurityException(非 STOPPED),Device 仍继续覆盖式下载并在 `download-ack` 中带 `sandbox_clear_failed=true`
```

- [ ] **Step 3: Verify the new section exists**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "^### 10\.4" docs/user-manu.md
```

Expected: 1 match (the new §10.4 heading).

- [ ] **Step 4: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): add §10.4 端到端测试(mock_worker) section

T16 added android/scripts/mock_worker.py as a test harness for the
Device Agent. Previously undocumented; this section provides:
- When to use it (debug without full Backend)
- 4-step recipe (start HTTP server, compute MD5, run mock, verify
  on device)
- 3 error-path injection scenarios (MD5 mismatch, URL 404, sandbox
  clear failure)
- Reference to the ack JSON shape (DOWNLOAD_COMPLETE event from T14.2)"
```

### Task T6: V1.4 changelog entry

**Files:**
- Modify: `docs/user-manu.md` (insert at top of `## Changelog` section, before existing V1.3 entry)

- [ ] **Step 1: Find the Changelog section**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "^## Changelog\|^**V1\." docs/user-manu.md
```

- [ ] **Step 2: Insert V1.4 entry above V1.3**

Find:
```
## Changelog

**V1.3 (2026-06-15)**
```

Insert before V1.3:
```
## Changelog

**V1.4 (2026-06-16)**
- §5.1 APK 安装补充 Android 13+ 通知权限运行时授权说明
- §5.5 Socket 连接说明改写为双向协议(Worker→Device 推 `DOWNLOAD_FILES`,Device→Worker 回送 `DOWNLOAD_COMPLETE`)
- §5.5.1 新增"停止 Device Agent"小节(`ACTION_STOP` → `stopForeground(STOP_FOREGROUND_REMOVE)`)
- §7.5 删除虚构的"启动"按钮说法,改为说明 Service 由 `Application.onCreate` 自启
- §10.4 新增"端到端测试(mock_worker)"章节

**V1.3 (2026-06-15)**
```

- [ ] **Step 3: Verify**

```bash
cd /data/workspaces/3IS-Auto-App
grep -n "^**V1\.4\|^**V1\.3" docs/user-manu.md
```

Expected: V1.4 appears before V1.3.

- [ ] **Step 4: Commit**

```bash
cd /data/workspaces/3IS-Auto-App
git add docs/user-manu.md
git commit -m "docs(user-manu): add V1.4 changelog entry (5 drift fixes)"
```

---

## Self-Review

**1. Spec coverage:**

| Spec section | Task |
|--------------|------|
| Item 1 (§5.1 + Android 13+ hint) | T1 ✓ |
| Item 2 (§5.5 bidirectional protocol) | T2 ✓ |
| Item 3 (§5.5.1 stop paragraph) | T3 ✓ |
| Item 4 (§7.5 remove Start button) | T4 ✓ |
| Item 5 (§10.4 new section) | T5 ✓ |
| V1.4 changelog entry | T6 ✓ |
| Self-review checklist from spec | Each task step 3-4 verifies ✓ |

No gaps.

**2. Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details", "appropriate error handling" in any task. All 6 commits have explicit diff text and exact commands.

**3. Consistency:** The wording "Android 13+" / "POST_NOTIFICATIONS" / "ACTION_STOP" / "DOWNLOAD_COMPLETE" / "stopForeground(STOP_FOREGROUND_REMOVE)" is consistent with the source code from T14.2/T15.2/T15.3 commits and the spec section §3.4.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-16-user-manu-drift-fixes.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
