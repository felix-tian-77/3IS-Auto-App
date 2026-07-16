# Proposal: Store Customer Phone as Plaintext

## Summary

将 `transactions` 表中的 `customer_phone` 字段从当前的"伪加密"存储方式改为明文存储。移除 `customer_phone_encrypted` 和 `customer_phone_search` 两个字段，统一使用单一的 `customer_phone` 字段。

## Motivation

当前实现存在以下问题：

1. **"伪加密"误导**：`customer_phone_encrypted` 字段名为"加密"，但实际存储的是明文（`transaction_service.py:77` 直接把 `request.customer_phone` 赋给 `customer_phone_encrypted`），字段名与实际语义不符，造成混淆
2. **冗余字段**：`customer_phone_search` 与 `customer_phone_encrypted` 存储完全相同的值，仅为搜索而保留，增加了维护成本和数据不一致风险
3. **未实现的加密设计**：代码中无任何加解密逻辑（无 Fernet/AES/Cipher），加密字段名暗示的安全能力实际并不存在
4. **简化数据模型**：明文存储后，搜索、展示、传递均直接使用单一字段，代码更清晰

## User Impact

- **后台运营/API 消费方**：API 响应字段由 `customer_phone_encrypted` 更名为 `customer_phone`，需同步更新前端类型定义
- **运维/DBA**：数据库 schema 简化，移除冗余列
- **开发**：消除字段名与语义不符的混淆，降低后续维护认知成本

## Scope

### In Scope
- Backend `Transaction` 模型：移除 `customer_phone_encrypted`、`customer_phone_search`，新增 `customer_phone` 列
- Backend Service / API：所有引用点改为 `customer_phone`
- `scripts/init_db.sql`：同步更新建表 DDL 与索引
- Backend 测试：更新 `tests/backend/test_transactions_list.py` 等测试中的字段引用
- Frontend 类型定义与页面：字段重命名
- 数据库迁移说明（手动 ALTER TABLE）

### Out of Scope
- 真正的加密/脱敏实现（前端展示层已有 `maskPhone` 函数，DB 层不再追求加密）
- 新的 API 端点
- 历史数据迁移脚本（提供 SQL，由运维决定执行）

## Success Criteria

1. `transactions` 表仅保留 `customer_phone` 一列存储电话
2. 创建交易时 `customer_phone` 正确写入
3. 列表/详情/Dashboard/Tasks API 返回 `customer_phone` 字段
4. 前端类型与页面正确消费新字段名
5. 搜索功能基于 `customer_phone` 列工作
6. 所有相关测试通过

## Non-Goals

- 不实现真正的加密存储
- 不修改 `customer_id_no_encrypted` 字段（本次仅处理 phone，保持范围聚焦）
- 不引入数据脱敏中间件
