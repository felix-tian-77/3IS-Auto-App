## 1. 修改 TransactionService._generate_id 方法

- [ ] 1.1 修改 `backend/services/transaction_service.py:43-44` 的 `_generate_id` 方法
  - 日期格式从 `%Y%m%d%H%M%S` 改为 `%Y%m%d`
  - 方法体变为：`return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"`

## 2. 修改事务 ID 前缀

- [ ] 2.1 修改 `backend/services/transaction_service.py:67` 的 `create_transaction` 方法
  - `self._generate_id("TXN")` 改为 `self._generate_id("T")`

## 3. 修改附件 ID 前缀

- [ ] 3.1 修改 `backend/services/transaction_service.py:89` 的 `create_transaction` 方法
  - `self._generate_id("ATT")` 改为 `self._generate_id("A")`

## 4. 同步修改 transactions.py 硬编码 attachment_id

- [ ] 4.1 修改 `backend/api/v1/transactions.py:42`
  - `f"ATT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx:04d}"` 改为 `f"A-{datetime.now().strftime('%Y%m%d')}-{idx:04d}"`

## 5. 验证

- [ ] 5.1 启动后端，创建新事务，验证返回的 `transaction_id` 格式为 `T-YYYYMMDD-XXXXXXXX`
- [ ] 5.2 验证返回的 `attachment_id` 格式为 `A-YYYYMMDD-XXXXXXXX`
- [ ] 5.3 验证前端列表和详情页正常显示新格式 ID
- [ ] 5.4 验证历史事务（旧格式 ID）仍可正常查询和展示

## 6. 回归测试

- [ ] 6.1 在 `backend/tests/` 中添加 `test_id_generation.py`，验证：
  - `_generate_id("T")` 输出格式为 `T-YYYYMMDD-XXXXXXXX` 且长度合法
  - `_generate_id("A")` 输出格式为 `A-YYYYMMDD-XXXXXXXX` 且长度合法
  - 连续 1000 次调用无重复（生日冲突概率极低，但仍可作冒烟检查）
