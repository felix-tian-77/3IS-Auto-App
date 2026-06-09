## ADDED Requirements

### Requirement: 基本信息展示
系统 SHALL 展示申请的完整基本信息，包括申请编号、手机号码、业务类型、当前状态、提交时间、处理设备。

#### Scenario: 页面加载
- **WHEN** 用户通过 /staff/detail/{id} 访问详情页
- **THEN** 系统调用 GET /api/v1/transactions/{id}，展示基本信息卡片

#### Scenario: 申请不存在
- **WHEN** API 返回 404 错误
- **THEN** 系统显示"申请不存在"提示，并提供返回列表的链接

### Requirement: 返回列表
系统 SHALL 提供返回按钮，允许用户返回申请跟踪列表页。

#### Scenario: 点击返回
- **WHEN** 用户点击"返回列表"按钮
- **THEN** 系统导航至 /staff/track，保留之前的筛选条件

### Requirement: 附件预览
系统 SHALL 以网格形式展示申请的所有附件，支持点击预览。

#### Scenario: 图片附件预览
- **WHEN** 用户点击 JPG/PNG 格式的附件
- **THEN** 系统弹出 Modal 显示图片的大图预览

#### Scenario: PDF 附件下载
- **WHEN** 用户点击 PDF 格式的附件
- **THEN** 系统触发浏览器下载该 PDF 文件

#### Scenario: 无附件
- **WHEN** 申请没有任何附件
- **THEN** 附件区域显示"暂无附件"

### Requirement: 处理时间线
系统 SHALL 以时间线形式按时间倒序展示申请的状态变更历史。

#### Scenario: 展示时间线
- **WHEN** 申请有多个状态变更记录
- **THEN** 系统从下往上按时间倒序展示，最新事件在最上方，每个节点显示时间、状态名称和描述

#### Scenario: 状态节点颜色
- **WHEN** 状态为"已完成"或"申请已提交"
- **THEN** 时间线节点显示绿色圆点
- **WHEN** 状态为"处理中"或"已派发"
- **THEN** 时间线节点显示蓝色圆点
- **WHEN** 状态为"失败"
- **THEN** 时间线节点显示红色圆点
