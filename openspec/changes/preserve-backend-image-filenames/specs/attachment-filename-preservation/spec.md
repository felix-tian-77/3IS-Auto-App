## ADDED Requirements

### Requirement: Backend exposes the canonical attachment filename

Backend SHALL include a `filename` field in every attachment item returned by the download URL API. The value MUST be the basename of the persisted attachment path, preserving its case and extension, such as `ID_CARD_FRONT.jpg`.

#### Scenario: Download metadata includes the stored basename

- **WHEN** a client requests download URLs for a transaction with stored attachments
- **THEN** each attachment item contains `filename` equal to the basename of that attachment's Backend storage path

#### Scenario: Filename does not expose storage directories

- **WHEN** Backend builds the download URL response
- **THEN** `filename` contains no parent directory or storage prefix

### Requirement: Worker preserves the Backend filename during download

Worker SHALL propagate the Backend `filename` through task dispatch and use it for the downloaded file's local path and download result metadata. When `filename` is present, Worker MUST NOT replace it with `attachment_id` or a generated ordinal name.

#### Scenario: Download uses the canonical filename

- **WHEN** Worker downloads an attachment with `filename` equal to `ID_CARD_FRONT.jpg`
- **THEN** the temporary file is saved as `{transaction_id}/ID_CARD_FRONT.jpg` and the download result carries the same filename

#### Scenario: Extension and case are preserved

- **WHEN** Backend returns a filename with a specific extension and letter case
- **THEN** Worker preserves the exact filename while saving the file

### Requirement: Worker validates filenames before writing

Worker SHALL reject an empty filename, an absolute path, a filename containing a path separator or NUL byte, or the special values `.` and `..` before creating the local file or pushing it to a device.

#### Scenario: Unsafe filename is rejected

- **WHEN** a download item contains a filename with a directory separator, NUL byte, or traversal value
- **THEN** Worker marks the attachment download as failed and does not write outside the transaction directory

#### Scenario: Valid basename is accepted

- **WHEN** a download item contains a non-empty single-file basename
- **THEN** Worker accepts it for local download and device push

### Requirement: Device delivery uses the canonical filename

Worker SHALL push each downloaded attachment to `/sdcard/3is/{transaction_id}/{filename}` and SHALL report that same device path as the attachment's delivered `local_path`.

#### Scenario: Device push uses the Backend filename

- **WHEN** Worker pushes `ID_CARD_FRONT.jpg` for transaction `TXN-001`
- **THEN** the device path is `/sdcard/3is/TXN-001/ID_CARD_FRONT.jpg`

#### Scenario: Delivery report matches the pushed path

- **WHEN** an attachment is reported as delivered
- **THEN** its `local_path` uses the same transaction directory and filename used by the device push

### Requirement: Airtest attachment selection uses canonical filenames

Airtest scripts that select transaction attachments SHALL enter the transaction directory and use the Backend filenames instead of legacy ordinal or attachment-ID filenames.

#### Scenario: Image script selects a canonical attachment

- **WHEN** a vehicle workflow selects the front side of an ID card
- **THEN** the script enters the transaction directory and selects `ID_CARD_FRONT.jpg`

#### Scenario: Legacy ordinal names are absent from active scripts

- **WHEN** the updated vehicle and renewal scripts are inspected
- **THEN** they do not use `01.jpg`, `02.jpg`, or `03.jpg` as attachment names
