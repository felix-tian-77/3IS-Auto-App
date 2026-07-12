# Design: Add Tax-Exempt and Transfer Insurance Fields

## Overview

This document describes the technical design for adding `tax_exempt` and `is_transfer` boolean fields to the insurance transaction model.

## Database Changes

### Table: `transactions`

Add two new columns to the `transactions` table:

```sql
ALTER TABLE transactions ADD COLUMN tax_exempt BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE transactions ADD COLUMN is_transfer BOOLEAN NOT NULL DEFAULT FALSE;
```

### ORM Model (`backend/models/transaction.py`)

```python
class Transaction(Base):
    # ... existing fields ...

    tax_exempt = Column(Boolean, default=False, nullable=False)
    is_transfer = Column(Boolean, default=False, nullable=False)
```

## Backend API Changes

### Schema Changes (`backend/schemas/transaction.py`)

Update `TransactionCreateRequest` to include new fields:

```python
class TransactionCreateRequest(BaseModel):
    # ... existing fields ...
    tax_exempt: bool = False
    is_transfer: bool = False
```

Update `TransactionResponse` to include new fields:

```python
class TransactionResponse(BaseModel):
    # ... existing fields ...
    tax_exempt: bool
    is_transfer: bool
```

### Transaction Service Changes (`backend/services/transaction_service.py`)

Update `create_transaction` method to store new fields:

```python
transaction = Transaction(
    # ... existing fields ...
    tax_exempt=request.tax_exempt,
    is_transfer=request.is_transfer,
)
```

### Transaction API Changes (`backend/api/v1/transactions.py`)

Update `list_transactions` endpoint response to include new fields in each transaction item:

```python
items.append({
    # ... existing fields ...
    "tax_exempt": t.tax_exempt,
    "is_transfer": t.is_transfer,
})
```

Update `get_transaction` endpoint response to include new fields.

## Frontend Changes

### Type Definition (`frontend/src/types/index.ts`)

Add new fields to `Transaction` interface:

```typescript
export interface Transaction {
  // ... existing fields ...
  tax_exempt: boolean;
  is_transfer: boolean;
}
```

### API Layer (`frontend/src/api/transactions.ts`)

Update `createTransaction` function signature and payload:

```typescript
export async function createTransaction(
  phone: string,
  businessType: string,
  files: File[],
  taxExempt: boolean = false,
  isTransfer: boolean = false
): Promise<CreateTransactionResponse> {
  // ...
  const transactionPayload = {
    business_type: businessType,
    customer_phone: phone,
    tax_exempt: taxExempt,
    is_transfer: isTransfer,
    attachments_meta: files.map((f) => ({
      file_type: 'OTHER',
      file_format: inferFormat(f),
    })),
  };
  // ...
}
```

Update `CreateTransactionResponse` to include new fields:

```typescript
export interface CreateTransactionResponse {
  transaction_id: string;
  status: TransactionStatus;
  tax_exempt: boolean;
  is_transfer: boolean;
  estimated_wait?: number;
  message?: string;
}
```

### Submit Application Form (`frontend/src/pages/staff/SubmitApplication.tsx`)

Add two Switch components for tax_exempt and is_transfer:

```tsx
<Form.Item label="免税投保" name="tax_exempt" valuePropName="checked">
  <Switch />
</Form.Item>

<Form.Item label="转保" name="is_transfer" valuePropName="checked">
  <Switch />
</Form.Item>
```

## File Changes Summary

| File | Change |
|------|--------|
| `backend/models/transaction.py` | Add `tax_exempt` and `is_transfer` columns |
| `backend/schemas/transaction.py` | Add fields to request/response schemas |
| `backend/services/transaction_service.py` | Store new fields when creating transaction |
| `backend/api/v1/transactions.py` | Return new fields in list/detail endpoints |
| `frontend/src/types/index.ts` | Add types for new fields |
| `frontend/src/api/transactions.ts` | Send new fields in createTransaction |
| `frontend/src/pages/staff/SubmitApplication.tsx` | Add form inputs for new fields |

## Default Values

- `tax_exempt`: `false` (默认不禁税)
- `is_transfer`: `false` (默认非转保)

## Backward Compatibility

- New fields have defaults so existing API calls continue to work
- Frontend form provides defaults of `false` when not specified
- API responses include new fields; clients ignoring them remain functional
