# Tasks: Add Tax-Exempt and Transfer Insurance Fields

## Implementation Tasks

### Phase 1: Backend Changes

- [ ] **1.1** Modify `backend/models/transaction.py`
  - Add `tax_exempt = Column(Boolean, default=False, nullable=False)` field
  - Add `is_transfer = Column(Boolean, default=False, nullable=False)` field

- [ ] **1.2** Modify `backend/schemas/transaction.py`
  - Add `tax_exempt: bool = False` to `TransactionCreateRequest`
  - Add `is_transfer: bool = False` to `TransactionCreateRequest`
  - Add `tax_exempt: bool` to `TransactionResponse`
  - Add `is_transfer: bool` to `TransactionResponse`

- [ ] **1.3** Modify `backend/services/transaction_service.py`
  - Update `create_transaction` to set `tax_exempt=request.tax_exempt` on Transaction
  - Update `create_transaction` to set `is_transfer=request.is_transfer` on Transaction

- [ ] **1.4** Modify `backend/api/v1/transactions.py`
  - Update `list_transactions` to include `tax_exempt` and `is_transfer` in response items
  - Update `get_transaction` to include `tax_exempt` and `is_transfer` in response

### Phase 2: Frontend Changes

- [ ] **2.1** Modify `frontend/src/types/index.ts`
  - Add `tax_exempt: boolean` to `Transaction` interface
  - Add `is_transfer: boolean` to `Transaction` interface

- [ ] **2.2** Modify `frontend/src/api/transactions.ts`
  - Update `createTransaction` function signature to accept `taxExempt` and `isTransfer` parameters
  - Update `createTransaction` function to include `tax_exempt` and `is_transfer` in `transactionPayload`
  - Update `CreateTransactionResponse` interface to include `tax_exempt` and `is_transfer`

- [ ] **2.3** Modify `frontend/src/pages/staff/SubmitApplication.tsx`
  - Add `tax_exempt` Form.Item with Switch component after business_type selector
  - Add `is_transfer` Form.Item with Switch component after tax_exempt
  - Update `handleSubmit` to pass both values from form to `createTransaction`
  - Update form `initialValues` to include `{ tax_exempt: false, is_transfer: false }`

### Phase 3: Database Migration

- [ ] **3.1** Create Alembic migration for new columns (if Alembic is configured)
  ```sql
  ALTER TABLE transactions ADD COLUMN tax_exempt BOOLEAN NOT NULL DEFAULT FALSE;
  ALTER TABLE transactions ADD COLUMN is_transfer BOOLEAN NOT NULL DEFAULT FALSE;
  ```
  Or run the SQL directly if not using Alembic.

### Phase 4: Verification

- [ ] **4.1** Verify backend API accepts new fields in transaction creation
- [ ] **4.2** Verify backend API returns new fields in list and detail endpoints
- [ ] **4.3** Verify frontend form displays and submits new fields correctly
- [ ] **4.4** Run typecheck and lint if available
