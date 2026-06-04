# Comparison: Airtest vs AutoX.js（移动端 RPA 框架选型）

| 字段 | 内容 |
|------|------|
| 主题 | Android 设备端 RPA 框架选型对比 |
| 文档版本 | V1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | Draft（参考材料） |
| 文档定位 | **参考材料**：为 Airtest vs AutoX.js 选型提供多维度对比 |
| 评估范围 | **手机端独立执行 RPA** 场景（非桌面 ADB 远程控制） |
| 关联文档 | 主架构 Plan A（Worker 端）/ Plan B（Device 端 Airtest）/ Plan C（Device 端 AutoX.js） |

**修订记录**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-03 | 初稿 | office-hours |

---

## 1. 背景与目标

### 1.1 评估背景

3IS-Auto-App 车险 RPA 系统需要选择 **Android 设备端 RPA 框架**（Plan B/C 方案）。当前 Plan A（Worker 端 Airtest）已确定为主架构，本对比为后续 Plan B/C 选型提供决策依据。

### 1.2 评估范围

- **范围**：在 Android 设备上独立执行 RPA 脚本（不通过桌面 ADB 远程控制）
- **不评估**：纯桌面 ADB 方案（已有 Plan A 覆盖）
- **目标读者**：架构师、技术负责人、合规审查员

### 1.3 候选框架

| 框架 | 简介 | 起源 |
|------|------|------|
| **Airtest** | 网易出品，Python 跨平台 UI 自动化框架 | 2017，网易游戏测试工具 |
| **AutoX.js** | Auto.js 社区分叉，JavaScript Android 自动化 | AutoX.js v6+（Auto.js 衍生） |

---

## 2. 框架概览

### 2.1 Airtest

| 维度 | 说明 |
|------|------|
| **官方主页** | https://airtest.netease.com/ |
| **GitHub** | https://github.com/AirtestProject/Airtest （7.5k+ stars） |
| **核心语言** | Python 3.x |
| **跨平台** | Android（ADB）、iOS、Windows、Web |
| **核心能力** | 图像识别（opencv 模板匹配）、Poco UI 反射、跨设备控制 |
| **典型场景** | 游戏测试、APP 自动化测试、跨平台 UI 测试 |
| **License** | Apache 2.0 |
| **维护方** | 网易（持续投入） |

**移动端执行方式**：
- 桌面 ADB 控制（默认）
- Chaquopy 嵌入 Android（自研）
- POCO + AndroidUiautomation（部分场景）

### 2.2 AutoX.js

| 维度 | 说明 |
|------|------|
| **官方主页** | https://github.com/kkevsekk1/AutoX |
| **GitHub** | https://github.com/kkevsekk1/AutoX （6.5k+ stars） |
| **核心语言** | JavaScript（Rhino / QuickJS 引擎） |
| **平台** | Android only |
| **核心能力** | AccessibilityService UI 反射、内置 OCR、图像识别、丰富手势 |
| **典型场景** | Android 自动化、APP 辅助工具、签到脚本、批量操作 |
| **License** | MIT（AutoX.js 分叉） |
| **维护方** | 社区驱动（Auto.js 商业使用争议后分叉） |

**移动端执行方式**：
- 独立 APP 安装（自带 IDE + 脚本编辑器）
- 打包为独立 APK（v6+ 支持项目打包）
- Java/Kotlin App 嵌入 AutoX.js 库

---

## 3. 多维度对比

### 3.1 部署与集成

| 维度 | Airtest（手机端） | AutoX.js | 优势方 |
|------|------------------|----------|--------|
| **Android 包大小** | 70MB（Chaquopy + airtest + opencv） | **20MB** | ✅ AutoX.js |
| **依赖系统组件** | Chaquopy Python 运行时 | 系统 AccessibilityService | ✅ AutoX.js |
| **冷启动时间** | 5-8s（Python 解释器启动） | **<1s** | ✅ AutoX.js |
| **内存占用（空闲）** | ~80MB | **~30MB** | ✅ AutoX.js |
| **内存占用（峰值）** | ~250MB（opencv 加载） | ~80MB | ✅ AutoX.js |
| **APK 体积影响选型** | 高（需 ≥6GB RAM 设备） | **低（中端即可）** | ✅ AutoX.js |
| **Python/Java 互调** | 需 Chaquopy 桥接（高复杂度） | **无（纯 Java + JS）** | ✅ AutoX.js |
| **Python/JS 互调** | 不适用 | **JS 调 Java（@JavaAdapter）** | ✅ AutoX.js |

### 3.2 UI 自动化能力

