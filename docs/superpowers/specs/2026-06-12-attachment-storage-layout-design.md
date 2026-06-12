# Attachment Storage Layout Redesign

**Date:** 2026-06-12
**Scope:** `backend/services/transaction_service.py` (storage key construction only)

## Problem

Current attachment storage key:

```
{customer_id}/{attachment_id}/{attachment_id}_{original_filename}
```

Real example on disk:

```
/data/attachments/default/ATT-20260612091623-74bf274e/ATT-20260612091623-74bf274e_01.jpg
```

Pain points:

- Files are bucketed by `customer_id`, which is currently always `"default"` — so every attachment piles into one directory.
- One folder per attachment is excessive — a 3-file transaction produces 3 sibling folders that all belong to the same transaction.
- Filenames preserve raw client-supplied names, which makes ordering/auditing harder and risks unsafe characters.
- No date partitioning, so the tree grows unbounded in a single namespace.

## Goal

Reorganize on-disk layout so attachments are:

1. Partitioned by **server UTC date** (cheap rotation, easy cleanup / backup windowing).
2. Grouped by **transaction_id** (one folder per business event, easy manual inspection).
3. Renamed to a **deterministic, ordered scheme** that preserves only the original extension.

## New Layout

```
/data/attachments/
  └── 2026-06-12/                          ← server UTC date (YYYY-MM-DD)
      └── TXN-20260612091623-abc12345/     ← transaction_id
          ├── TXN-20260612091623-abc12345_001.jpg
          ├── TXN-20260612091623-abc12345_002.png
          └── TXN-20260612091623-abc12345_003.pdf
```

### Storage key format

```
{YYYY-MM-DD}/{transaction_id}/{transaction_id}_{NNN}{ext}
```

- `YYYY-MM-DD` — server UTC date at transaction creation, via `datetime.utcnow().strftime('%Y-%m-%d')`.
- `transaction_id` — existing `TXN-<timestamp>-<hex8>` value generated earlier in `create_transaction`.
- `NNN` — 3-digit zero-padded sequence starting at `001`, matching the order of `attachments_meta` in the request.
- `ext` — original file extension from `UploadFile.filename`, derived via `pathlib.Path(filename).suffix`. Lowercased for normalization. Empty string if the upload has no extension.

## Implementation Changes

Only `backend/services/transaction_service.py` changes. Diff outline:

```python
# add import
from pathlib import Path

# inside create_transaction(), in the per-file loop:
date_str = datetime.utcnow().strftime('%Y-%m-%d')           # NEW
ext = Path(file_meta['filename']).suffix.lower()            # NEW
filename = f"{transaction_id}_{idx + 1:03d}{ext}"           # CHANGED
storage_key = f"{date_str}/{transaction_id}/{filename}"     # CHANGED
```

Everything else stays the same:

- `attachment_id` is still generated and used as the DB primary key — only the on-disk layout changes.
- `LocalStorageBackend.put` already calls `parent.mkdir(parents=True, exist_ok=True)`, so new date/transaction folders are auto-created.
- `_validate_key` path-traversal check still applies because the key starts with `YYYY-MM-DD/` and contains no `..`.
- `attachment.storage_path` is persisted as the new key, so downloads (`backend/api/v1/downloads.py`) keep working unchanged — they look up `storage_path` from DB and call `storage.get()`.

## Non-Goals

- No migration of pre-existing files on disk. Old files keep their old keys (already recorded in DB rows), new files use the new layout.
- No change to `attachment_id` format or DB schema.
- No change to download URL signing or signed-URL paths.
- No retention / cleanup automation (date partitioning enables it, but implementation is out of scope here).
- `customer_id` is no longer part of the key. It is still stored on the `Attachment` row for queryability.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| File with no extension uploads as `..._001` (no suffix) | Acceptable. `Path("foo").suffix` returns `""`, file is still stored and indexed by DB. |
| Two transactions created in the same microsecond on different UTC days | Each transaction has its own folder under its own date — no collision. |
| Existing tests assert old `storage_path` format | Update test fixtures to match new format. Verify via `pytest backend/`. |
| Downloads of old files | Old `storage_path` values in DB still resolve under `/data/attachments/<old-key>`. Unchanged. |

## Verification

After implementing:

1. `pytest` — existing transaction tests should pass (with updated path assertions if any).
2. Manual smoke: `POST /api/v1/transactions` with 3 files, then `ls /data/attachments/$(date -u +%Y-%m-%d)/TXN-*/` shows `TXN-..._001.jpg`, `_002.jpg`, `_003.jpg`.
3. `GET /api/v1/downloads/...` for one of the new attachments returns the file bytes.
