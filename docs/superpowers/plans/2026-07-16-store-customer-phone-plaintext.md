# Store Customer Phone as Plaintext Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the misleading `customer_phone_encrypted` + `customer_phone_search` dual-column setup on the `transactions` table with a single plaintext `customer_phone` column, and update every backend service, API endpoint, SQL DDL, test, and frontend consumer to use the new field name.

**Architecture:** A schema simplification - the ORM model drops two columns and adds one, the service writes a single field, API endpoints rename response keys, `init_db.sql` mirrors the new schema, tests update ORM construction calls, and the frontend renames the TypeScript field and column `dataIndex` values. No encryption logic exists or is added.

**Tech Stack:** Python 3.14, SQLAlchemy (async), FastAPI, Pydantic, PostgreSQL, pytest (asyncio), TypeScript, React + Ant Design.

## Global Constraints

- The project uses `Base.metadata.create_all` for test/dev DBs (no Alembic). The ORM model is the source of truth for tests; `scripts/init_db.sql` is the source of truth for manual bootstrap and must stay in sync.
- `TransactionCreateRequest.customer_phone` (Pydantic schema field) is **unchanged** - only the ORM column names and API response keys change.
- `customer_id_no_encrypted` is explicitly **out of scope** - do not touch it.
- Tests live under `tests/` (root) configured via `pytest.ini` (`testpaths = tests`, `asyncio_mode = auto`). Run with the backend venv activated: `& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1`.
- Frontend typecheck: `npm run build` (runs `tsc -b && vite build`) from `frontend/`. Lint: `npm run lint`.
- The `maskPhone` helper in the frontend is a **display-only** concern and is unchanged - DB stores plaintext, UI masks it.
- The worker (`worker/`) does not reference `customer_phone` at all - no worker changes.

## Files Touched

| File | Change | Responsibility |
|------|--------|----------------|
| `backend/models/transaction.py` | Replace 2 cols with 1 (Task 1) | ORM schema source of truth |
| `backend/services/transaction_service.py` | Write single `customer_phone` field (Task 1) | Create transaction |
| `backend/api/v1/transactions.py` | Search filter + response key rename + detail adds field (Task 2) | List/detail endpoints |
| `backend/api/v1/tasks.py` | Response key rename (Task 2) | Poll endpoint |
| `backend/services/dashboard_service.py` | Response key rename (Task 2) | Dashboard recent list |
| `scripts/init_db.sql` | Update DDL + index (Task 3) | Fresh DB bootstrap |
| `tests/backend/test_transactions_list.py` | Update ORM construction (Task 4) | Search/pagination tests |
| `frontend/src/types/index.ts` | Rename interface field (Task 5) | TS type source of truth |
| `frontend/src/pages/staff/ApplicationDetail.tsx` | Update field access (Task 5) | Detail page |
| `frontend/src/pages/staff/TrackApplications.tsx` | Update column dataIndex (Task 5) | List page |
| `frontend/src/pages/admin/Dashboard.tsx` | Update column dataIndex (Task 5) | Dashboard page |

---

## Task 1: Update ORM Model and Service Layer

**Files:**
- Modify: `backend/models/transaction.py:29-30`
- Modify: `backend/services/transaction_service.py:77-78`

**Interfaces:**
- Consumes: `TransactionCreateRequest.customer_phone` (Pydantic `Optional[str]`, unchanged)
- Produces: `Transaction.customer_phone` (`Column(String(20))`, nullable, indexed) - all downstream code reads this attribute

- [ ] **Step 1: Update the ORM model**

In `backend/models/transaction.py`, replace lines 29-30:

Remove:
```python
    customer_phone_encrypted = Column(String(256), nullable=True)
    customer_phone_search = Column(String(20), nullable=True, index=True)
```

Add in their place:
```python
    customer_phone = Column(String(20), nullable=True, index=True)
```

The surrounding context should read:
```python
    status = Column(String(20), default=TransactionStatus.PENDING.value)
    customer_phone = Column(String(20), nullable=True, index=True)
    customer_id_no_encrypted = Column(String(256), nullable=True)
```

