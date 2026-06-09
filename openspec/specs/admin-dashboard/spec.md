# Purpose
TBD — describe purpose of admin-dashboard capability.

## Requirements

### Requirement: 统计卡片
系统 SHALL 在仪表盘顶部展示四个关键指标卡片：今日申请数、成功率、平均处理时间、设备负载。

#### Scenario: 页面加载
- **WHEN** 用户进入管理概览页面
- **THEN** 系统调用 GET /api/v1/statistics/dashboard，展示四个统计卡片

#### Scenario: 环比变化
- **WHEN** 今日数据与昨日有差异
- **THEN** 每个卡片显示环比变化百分比和箭头方向（上升绿色、下降红色）

### Requirement: 申请趋势图
系统 SHALL 以柱状图展示今日每小时的申请数量趋势。

#### Scenario: 展示趋势图
- **WHEN** 仪表盘数据加载完成
- **THEN** 系统渲染柱状图，X 轴为小时（8:00-18:00），Y 轴为申请数量

#### Scenario: 无数据
- **WHEN** 今日无任何申请
- **THEN** 图表区域显示"暂无数据"

### Requirement: 状态分布图
系统 SHALL 以饼图展示今日申请的状态分布。状态标签 SHALL 使用后端返回的中文文本（成功、处理中、待处理、失败），前端不再做英文→中文的二次映射。

#### Scenario: 展示饼图
- **WHEN** 仪表盘数据加载完成
- **THEN** 系统渲染饼图，每个状态扇区显示后端返回的中文 label

#### Scenario: 状态文本来源
- **WHEN** 前端渲染饼图图例
- **THEN** 直接使用 `status_distribution[i].status` 字段，不再通过 `STATUS_MAP` 转换

### Requirement: 最近申请列表
系统 SHALL 在仪表盘底部展示最近 10 条申请记录。

#### Scenario: 展示最近申请
- **WHEN** 仪表盘数据加载完成
- **THEN** 系统展示最近 10 条申请，包含申请编号、手机号、类型、状态、处理设备、耗时

#### Scenario: 点击跳转详情
- **WHEN** 用户点击某条申请的申请编号
- **THEN** 系统导航至 /staff/detail/{transaction_id}
