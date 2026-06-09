# Purpose
TBD — describe purpose of track-applications capability.

## Requirements

### Requirement: 申请列表展示
系统 SHALL 以表格形式展示所有申请记录，包含申请编号、手机号码、业务类型、状态、提交时间、操作列。

#### Scenario: 页面加载
- **WHEN** 用户进入申请跟踪页面
- **THEN** 系统调用 GET /api/v1/transactions 获取第 1 页数据（每页 20 条），并以表格展示

#### Scenario: 空列表
- **WHEN** 系统中无任何申请记录
- **THEN** 表格显示空状态提示"暂无申请记录"

### Requirement: 搜索与筛选
系统 SHALL 支持按手机号或申请编号搜索（手机号优先匹配，匹配不到再按申请编号），以及按状态和业务类型筛选。

#### Scenario: 按手机号搜索
- **WHEN** 用户在搜索框输入 "1381" 并点击查询
- **THEN** 系统调用 API 传入 `phone=1381` 参数，表格刷新为手机号包含 "1381" 的所有申请（不再依赖正则判断手机号格式）

#### Scenario: 按申请编号搜索
- **WHEN** 用户在搜索框输入 "TXN-2026" 并点击查询
- **THEN** 系统调用 API 传入 `transaction_id=TXN-2026` 参数，表格刷新为申请编号包含 "TXN-2026" 的所有申请

#### Scenario: 组合筛选
- **WHEN** 用户同时设置搜索关键词、状态筛选和业务类型筛选
- **THEN** 系统调用 API 传入所有筛选参数，表格显示同时满足所有条件的申请

#### Scenario: 重置筛选
- **WHEN** 用户清空搜索框并将筛选下拉框恢复为"全部"
- **THEN** 系统重新加载全部申请数据

### Requirement: 状态标签
系统 SHALL 使用不同颜色的标签展示申请状态。

#### Scenario: 状态颜色映射
- **WHEN** 申请状态为"待处理"
- **THEN** 显示橙色标签"待处理"
- **WHEN** 申请状态为"已派发"或"处理中"
- **THEN** 显示蓝色标签
- **WHEN** 申请状态为"已完成"
- **THEN** 显示绿色标签"已完成"
- **WHEN** 申请状态为"失败"
- **THEN** 显示红色标签"失败"

### Requirement: 分页
系统 SHALL 支持分页浏览申请列表。

#### Scenario: 翻页
- **WHEN** 用户点击第 2 页
- **THEN** 系统调用 API 传入 page=2，表格刷新为第 2 页数据

#### Scenario: 修改每页条数
- **WHEN** 用户将每页条数从 20 改为 50
- **THEN** 系统调用 API 传入 page_size=50，表格刷新显示 50 条数据

### Requirement: 跳转详情
系统 SHALL 支持从列表跳转至申请详情页。

#### Scenario: 点击详情
- **WHEN** 用户点击某条申请的"详情"按钮
- **THEN** 系统导航至 /staff/detail/{transaction_id}

### Requirement: 手动刷新
系统 SHALL 提供刷新按钮，允许用户手动重新加载当前页数据。

#### Scenario: 点击刷新
- **WHEN** 用户点击刷新按钮
- **THEN** 系统重新调用 API 获取当前页数据，保留当前筛选条件