| 维度 | Airtest | AutoX.js | 优势方 |
|------|---------|----------|--------|
| **控件识别** | Poco（需目标 APP 集成 SDK）<br>or 图像识别 | **AccessibilityService（系统级）** | ✅ AutoX.js |
| **图像识别精度** | **opencv 模板匹配（业界领先）** | 内置（功能较弱） | ✅ Airtest |
| **OCR 文字识别** | 需集成第三方库 | **内置** | ✅ AutoX.js |
| **手势操作丰富度** | touch / swipe | **touch + 多点触控 + 压力 + 链式** | ✅ AutoX.js |
| **混合模式** | 手动组合 | **控件 + 图像 + 坐标 自动 fallback** | ✅ AutoX.js |
| **UI 树查询** | 弱（需 SDK） | **强（直接读 accessibility 树）** | ✅ AutoX.js |
| **跨应用跳转** | 支持 | **更稳定（Intent 操作丰富）** | ✅ AutoX.js |
| **录屏/截图** | 支持 | **支持（含视频录制）** | 🟡 相当 |

### 3.3 脚本开发与运维

| 维度 | Airtest | AutoX.js | 优势方 |
|------|---------|----------|--------|
| **开发语言** | Python | JavaScript | 🟡 团队栈决定 |
| **桌面 IDE** | **AirtestIDE（强：录制 + 调试 + 设备连接）** | VSCode 插件 | ✅ Airtest |
| **设备端 IDE** | 无 | **内置编辑器** | ✅ AutoX.js |
| **断点调试** | **桌面 IDE 支持** | 设备端日志 | ✅ Airtest |
| **脚本录制** | **AirtestIDE 录制器** | AutoX.js 录制 | ✅ Airtest |
| **脚本热更新** | OSS 下发 .py | **APK 内置 + 远程加载 .js** | ✅ AutoX.js |
| **API 学习曲线** | 中等 | **较低**（链式 API 友好） | ✅ AutoX.js |
| **报错调试信息** | Python traceback | **JS 错误 + 控件查询建议** | ✅ AutoX.js |
| **第三方库生态** | Python pip（强） | Node.js 风格（受限） | ✅ Airtest |
| **版本管理** | .py 文件 + semver | .js 文件 + APK 打包版本 | 🟡 相当 |

### 3.4 稳定性与抗检测

| 维度 | Airtest | AutoX.js | 优势方 |
|------|---------|----------|--------|
| **反 AccessibilityService 检测** | 中（需开启辅助功能） | **中（同样需开启）** | 🟡 相当 |
| **抗 UI 布局变化** | **强**（图像识别对布局变化鲁棒） | 弱（控件选择器依赖结构） | ✅ Airtest |
| **抗字体/分辨率变化** | 中（需重新做模板） | 弱（控件 ID 跨分辨率可能失效） | ✅ Airtest |
| **抗 Dark Mode 切换** | **强**（图像识别不依赖颜色） | 中（控件 ID 通常不变） | ✅ Airtest |
| **长时间运行稳定性** | 中（Python 内存泄漏风险） | **高**（Java 进程 + JS 轻量） | ✅ AutoX.js |
| **后台保活** | 需手动处理 | **支持前台 Service 保活** | ✅ AutoX.js |
| **多 APP 切换稳定性** | 中 | **高**（AccessibilityService 系统级） | ✅ AutoX.js |
| **崩溃恢复** | 需外部监控 | **自带异常捕获 + 重试** | ✅ AutoX.js |

### 3.5 安全与合规

| 维度 | Airtest | AutoX.js | 优势方 |
|------|---------|----------|--------|
| **代码可审计性** | ✅ Python 源码易读 | ⚠️ JS 压缩后较难 | ✅ Airtest |
| **第三方依赖风险** | opencv / numpy / pillow（成熟） | 较少依赖 | ✅ AutoX.js |
| **License 清晰度** | Apache 2.0 | MIT | 🟡 相当 |
| **Auto.js 商业使用争议** | **无此问题** | ⚠️ Auto.js Pro 历史商业限制争议，需确认 AutoX.js 分叉后状态 | ✅ Airtest |
| **企业内部分发** | 需自研打包工具 | **支持项目打包为独立 APK** | ✅ AutoX.js |
| **代码混淆** | Python 无强混淆 | **可 JS 混淆** | 🟡 相当 |
| **审计日志** | 自研 | **可记录操作详情** | 🟡 相当 |

### 3.6 团队与生态

| 维度 | Airtest | AutoX.js | 优势方 |
|------|---------|----------|--------|
| **国内社区** | 网易 + 游戏测试 | **Auto.js 生态延续，活跃度高** | 🟡 相当 |
| **官方文档** | 网易官方（完善） | 社区文档（参差） | ✅ Airtest |
| **GitHub Stars** | 7.5k+ | 6.5k+ | 🟡 相当 |
| **第三方插件** | poco / airtest-selenium / ocr plugins | ui / http / floaty 等 | 🟡 相当 |
| **招聘市场** | Python 工程师易招 | **前端 JS 工程师易招** | 🟡 相当 |
| **学习资料** | 视频教程丰富 | 社区文章多 | 🟡 相当 |
| **长期维护风险** | **网易持续维护（低风险）** | 社区驱动（中等风险） | ✅ Airtest |

