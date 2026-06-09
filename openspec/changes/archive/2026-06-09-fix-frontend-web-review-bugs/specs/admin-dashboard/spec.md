## MODIFIED Requirements

### Requirement: 状态分布图
系统 SHALL 以饼图展示今日申请的状态分布。状态标签 SHALL 使用后端返回的中文文本（成功、处理中、待处理、失败），前端不再做英文→中文的二次映射。

#### Scenario: 展示饼图
- **WHEN** 仪表盘数据加载完成
- **THEN** 系统渲染饼图，每个状态扇区显示后端返回的中文 label

#### Scenario: 状态文本来源
- **WHEN** 前端渲染饼图图例
- **THEN** 直接使用 `status_distribution[i].status` 字段，不再通过 `STATUS_MAP` 转换