- [ ] **Step 2: Update the service layer**

In `backend/services/transaction_service.py`, the `create_transaction` method constructs a `Transaction` (lines 72-84). Replace the two phone assignments:

Remove:
```python
            customer_phone_encrypted=request.customer_phone,
            customer_phone_search=request.customer_phone,
```

Add in their place (single line):
```python
            customer_phone=request.customer_phone,
```

The surrounding context should read:
```python
        transaction = Transaction(
            transaction_id=transaction_id,
            external_id=request.external_id,
            business_type=request.business_type,
            status=TransactionStatus.PENDING.value,
            customer_phone=request.customer_phone,
            customer_id_no_encrypted=request.customer_id_no,
            submitted_by=customer_id,
            tax_exempt=request.tax_exempt,
            is_transfer=request.is_transfer,
            holder_phone=request.holder_phone,
        )
```

- [ ] **Step 3: Verify no syntax errors**

Run:
```powershell
& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1
python -c "from backend.models.transaction import Transaction; print(hasattr(Transaction, 'customer_phone')); print(not hasattr(Transaction, 'customer_phone_encrypted'))"
```
Expected output:
```
True
True
```

- [ ] **Step 4: Commit**

```bash
git add backend/models/transaction.py backend/services/transaction_service.py
git commit -m "refactor(backend): replace phone_encrypted/search with single customer_phone column"
```

---

## Task 2: Update API Endpoints and Dashboard Service

**Files:**
- Modify: `backend/api/v1/transactions.py:92, 119, 144-151`
- Modify: `backend/api/v1/tasks.py:61`
- Modify: `backend/services/dashboard_service.py:161`

**Interfaces:**
- Consumes: `Transaction.customer_phone` (from Task 1)
- Produces: API responses now have key `"customer_phone"` instead of `"customer_phone_encrypted"`; `get_transaction` now includes the phone field

- [ ] **Step 1: Update search filter in `list_transactions`**

In `backend/api/v1/transactions.py` line 92, replace:

```python
            Transaction.customer_phone_search.contains(search),
```

with:

```python
            Transaction.customer_phone.contains(search),
```

- [ ] **Step 2: Update list response item key**

In `backend/api/v1/transactions.py` line 119, replace:

```python
            "customer_phone_encrypted": t.customer_phone_encrypted,
```

with:

```python
            "customer_phone": t.customer_phone,
```

- [ ] **Step 3: Add phone field to `get_transaction` response**

In `backend/api/v1/transactions.py`, the `get_transaction` return dict (lines 144-151). Replace:

```python
    return {
        "transaction_id": txn.transaction_id,
        "status": txn.status,
        "business_type": txn.business_type,
        "tax_exempt": txn.tax_exempt,
        "is_transfer": txn.is_transfer,
        "holder_phone": txn.holder_phone,
    }
```

with:

```python
    return {
        "transaction_id": txn.transaction_id,
        "status": txn.status,
        "business_type": txn.business_type,
        "customer_phone": txn.customer_phone,
        "tax_exempt": txn.tax_exempt,
        "is_transfer": txn.is_transfer,
        "holder_phone": txn.holder_phone,
    }
```

- [ ] **Step 4: Update `tasks.py` poll response key**

In `backend/api/v1/tasks.py` line 61, replace:

```python
            "customer_phone_encrypted": txn.customer_phone_encrypted,
```

with:

```python
            "customer_phone": txn.customer_phone,
```

- [ ] **Step 5: Update `dashboard_service.py` response key**

In `backend/services/dashboard_service.py` line 161, replace:

```python
                    "customer_phone_encrypted": t.customer_phone_encrypted,
```

with:

```python
                    "customer_phone": t.customer_phone,
```

- [ ] **Step 6: Verify imports load cleanly**

Run:
```powershell
& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1
python -c "from backend.api.v1 import transactions, tasks; from backend.services.dashboard_service import DashboardService; print('imports OK')"
```
Expected output:
```
imports OK
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/v1/transactions.py backend/api/v1/tasks.py backend/services/dashboard_service.py
git commit -m "refactor(api): rename customer_phone_encrypted to customer_phone in responses"
```

