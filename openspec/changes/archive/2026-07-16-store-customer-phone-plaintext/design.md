# Design: Store Customer Phone as Plaintext

## Overview

This document describes the technical design for replacing the misleading
`customer_phone_encrypted` + `customer_phone_search` dual-column setup with a
single plaintext `customer_phone` column on the `transactions` table.

## Background

Current state of the `transactions` table (relevant columns only):

| Column                       | Type           | Notes                                            |
|------------------------------|----------------|--------------------------------------------------|
| `customer_phone_encrypted`   | `String(256)`  | Stores plaintext despite the name (no encryption)|
| `customer_phone_search`      | `String(20)`   | Duplicate of the above, indexed for `LIKE` search|
| `customer_id_no_encrypted`   | `String(256)`  | Out of scope for this change                     |

The service layer (`transaction_service.py:77-78`) writes the *same* value
into both columns directly from `request.customer_phone` with no encryption.
Likewise, reads surface `customer_phone_encrypted` verbatim to the API and
frontend. No `Fernet`/`AES`/`Cipher` code exists anywhere in the backend.

## Database Changes

### Table: `transactions`

Drop two columns, add one:

```sql
-- Add the new plaintext column first so data can be copied
ALTER TABLE transactions ADD COLUMN customer_phone VARCHAR(20);

-- Backfill from existing plaintext data
UPDATE transactions SET customer_phone = customer_phone_encrypted
  WHERE customer_phone_encrypted IS NOT NULL;

-- Create index to preserve search performance
CREATE INDEX ix_transactions_customer_phone ON transactions (customer_phone);

-- Drop the redundant columns
ALTER TABLE transactions DROP COLUMN customer_phone_search;
ALTER TABLE transactions DROP COLUMN customer_phone_encrypted;
```

### ORM Model (`backend/models/transaction.py`)

Replace the two columns with one:

```python
class Transaction(Base):
    # ... existing fields ...
    customer_phone = Column(String(20), nullable=True, index=True)
    customer_id_no_encrypted = Column(String(256), nullable=True)
    # ... rest ...
```

Column width is reduced from `256` to `20` since the value is now known to be
a plaintext phone number (Chinese mobile numbers are 11 digits). Keeping it at
`20` allows for formatting variants like `+86 138...`.

## Backend Service Changes (`backend/services/transaction_service.py`)

In `create_transaction`, write to the single column:

```python
transaction = Transaction(
    # ... existing fields ...
    customer_phone=request.customer_phone,
    customer_id_no_encrypted=request.customer_id_no,
    # ... rest ...
)
```

The duplicate `customer_phone_search=request.customer_phone` line is removed.

## Backend API Changes

### `backend/api/v1/transactions.py`

1. **Search filter** (`list_transactions`): replace
   `Transaction.customer_phone_search.contains(search)` with
   `Transaction.customer_phone.contains(search)`.

2. **List response items**: rename the key from
   `"customer_phone_encrypted"` to `"customer_phone"` (value `t.customer_phone`).

3. **Detail response** (`get_transaction`): add
   `"customer_phone": txn.customer_phone` to the returned dict.

### `backend/api/v1/tasks.py`

In the `poll` task response, rename the key
`"customer_phone_encrypted"` to `"customer_phone"` (value
`txn.customer_phone`).

### `backend/services/dashboard_service.py`

In the recent transactions list, rename the key
`"customer_phone_encrypted"` to `"customer_phone"` (value
`t.customer_phone`).

### `scripts/init_db.sql`

Update the `CREATE TABLE transactions` DDL to use the new column and index:

```sql
-- In CREATE TABLE transactions:
--   Replace:
--     customer_phone_encrypted VARCHAR(256),
--     customer_phone_search VARCHAR(20),
--   With:
    customer_phone VARCHAR(20),

-- In the Indexes section:
--   Replace:
--     CREATE INDEX idx_transactions_phone_search ON transactions(customer_phone_search);
--   With:
    CREATE INDEX idx_transactions_customer_phone ON transactions(customer_phone);
```

This file is used to bootstrap fresh databases (dev, CI), so it must stay in
sync with the ORM model or `create_all` will diverge from the SQL bootstrap.

### `backend/schemas/transaction.py`

`TransactionCreateRequest` already has `customer_phone: Optional[str]` -
no change needed there. `TransactionResponse` does not currently expose the
phone, so no schema change is required for the create endpoint.

## Frontend Changes

### Type Definition (`frontend/src/types/index.ts`)

Rename the field on the `Transaction` interface:

```typescript
export interface Transaction {
  // ... existing fields ...
  customer_phone?: string;   // was: customer_phone_encrypted?: string
}
```

### API consumers

- `frontend/src/pages/staff/ApplicationDetail.tsx`:
  `txn.customer_phone_encrypted` -> `txn.customer_phone`
- `frontend/src/pages/staff/TrackApplications.tsx`:
  column `dataIndex: 'customer_phone_encrypted'` -> `'customer_phone'`
- `frontend/src/pages/admin/Dashboard.tsx`:
  column `dataIndex: 'customer_phone_encrypted'` -> `'customer_phone'`

The `maskPhone` rendering helper is unchanged - masking is a display concern
and remains at the UI layer.

## Worker Impact

The worker does not reference `customer_phone` (grep confirmed no matches in
`worker/`). No worker changes are required.

## File Changes Summary

| File                                       | Change                                                |
|--------------------------------------------|-------------------------------------------------------|
| `backend/models/transaction.py`            | Replace 2 cols with `customer_phone`                 |
| `backend/services/transaction_service.py`  | Write single `customer_phone` field                  |
| `backend/api/v1/transactions.py`           | Search + response key rename, detail adds field       |
| `backend/api/v1/tasks.py`                  | Response key rename                                   |
| `backend/services/dashboard_service.py`    | Response key rename                                   |
| `scripts/init_db.sql`                      | Update DDL + index for new column                    |
| `tests/backend/test_transactions_list.py`  | Update ORM construction to use `customer_phone`      |
| `backend/tests/test_dispatcher_no_worker.py`| Verify no old column references (schema field unchanged) |
| `frontend/src/types/index.ts`              | Rename interface field                                |
| `frontend/src/pages/staff/ApplicationDetail.tsx` | Update field access                            |
| `frontend/src/pages/staff/TrackApplications.tsx` | Update column dataIndex                         |
| `frontend/src/pages/admin/Dashboard.tsx`   | Update column dataIndex                               |

## Migration Strategy

Since the project uses `Base.metadata.create_all` (no Alembic configured - see
`test_dispatcher_no_worker.py:30`), the migration is applied manually:

1. Add `customer_phone` column (nullable initially)
2. Backfill from `customer_phone_encrypted`
3. Add index
4. Drop old columns
5. Deploy code that references only `customer_phone`

For fresh installs (tests, dev), `create_all` will produce the new schema
directly.

## Backward Compatibility

- The API response key changes from `customer_phone_encrypted` to
  `customer_phone`. Frontend must be deployed together with backend to avoid
  missing-field display issues.
- The DB migration is reversible only if the old columns are not yet dropped;
  once dropped, the data is consolidated into `customer_phone`.

## Risks

- **[Low] Existing data** - backfill SQL handles migration; manual verification
  recommended before dropping columns.
- **[Low] Frontend/backend deployment order** - both must ship together; the
  frontend gracefully handles `undefined` via `maskPhone`'s fallback, but
  data would not display until both sides are updated.
