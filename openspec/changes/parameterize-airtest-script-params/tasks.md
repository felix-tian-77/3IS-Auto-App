## 1. 修改 `old_vehicle.air/old_vehicle.py`

- [x] 1.1 替换 `:12` 的 `customer_phone =  "19110898582"` 为统一参数块：
  ```python
  import os

  # ---- Parameters (injected by Worker via environment variables) ----
  transaction_id = os.environ.get("TRANSACTION_ID")
  holder_phone   = os.environ.get("HOLDER_PHONE")
  customer_phone = os.environ.get("CUSTOMER_PHONE")
  business_type  = os.environ.get("BUSINESS_TYPE")
  tax_exempt     = os.environ.get("TAX_EXEMPT", "false").lower() == "true"
  is_transfer    = os.environ.get("IS_TRANSFER", "false").lower() == "true"

  # 手机号 fallback：优先客户手机号，其次被保险人手机号，最后测试默认值
  mobile_phone = customer_phone or holder_phone or "19110898582"
  ```
- [x] 1.2 确认 `:94` 的 `set_text(mobile_phone)` 不变（变量现已正确定义，bug 已修复）

## 2. 修改 `new_vehicle.air/old_vehicle.py`

- [x] 2.1 替换 `:14-15` 的部分参数化代码：
  ```python
  import os
  mobile_phone = os.environ.get("CUSTOMER_PHONE") or os.environ.get("HOLDER_PHONE") or "19110898582"
  ```
  为统一参数块（与 Task 1.1 相同）。
- [x] 2.2 确认 `:97` 的 `set_text(mobile_phone)` 不变

## 3. 修改 `renew/renew_01.air/renew_01.py`

- [x] 3.1 替换 `:14` 的 `mobile_phone = "19110898582"` 为统一参数块（与 Task 1.1 相同）
- [x] 3.2 将 `:96` 的 `set_text("19110898582")` 改为 `set_text(mobile_phone)`

## 4. 验证

- [x] 4.1 人工检查 3 个脚本的参数块格式完全一致
- [x] 4.2 人工检查 3 个脚本中不再有硬编码的 `"19110898582"`（fallback 默认值除外）
- [x] 4.3 人工检查 `old_vehicle.air/old_vehicle.py` 中 `mobile_phone` 变量在 `set_text` 调用前已定义