---

## Task 3: Update `scripts/init_db.sql`

**Files:**
- Modify: `scripts/init_db.sql:54-55, 104`

**Interfaces:**
- Consumes: none (DDL is standalone)
- Produces: Fresh DB bootstrap matches the ORM model from Task 1

- [ ] **Step 1: Update the CREATE TABLE columns**

In `scripts/init_db.sql` lines 54-55, replace:

```sql
    customer_phone_encrypted VARCHAR(256),
    customer_phone_search VARCHAR(20),
```

with:

```sql
    customer_phone VARCHAR(20),
```

The surrounding context should read:
```sql
    status VARCHAR(20) DEFAULT 'PENDING',
    customer_phone VARCHAR(20),
    customer_id_no_encrypted VARCHAR(256),
```

- [ ] **Step 2: Update the index**

In `scripts/init_db.sql` line 104, replace:

```sql
CREATE INDEX idx_transactions_phone_search ON transactions(customer_phone_search);
```

with:

```sql
CREATE INDEX idx_transactions_customer_phone ON transactions(customer_phone);
```

- [ ] **Step 3: Commit**

```bash
git add scripts/init_db.sql
git commit -m "chore(db): sync init_db.sql with plaintext customer_phone column"
```

---

## Task 4: Update Backend Tests

**Files:**
- Modify: `tests/backend/test_transactions_list.py:28-29, 70-71, 78-79, 121, 128`
- Inspect: `backend/tests/test_dispatcher_no_worker.py` (verify no old column references)

**Interfaces:**
- Consumes: `Transaction.customer_phone` (from Task 1)
- Produces: Tests that construct `Transaction(...)` ORM objects with the new field name

- [ ] **Step 1: Update `test_list_transactions_pagination`**

In `tests/backend/test_transactions_list.py` lines 28-29, replace:

```python
            customer_phone_encrypted="enc",
            customer_phone_search="13800000000",
```

with:

```python
            customer_phone="13800000000",
```

- [ ] **Step 2: Update `test_list_transactions_phone_search`**

In `tests/backend/test_transactions_list.py` lines 70-71, replace:

```python
            customer_phone_encrypted="enc-a",
            customer_phone_search="13812345678",
```

with:

```python
            customer_phone="13812345678",
```

And lines 78-79, replace:

```python
            customer_phone_encrypted="enc-b",
            customer_phone_search="13987654321",
```

with:

```python
            customer_phone="13987654321",
```

- [ ] **Step 3: Update `test_list_transactions_id_search`**

In `tests/backend/test_transactions_list.py` line 121, replace:

```python
            customer_phone_search="13800000001",
```

with:

```python
            customer_phone="13800000001",
```

And line 128, replace:

```python
            customer_phone_search="13800000002",
```

with:

```python
            customer_phone="13800000002",
```

- [ ] **Step 4: Verify `backend/tests/test_dispatcher_no_worker.py` needs no changes**

Run:
```powershell
& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1
Select-String -Path "D:\workspace\3IS-auto-app\backend\tests\test_dispatcher_no_worker.py" -Pattern "customer_phone_encrypted|customer_phone_search"
```
Expected: no matches (the test uses `TransactionCreateRequest(customer_phone=...)` which is a schema field, not an ORM column). If any matches appear, replace `customer_phone_encrypted` / `customer_phone_search` with `customer_phone` in the matched lines.

- [ ] **Step 5: Run the affected tests**

Run:
```powershell
& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "worker;."
pytest tests/backend/test_transactions_list.py -v
```
Expected: all 4 tests PASS (`test_list_transactions_pagination`, `test_list_transactions_phone_search`, `test_list_transactions_id_search`, `test_list_transactions_status_filter`).

- [ ] **Step 6: Run the full backend test suite**

Run:
```powershell
$env:PYTHONPATH = "worker;."
pytest tests/ -q
```
Expected: all tests PASS (no failures).

- [ ] **Step 7: Commit**

```bash
git add tests/backend/test_transactions_list.py
git commit -m "test(backend): update transaction list tests for customer_phone field"
```

---

