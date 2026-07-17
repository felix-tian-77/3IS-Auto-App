## 1. Backend API Contract

- [x] 1.1 Update `backend/api/v1/downloads.py` to include each attachment's canonical Backend basename as the `filename` field in the download URL response.
- [x] 1.2 Add or update Backend API tests to verify `filename` preserves the stored basename, extension, case, and excludes storage directories.

## 2. Worker Filename Propagation

- [x] 2.1 Update `worker/main.py` to retain `filename` when building download inputs and when constructing delivered attachment paths.
- [x] 2.2 Update `worker/file_downloader.py` and its download result model to validate basename-only filenames, save files as `{transaction_id}/{filename}`, and carry the exact filename through the result.
- [x] 2.3 Add the documented compatibility fallback for legacy responses without `filename` while ensuring responses with `filename` never use `attachment_id` for naming.
- [x] 2.4 Update `worker/device_pusher.py` to push files to `/sdcard/3is/{transaction_id}/{filename}` and preserve existing upload error handling.
- [x] 2.5 Update `worker/main.py` delivery reporting so `local_path` exactly matches the device path built from the canonical filename.

## 3. Worker Scripts and Documentation

- [x] 3.1 Update `worker/scripts/new_vehicle.air/old_vehicle.py` to enter the transaction directory and select Backend filenames for all attachments.
- [x] 3.2 Update `worker/scripts/renew/renew_01.air/renew_01.py` to enter the transaction directory and select Backend filenames for all attachments.
- [x] 3.3 Verify `worker/scripts/old_vehicle.air/old_vehicle.py` follows the same transaction-directory and canonical-filename contract.
- [x] 3.4 Update `docs/user-manu.md` and related attachment storage/download documentation to describe the canonical filename and device path rules.

## 4. Tests and Regression Coverage

- [x] 4.1 Update `worker/tests/test_file_downloader.py` with canonical filename, case/extension preservation, unsafe basename rejection, and legacy fallback coverage.
- [x] 4.2 Update `worker/tests/test_device_pusher.py` to assert device paths use the canonical filename.
- [x] 4.3 Update `tests/backend/test_attachments_delivered.py` and Worker dispatch tests to assert delivered paths use `{transaction_id}/{filename}`.
- [x] 4.4 Resolve stale attachment storage layout assertions in `tests/backend/test_attachment_storage_layout.py` so they match the current Backend `file_type + ext` naming contract.
- [x] 4.5 Run the relevant Backend and Worker test suites and confirm all filename-preservation scenarios pass.
