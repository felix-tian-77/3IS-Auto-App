## ADDED Requirements

### Requirement: Backend converts PNG uploads to JPEG before storage

Backend SHALL, when persisting an uploaded attachment whose filename extension is `.png`, decode the bytes and re-encode them as JPEG before writing to the storage backend. The stored file SHALL have a `.jpg` extension and JPEG byte content.

#### Scenario: PNG image is converted to JPG

- **WHEN** an attachment is uploaded with filename `ID_CARD_BACK.png` and valid PNG bytes
- **THEN** the stored file is named `{transaction_id}/ID_CARD_BACK.jpg`
- **AND** the bytes read back from storage are decodable as JPEG and not as PNG

#### Scenario: RGBA PNG is composited on white background

- **WHEN** an attachment is uploaded as an RGBA PNG with transparent regions
- **THEN** the converted JPEG stores those regions as white pixels
- **AND** the stored image has no alpha channel

#### Scenario: JPG attachment is passed through unchanged

- **WHEN** an attachment is uploaded with a `.jpg` extension and JPEG bytes
- **THEN** the stored file keeps the `.jpg` extension and the bytes are identical to the uploaded bytes

#### Scenario: PDF attachment is passed through unchanged

- **WHEN** an attachment is uploaded with a `.pdf` extension and PDF bytes
- **THEN** the stored file keeps the `.pdf` extension and the bytes are identical to the uploaded bytes

#### Scenario: Attachment with no extension is passed through unchanged

- **WHEN** an attachment is uploaded with a filename that has no extension
- **THEN** the stored file has no extension suffix and the bytes are identical to the uploaded bytes

### Requirement: PNG conversion normalizes file_format metadata

Backend SHALL set the `Attachment.file_format` value to `JPG` for any attachment that was converted from PNG, regardless of the client-declared `file_format` in `attachments_meta`.

#### Scenario: file_format is overwritten to JPG after PNG conversion

- **WHEN** an attachment is uploaded with `attachments_meta.file_format = "PNG"` and a `.png` filename
- **THEN** the persisted `Attachment.file_format` equals `JPG`
- **AND** the persisted `storage_path` ends with `.jpg`

### Requirement: PNG conversion failure aborts the transaction

Backend SHALL treat a failure to decode or re-encode a `.png` attachment as an attachment-save failure and SHALL NOT persist the offending attachment's bytes or create its `Attachment` row. The behavior SHALL be consistent with the existing required-file-missing failure semantics.

#### Scenario: Corrupt PNG bytes cause failure

- **WHEN** an attachment is uploaded with filename `back.png` but its bytes are not a valid PNG image
- **THEN** `create_transaction` raises an error and no `Attachment` row is persisted for that file
- **AND** no file is written to the storage backend for that attachment

### Requirement: Backend depends on Pillow for image transcoding

Backend SHALL declare Pillow as a runtime dependency in `backend/pyproject.toml` to provide PNG-to-JPEG decoding and encoding.

#### Scenario: Pillow is installed in backend runtime

- **WHEN** the backend environment is installed from `backend/pyproject.toml`
- **THEN** the `PIL` package is importable