## Task 5: Update Frontend

**Files:**
- Modify: `frontend/src/types/index.ts:24`
- Modify: `frontend/src/pages/staff/ApplicationDetail.tsx:88`
- Modify: `frontend/src/pages/staff/TrackApplications.tsx:55`
- Modify: `frontend/src/pages/admin/Dashboard.tsx:29`

**Interfaces:**
- Consumes: API responses with key `customer_phone` (from Task 2)
- Produces: Frontend that correctly reads and displays the new field name

- [ ] **Step 1: Update TypeScript type definition**

In `frontend/src/types/index.ts` line 24, replace:

```typescript
  customer_phone_encrypted?: string;
```

with:

```typescript
  customer_phone?: string;
```

- [ ] **Step 2: Update ApplicationDetail page**

In `frontend/src/pages/staff/ApplicationDetail.tsx` line 88, replace:

```tsx
            {maskPhone(txn.customer_phone_encrypted)}
```

with:

```tsx
            {maskPhone(txn.customer_phone)}
```

- [ ] **Step 3: Update TrackApplications column**

In `frontend/src/pages/staff/TrackApplications.tsx` line 55, replace:

```tsx
      dataIndex: 'customer_phone_encrypted',
```

with:

```tsx
      dataIndex: 'customer_phone',
```

- [ ] **Step 4: Update Dashboard column**

In `frontend/src/pages/admin/Dashboard.tsx` line 29, replace:

```tsx
    { title: '手机号', dataIndex: 'customer_phone_encrypted', width: 130, render: (p: string) => maskPhone(p) },
```

with:

```tsx
    { title: '手机号', dataIndex: 'customer_phone', width: 130, render: (p: string) => maskPhone(p) },
```

- [ ] **Step 5: Run frontend typecheck**

Run:
```powershell
npm run build
```
(workdir: `frontend`)
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Run frontend lint**

Run:
```powershell
npm run lint
```
(workdir: `frontend`)
Expected: no errors related to the changed fields.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/pages/staff/ApplicationDetail.tsx frontend/src/pages/staff/TrackApplications.tsx frontend/src/pages/admin/Dashboard.tsx
git commit -m "refactor(frontend): rename customer_phone_encrypted to customer_phone"
```

---

## Task 6: Final Verification

**Files:**
- None modified - verification only

- [ ] **Step 1: Run the complete backend test suite**

Run:
```powershell
& D:\workspace\3IS-auto-app\backend\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "worker;."
pytest tests/ -q
```
Expected: all tests PASS.

- [ ] **Step 2: Run frontend build**

Run:
```powershell
npm run build
```
(workdir: `frontend`)
Expected: build succeeds.

- [ ] **Step 3: Grep for any remaining old field names in source code**

Run a search for `customer_phone_encrypted` and `customer_phone_search` across:
- `backend/` (Python files)
- `frontend/src/` (TS/TSX files)
- `scripts/init_db.sql`
- `tests/` (Python files)

Expected: **zero matches** in active source code. The only acceptable remaining matches are in `openspec/` (historical spec/design docs) and `docs/superpowers/plans/` (historical plan docs).

- [ ] **Step 4: Commit if any stragglers were found and fixed**

If Step 3 found and fixed any remaining references, commit them:
```bash
git add -A
git commit -m "fix: clean up remaining customer_phone_encrypted references"
```

If no stragglers, skip this step.

---

## Migration Note (for operations, not a code task)

For existing databases with data, apply this SQL **before** deploying the new code:

```sql
ALTER TABLE transactions ADD COLUMN customer_phone VARCHAR(20);
UPDATE transactions
  SET customer_phone = customer_phone_encrypted
  WHERE customer_phone_encrypted IS NOT NULL;
CREATE INDEX idx_transactions_customer_phone ON transactions (customer_phone);
ALTER TABLE transactions DROP COLUMN customer_phone_search;
ALTER TABLE transactions DROP COLUMN customer_phone_encrypted;
```

For fresh installs / test DBs, `Base.metadata.create_all` (tests) or `scripts/init_db.sql` (manual bootstrap) produces the new schema directly.
