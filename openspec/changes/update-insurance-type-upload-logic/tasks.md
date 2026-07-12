# Tasks: Update Insurance Type Upload Logic

## Implementation Tasks

### Phase 1: Backend Enum Changes

- [ ] **1.1** Modify `backend/models/transaction.py`
  - Update `BusinessType` enum: `NEW` → `NEW_VEHICLE`, `RENEWAL` → `OLD_VEHICLE`
  - Add `holder_phone = Column(String(20), nullable=True)` field

- [ ] **1.2** Modify `backend/models/attachment.py`
  - Update `FileType` enum to include:
    - `ID_CARD_FRONT` - 身份证正面
    - `ID_CARD_BACK` - 身份证反面
    - `DRIVING_LICENSE_FRONT` - 行驶证正面
    - `DRIVING_LICENSE_BACK` - 行驶证反面
    - `ELECTRONIC_INVOICE` - 电子发票
    - `CERTIFICATE` - 合格证
    - `TAX_EXEMPT_CERT` - 车船税减免税证明
    - `INSURER_ID_CARD_FRONT` - 投保人身份证正面
    - `INSURER_ID_CARD_BACK` - 投保人身份证反面

### Phase 2: Backend Schema Changes

- [ ] **2.1** Modify `backend/schemas/transaction.py`
  - Add `holder_phone: Optional[str] = None` to `TransactionCreateRequest`
  - Update `TransactionResponse` to include `holder_phone`

### Phase 3: Backend Service Changes

- [ ] **3.1** Modify `backend/services/transaction_service.py`
  - Update storage path to: `{transaction_id}/{file_type}{ext}`
  - Add `REQUIRED_FILES` and `ADDITIONAL_FILES` validation maps
  - Add validation logic to check required files based on business_type, tax_exempt, is_transfer
  - Store `holder_phone` on transaction if provided

### Phase 4: Backend API Changes

- [ ] **4.1** Modify `backend/api/v1/transactions.py`
  - Update `list_transactions` to include `holder_phone` in response
  - Update `get_transaction` to include `holder_phone` in response

### Phase 5: Frontend Type Changes

- [ ] **5.1** Modify `frontend/src/types/index.ts`
  - Update `BusinessType` to `'NEW_VEHICLE' | 'OLD_VEHICLE'`
  - Add `holder_phone?: string` to `Transaction` interface
  - Add `holder_phone?: string` to `CreateTransactionResponse` interface
  - Update `CreateTransactionRequest` to include new fields

### Phase 6: Frontend API Changes

- [ ] **6.1** Modify `frontend/src/api/transactions.ts`
  - Update `createTransaction` function to accept and send `holder_phone` parameter

### Phase 7: Frontend Form Changes

- [ ] **7.1** Modify `frontend/src/pages/staff/SubmitApplication.tsx`
  - Change `Segmented` to `RadioGroup` for business_type selection
  - Update business_type options to '新车投保'/'旧车投保' with values 'NEW_VEHICLE'/'OLD_VEHICLE'
  - Add `holder_phone` Form.Item (shown when is_transfer is true)
  - Implement dynamic required files display based on business_type and switches
  - Pass holder_phone to createTransaction

- [ ] **7.2** Modify `frontend/src/components/FileUpload.tsx`
  - Add `requiredFiles?: string[]` prop
  - Display required files hint above upload area
  - Show validation message if files don't match required list

### Phase 8: Database Migration

- [ ] **8.1** Run manual SQL migration
  ```sql
  ALTER TABLE transactions ADD COLUMN holder_phone VARCHAR(20);
  ```

### Phase 9: Verification

- [ ] **9.1** Verify backend API accepts NEW_VEHICLE/OLD_VEHICLE business_type
- [ ] **9.2** Verify backend validates required files based on business_type
- [ ] **9.3** Verify storage path includes transaction_id and file_type
- [ ] **9.4** Verify frontend form shows dynamic required files
- [ ] **9.5** Verify frontend RadioGroup works as single-select
- [ ] **9.6** Verify is_transfer shows holder_phone field
- [ ] **9.7** Run typecheck and lint