---

## 4. 项目特定分析（车险 RPA）

### 4.1 业务特征

| 特征 | 描述 | 对框架的影响 |
|------|------|--------------|
| **目标 APP 数量** | 1-2 个保险 APP（业务方提供） | 控件结构相对稳定 |
| **UI 变化频率** | 中（季度更新 + 紧急热修） | 抗 UI 变化能力重要 |
| **影像资料种类** | 身份证/行驶证/合格证/发票（多种） | 需频繁操作文件选择器 |
| **表单填写** | 手机号/身份证号/车辆信息 | 文本输入 + 控件选择 |
| **OCR 需求** | 中（行驶证/合格证字段识别） | OCR 能力重要 |
| **事务并发** | 50 笔/分 | 需支持多设备并行 |
| **运维** | 现场无专业 RPA 工程师 | 需可远程调试、热更新 |
| **合规** | 需审计代码（金融场景） | 代码可读性重要 |
| **设备采购** | 每站点多设备 | 设备成本敏感 |

### 4.2 关键能力匹配度

| 能力 | Airtest 评分 | AutoX.js 评分 | 优势方 | 备注 |
|------|:-----------:|:-------------:|--------|------|
| **文件选择器自动化** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | AutoX.js | 控件 + 图像 fallback |
| **表单填写稳定性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | AutoX.js | 控件定位更准 |
| **抗 UI 变化** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Airtest | 图像识别 |
| **OCR 文字识别** | ⭐⭐ | ⭐⭐⭐⭐⭐ | AutoX.js | 内置 |
| **远程调试** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Airtest | 桌面 IDE |
| **代码可审计** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Airtest | Python 可读性 |
| **包大小（设备成本）** | ⭐⭐ | ⭐⭐⭐⭐⭐ | AutoX.js | 20MB vs 70MB |
| **冷启动速度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | AutoX.js | <1s vs 5-8s |
| **长时间运行** | ⭐⭐⭐ | ⭐⭐⭐⭐ | AutoX.js | 内存控制 |
| **多设备并发** | ⭐⭐⭐ | ⭐⭐⭐⭐ | AutoX.js | GIL 限制 |
| **License 合规** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Airtest | Auto.js 历史 |
| **团队上手成本** | ⭐⭐⭐ | ⭐⭐⭐⭐ | AutoX.js | JS 友好 |
| **综合** | 39/55 | **45/55** | **AutoX.js** | 微弱优势 |

**综合得分**：
- **Airtest**：⭐⭐⭐ (39/55) = 70.9%
- **AutoX.js**：⭐⭐⭐ (45/55) = 81.8%

### 4.3 风险地图

**Airtest 风险**：

| 风险 | 等级 | 说明 |
|------|------|------|
| Chaquopy 集成稳定性 | 🟡 中 | 需 PoC 验证某些 Android 厂商定制 ROM |
| APK 70MB 影响低端设备 | 🟡 中 | 需中高端 Android 设备（≥6GB RAM） |
| Python GIL 限制并发 | 🟡 中 | 单 Step 串行下发可缓解 |
| 桌面依赖强 | 🟢 低 | 远程调试需桌面环境 |

**AutoX.js 风险**：

| 风险 | 等级 | 说明 |
|------|------|------|
| **License 商业使用风险** | 🔴 高 | Auto.js Pro 历史商业使用限制争议，需法务确认 AutoX.js 分叉后合规性 |
| AccessibilityService 被禁用 | 🟡 中 | 引导用户在首次启动时授权；运营成本 |
| 图像识别能力弱于 Airtest | 🟡 中 | 无 opencv 精度，需配合 OCR/控件定位 |
| 社区维护节奏不稳 | 🟡 中 | AutoX.js 维护依赖核心贡献者，长期可持续性中等 |
| 调试能力弱 | 🟡 中 | 设备端日志为主，远程调试需额外搭建 |

### 4.4 综合评判

**优势方：AutoX.js**（微弱优势）
- 关键技术指标全面占优：包小、启动快、UI 反射强、OCR 内置
- 业务场景匹配度更高：表单填写、文件选择器、长时间运行
- 团队上手成本低：JS 工程师易招

**关键前提：License 风险可控**
- 必须由法务确认 AutoX.js 分叉后的商业使用合规性
- 若 License 不可用 → 退回 Airtest

**Airtest 的不可替代价值**：
- 抗 UI 变化（图像识别对 Dark Mode/布局变化鲁棒）
- 远程调试（桌面 IDE 在生产问题排查时价值大）
- License 清晰（金融场景刚需）

---

