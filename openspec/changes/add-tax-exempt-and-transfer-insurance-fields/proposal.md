# Proposal: Add Tax-Exempt and Transfer Insurance Fields

## Summary

为每个投保事务(transaction)增加两个新属性：
1. **免税投保(tax_exempt)**: 标识该保单是否享受免税政策
2. **转保(transfer)**: 标识该保单是否为转保业务

## Motivation

当前系统仅支持`NEW`(新保)和`RENEWAL`(续保)两种业务类型，缺少对以下业务场景的支持：

- **免税投保**: 某些特定客户(如残疾人、公务员等)可享受税收减免政策，需要单独标识
- **转保**: 从其他保险公司转入的保单需要特别处理，与新保和续保不同

## User Impact

- **车险业务人员**: 需要在提交投保申请时标记免税和转保属性
- **后台运营**: 需要能查询和统计免税/转保业务数据
- **RPA流程**: 需要根据这些属性执行不同的处理逻辑

## Scope

### In Scope
- 数据库`transactions`表增加`tax_exempt`和`is_transfer`字段
- Backend API修改支持这两个新字段的传入和返回
- 前端`SubmitApplication`表单增加免税/转保输入项
- 前端`Transaction`类型定义更新

### Out of Scope
- RPA流程逻辑修改(仅添加数据字段)
- 新的API端点或删除现有端点
- 数据库迁移脚本(手动alter table)

## Success Criteria

1. 创建交易时可以指定`tax_exempt`和`is_transfer`字段，默认为`false`
2. 交易列表和详情API返回完整的两个字段
3. 前端提交表单支持选择免税/转保
4. 类型定义完整且前后端一致

## Non-Goals

- 不修改现有业务逻辑流程
- 不添加新的业务类型枚举
- 不实现税收计算或减免逻辑
