## ADDED Requirements

### Requirement: 业务类型选择
系统 SHALL 提供新保和续保两种业务类型供用户选择，默认选中"新保"。

#### Scenario: 默认选中新保
- **WHEN** 用户进入提交申请页面
- **THEN** 业务类型默认选中"新保"

#### Scenario: 切换业务类型
- **WHEN** 用户点击"续保"选项
- **THEN** 业务类型切换为"续保"，后续提交时将 business_type 设为 RENEWAL

### Requirement: 手机号输入与校验
系统 SHALL 提供手机号输入框，仅允许输入 11 位中国大陆手机号。

#### Scenario: 输入合法手机号
- **WHEN** 用户输入 "13812341234"
- **THEN** 校验通过，无错误提示

#### Scenario: 输入非法手机号
- **WHEN** 用户输入 "1234" 并尝试提交
- **THEN** 系统显示错误提示"请输入正确的手机号码"，阻止提交

#### Scenario: 手机号为空
- **WHEN** 用户未输入手机号直接点击提交
- **THEN** 系统显示错误提示"请输入手机号码"，阻止提交

### Requirement: 文件上传
系统 SHALL 提供文件上传区域，支持点击选择或拖拽上传，允许一次选择多个文件。

#### Scenario: 点击上传文件
- **WHEN** 用户点击上传区域并选择 3 个 JPG 文件
- **THEN** 系统显示已选文件列表，包含文件名和大小

#### Scenario: 拖拽上传文件
- **WHEN** 用户拖拽 2 个文件到上传区域
- **THEN** 系统显示已选文件列表，包含文件名和大小

#### Scenario: 删除已选文件
- **WHEN** 用户在已选文件列表中点击某个文件的删除按钮
- **THEN** 该文件从列表中移除

#### Scenario: 上传不支持的文件格式
- **WHEN** 用户选择 .docx 文件
- **THEN** 系统拒绝该文件并提示"仅支持 JPG、PNG、PDF 格式"

#### Scenario: 上传超大文件
- **WHEN** 用户选择超过 20MB 的文件
- **THEN** 系统拒绝该文件并提示"文件大小不能超过 20MB"

### Requirement: 表单提交
系统 SHALL 将业务类型、手机号和文件以 multipart/form-data 格式提交至 POST /api/v1/transactions。

#### Scenario: 提交成功
- **WHEN** 用户填写合法手机号、选择业务类型、上传至少 1 个文件并点击"提交申请"
- **THEN** 系统调用 POST /api/v1/transactions，成功后显示通知包含申请编号和预计等待时间，并清空表单

#### Scenario: 提交失败
- **WHEN** API 返回错误响应
- **THEN** 系统显示错误信息，表单内容保留不丢失

#### Scenario: 提交中显示加载状态
- **WHEN** 用户点击"提交申请"后 API 请求进行中
- **THEN** 提交按钮显示加载状态且不可重复点击

### Requirement: 表单重置
系统 SHALL 提供重置按钮，清空所有输入和已选文件。

#### Scenario: 点击重置
- **WHEN** 用户点击"重置"按钮
- **THEN** 手机号清空，已选文件清空，业务类型恢复为默认"新保"
