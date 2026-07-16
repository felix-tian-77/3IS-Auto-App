# Tasks: Store Customer Phone as Plaintext

## Implementation Tasks

### Phase 1: Backend Model & Service

- [ ] **1.1** Modify `backend/models/transaction.py`
  - Remove `customer_phone_encrypted = Column(String(256), nullable=True)`
  - Remove `customer_phone_search = Column(String(20), nullable=True, index=True)`
  - Add `customer_phone = Column(String(20), nullable=True, index=True)`

- [ ] **1.2** Modify `backend/services/transaction_service.py`
  - In `create_transaction`, replace
    `customer_phone_encrypted=request.customer_phone` and
    `customer_phone_search=request.customer_phone`
    with a single `customer_phone=request.customer_phone` assignment

### Phase 2: Backend API Layer

- [ ] **2.1** Modify `backend/api/v1/transactions.py`
  - In `list_transactions` search filter, replace
    `Transaction.customer_phone_search.contains(search)` with
    `Transaction.customer_phone.contains(search)`
  - In `list_transactions` response item dict, rename key
    `"customer_phone_encrypted"` to `"customer_phone"` (value
    `t.customer_phone`)
  - In `get_transaction` response dict, add
    `"customer_phone": txn.customer_phone`

- [ ] **2.2** Modify `backend/api/v1/tasks.py`
  - In the poll task response dict, rename key
    `"customer_phone_encrypted"` to `"customer_phone"` (value
    `txn.customer_phone`)

- [ ] **2.3** Modify `backend/services/dashboard_service.py`
  - In the recent transactions list dict, rename key
    `"customer_phone_encrypted"` to `"customer_phone"` (value
    `t.customer_phone`)

- [ ] **2.4** Modify `scripts/init_db.sql`
  - In the `CREATE TABLE transactions` DDL, replace the two lines:
    `customer_phone_encrypted VARCHAR(256),` and
    `customer_phone_search VARCHAR(20),` with a single
    `customer_phone VARCHAR(20),`
  - In the Indexes section, replace
    `CREATE INDEX idx_transactions_phone_search ON transactions(customer_phone_search);`
    with
    `CREATE INDEX idx_transactions_customer_phone ON transactions(customer_phone);`

### Phase 3: Backend Tests

- [ ] **3.1** Modify `tests/backend/test_transactions_list.py`
  - In `test_list_transactions_pagination`: replace
    `customer_phone_encrypted="enc", customer_phone_search="13800000000"`
    with `customer_phone="13800000000"`
  - In `test_list_transactions_phone_search`: replace
    `customer_phone_encrypted="enc-a", customer_phone_search="13812345678"`
    with `customer_phone="13812345678"`, and
    `customer_phone_encrypted="enc-b", customer_phone_search="13987654321"`
    with `customer_phone="13987654321"`
  - In `test_list_transactions_id_search`: replace
    `customer_phone_search="13800000001"` with
    `customer_phone="13800000001"`, and
    `customer_phone_search="13800000002"` with
    `customer_phone="13800000002"`

- [ ] **3.2** Inspect `backend/tests/test_dispatcher_no_worker.py`
  - The test builds a `TransactionCreateRequest` with `customer_phone` (schema
    field name unchanged) - verify no assertion references the old column name
    `customer_phone_encrypted` / `customer_phone_search`
  - Update any direct ORM assertions to use `customer_phone`

- [ ] **3.3** Search the rest of `tests/` and `backend/tests/` for
  `customer_phone_encrypted` and `customer_phone_search` references;
  update any found to `customer_phone`

### Phase 4: Frontend Changes

- [ ] **4.1** Modify `frontend/src/types/index.ts`
  - Rename `customer_phone_encrypted?: string` to `customer_phone?: string`
    on the `Transaction` interface

- [ ] **4.2** Modify `frontend/src/pages/staff/ApplicationDetail.tsx`
  - Change `txn.customer_phone_encrypted` to `txn.customer_phone`

- [ ] **4.3** Modify `frontend/src/pages/staff/TrackApplications.tsx`
  - Change column `dataIndex: 'customer_phone_encrypted'` to
    `dataIndex: 'customer_phone'`

- [ ] **4.4** Modify `frontend/src/pages/admin/Dashboard.tsx`
  - Change column `dataIndex: 'customer_phone_encrypted'` to
    `dataIndex: 'customer_phone'`

### Phase 5: Database Migration

- [ ] **5.1** Apply the schema migration on existing databases (manual SQL):
  ```sql
  ALTER TABLE transactions ADD COLUMN customer_phone VARCHAR(20);
  UPDATE transactions
    SET customer_phone = customer_phone_encrypted
    WHERE customer_phone_encrypted IS NOT NULL;
  CREATE INDEX ix_transactions_customer_phone ON transactions (customer_phone);
  ALTER TABLE transactions DROP COLUMN customer_phone_search;
  ALTER TABLE transactions DROP COLUMN customer_phone_encrypted;
  ```
  For fresh installs / test DBs, `Base.metadata.create_all` handles it.

### Phase 6: Verification

- [ ] **6.1** Run backend tests: `pytest backend/tests -q`
- [ ] **6.2** Run frontend typecheck / lint if configured
- [ ] **6.3** Manually verify create transaction writes `customer_phone`
- [ ] **6.4** Manually verify list/detail/dashboard/tasks endpoints return
      `customer_phone` key
- [ ] **6.5** Manually verify search by phone still works