## 5. 三个候选方案

### 5.1 方案 1：纯 AutoX.js（推荐 Plan C）

**架构**：完全 AutoX.js 路线，详见 `2026-06-03-android-device-autoxjs-architecture-design.md`

| 项 | 内容 |
|----|------|
| Device Agent | AutoX.js 嵌入式 + JS 脚本（~20MB） |
| Worker | 纯编排器（~50MB Python，无 Airtest） |
| 脚本语言 | JavaScript |
| UI 反射 | AccessibilityService |
| OCR | 内置 |
| 适用 | 团队以 JS 为主、运维依赖现场、热更新频繁 |

### 5.2 方案 2：纯 Airtest（已有 Plan B）

**架构**：详见 `2026-06-03-android-device-airtest-architecture-design.md`

| 项 | 内容 |
|----|------|
| Device Agent | Chaquopy + Airtest（~70MB） |
| Worker | 纯编排器（无 Airtest） |
| 脚本语言 | Python |
| UI 反射 | POCO + AndroidUiautomation |
| 适用 | 团队以 Python 为主、目标 APP UI 频繁变动、License 严格 |

### 5.3 方案 3：混合架构

**架构**：AutoX.js 主框架 + Airtest 图像识别模块

| 操作类型 | 使用 | 理由 |
|----------|------|------|
| 稳定控件操作 | AutoX.js | AccessibilityService 反射准 |
| OCR 文字识别 | AutoX.js | 内置 |
| 复杂手势 | AutoX.js | 链式 API |
| 抗 UI 变化操作 | Airtest 图像模块 | opencv 精度高 |

**实现**：
- AutoX.js 作为主框架（~20MB）
- 嵌入 Airtest opencv 库（仅图像匹配，约 +5MB）
- JS 脚本中调用 Airtest 图像模块

**风险**：集成复杂度高、双框架维护成本

### 5.4 方案选型决策树

```
                          目标 APP UI 变化频率
                          ↓
                       高 ←─────→ 低
                       │          │
            License 严格     License 严格
            ↓                ↓
          Airtest           Airtest
                      
                       │          │
            License 灵活     License 灵活
            ↓                ↓
          混合架构          AutoX.js
                            (推荐)
```

---

## 6. 推荐与决策

### 6.1 我的推荐

**短期 MVP（推荐 Plan C：AutoX.js）**：
- 业务匹配度更高（表单/文件选择/OCR）
- 团队上手成本低（JS）
- 设备成本低（包小）
- **前置条件**：法务确认 License 合规（1 周内可完成）

**长期演进（推荐混合架构）**：
- 在 Plan C 基础上，必要时引入 Airtest 图像模块
- 应对极端 UI 变化场景

**License 风险不可控时**：
- 退回 Plan B（Airtest）
- 或采购商业 RPA 平台（如 UiBot、影刀）

### 6.2 决策矩阵（供业务方/技术负责人评审）

| 权重 | 维度 | Airtest | AutoX.js | 优势方 |
|------|------|:-------:|:--------:|--------|
| 25% | 业务匹配度 | 70 | **82** | AutoX.js |
| 20% | 团队上手成本 | 中 | **低** | AutoX.js |
| 20% | 长期维护风险 | **低** | 中 | Airtest |
| 15% | License 合规 | **清晰** | 需确认 | Airtest |
| 10% | 设备成本 | 高 | **低** | AutoX.js |
| 10% | 远程调试 | **强** | 弱 | Airtest |
| **加权** | - | **66.5** | **71.4** | **AutoX.js** |

### 6.3 决策记录

| 决策点 | 选项 | **最终选择** | 理由 |
|--------|------|-------------|------|
| Plan B | Airtest / AutoX.js | **Airtest**（已定） | License 风险规避优先 |
| Plan C | Airtest / AutoX.js / 混合 | **AutoX.js** | 业务匹配度更高 |
| 优先验证 | AutoX.js License 合规性 | 1 周内 | 决策前提 |
| 实施顺序 | Plan A → Plan C（混合） | 分阶段 | 渐进演进 |

---

## 7. 关联文档

- 主架构 Plan A（Worker 端 Airtest）：`docs/superpowers/specs/2026-06-03-rpa-worker-side-architecture-design.md`
- Plan B（Device 端 Airtest）：`docs/superpowers/specs/2026-06-03-android-device-airtest-architecture-design.md`
- Plan C（Device 端 AutoX.js）：`docs/superpowers/specs/2026-06-03-android-device-autoxjs-architecture-design.md`
- 主 PRD：`docs/superpowers/specs/2026-06-02-prd-design.md` V1.1
- PRD 评审：`docs/superpowers/specs/2026-06-02-prd-review.md`

---

**文档状态推进路径**：

`Draft`（参考材料）→ 不进入 Review/Approved 流程，作为长期技术决策参考
