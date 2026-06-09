# Purpose
TBD — describe purpose of worker-monitor capability.

### Requirement: 统计卡片
系统 SHALL 在设备监控页面顶部展示四个统计卡片：在线设备数、离线设备数、处理中任务数、排队中任务数。

#### Scenario: 页面加载
- **WHEN** 用户进入设备监控页面
- **THEN** 系统调用 GET /api/v1/workers，展示四个统计卡片

### Requirement: 设备列表
系统 SHALL 以表格形式展示所有 Worker 节点及其绑定的 Android 设备信息。

#### Scenario: 展示设备列表
- **WHEN** 设备数据加载完成
- **THEN** 表格展示每台设备的：Worker 名称/IP、绑定设备型号/Android版本、在线状态、CPU、内存、设备电量、存储、最后心跳时间

#### Scenario: 无设备
- **WHEN** 系统中无任何注册的 Worker
- **THEN** 表格显示空状态提示"暂无设备"

### Requirement: 在线状态标识
系统 SHALL 用颜色标签区分设备的在线和离线状态。

#### Scenario: 在线设备
- **WHEN** Worker 最后心跳时间在 60 秒内
- **THEN** 状态列显示绿色标签"在线"

#### Scenario: 离线设备
- **WHEN** Worker 最后心跳时间超过 60 秒
- **THEN** 状态列显示红色标签"离线"，CPU/内存/电量/存储列显示"--"

### Requirement: 电量预警
系统 SHALL 对电量低于 30% 的设备进行视觉预警。

#### Scenario: 低电量预警
- **WHEN** 设备电量低于 30%
- **THEN** 电量数值显示为橙色

#### Scenario: 正常电量
- **WHEN** 设备电量大于等于 30%
- **THEN** 电量数值显示为绿色

### Requirement: 状态筛选
系统 SHALL 支持按在线状态筛选设备列表。

#### Scenario: 筛选在线设备
- **WHEN** 用户选择筛选"在线"
- **THEN** 表格仅显示在线状态的设备

#### Scenario: 筛选离线设备
- **WHEN** 用户选择筛选"离线"
- **THEN** 表格仅显示离线状态的设备
