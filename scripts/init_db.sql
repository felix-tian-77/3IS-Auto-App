-- Create database
CREATE DATABASE 3is_auto;

-- Create tables (matches SQLAlchemy models)
CREATE TABLE workers (
    worker_id VARCHAR(32) PRIMARY KEY,
    fingerprint VARCHAR(64) UNIQUE,
    hostname VARCHAR(128),
    ip_address VARCHAR(45),
    version VARCHAR(32),
    tags TEXT,
    cpu_usage FLOAT DEFAULT 0.0,
    memory_usage FLOAT DEFAULT 0.0,
    bound_device_id VARCHAR(32),
    port INTEGER DEFAULT 8765,
    token VARCHAR(64),
    status VARCHAR(20) DEFAULT 'OFFLINE',
    last_heartbeat_at TIMESTAMP,
    registered_at TIMESTAMP
);

CREATE TABLE devices (
    device_id VARCHAR(32) PRIMARY KEY,
    sn VARCHAR(64) UNIQUE,
    worker_id VARCHAR(32),
    adb_serial VARCHAR(128),
    sandbox_path VARCHAR(256) DEFAULT '/sdcard/sandbox/{txn_id}/',
    model VARCHAR(128),
    android_version VARCHAR(32),
    battery_level INTEGER DEFAULT 100,
    storage_free_mb INTEGER DEFAULT 0,
    screen_locked BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'OFFLINE',
    adb_status VARCHAR(20) DEFAULT 'DISCONNECTED',
    current_transaction_id VARCHAR(32),
    last_seen_at TIMESTAMP
);

CREATE TABLE flows (
    flow_id VARCHAR(32) PRIMARY KEY,
    flow_name VARCHAR(64),
    business_type VARCHAR(32),
    current_version VARCHAR(32),
    schema JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id VARCHAR(32) PRIMARY KEY,
    external_id VARCHAR(64),
    business_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'PENDING',
    customer_phone_encrypted VARCHAR(256),
    customer_id_no_encrypted VARCHAR(256),
    submitted_by VARCHAR(128),
    flow_id VARCHAR(32),
    worker_id VARCHAR(32),
    device_id VARCHAR(32),
    retry_count INTEGER DEFAULT 0,
    failure_reason TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE TABLE attachments (
    attachment_id VARCHAR(32) PRIMARY KEY,
    transaction_id VARCHAR(32),
    customer_id VARCHAR(64),
    file_type VARCHAR(20),
    description VARCHAR(128),
    file_format VARCHAR(10),
    file_size BIGINT DEFAULT 0,
    storage_backend VARCHAR(10) DEFAULT 'local',
    storage_path VARCHAR(512),
    is_orphan BOOLEAN DEFAULT FALSE,
    md5 VARCHAR(64),
    uploaded_at TIMESTAMP
);

CREATE TABLE download_urls (
    url_id VARCHAR(32) PRIMARY KEY,
    transaction_id VARCHAR(32),
    attachment_id VARCHAR(32),
    signed_url VARCHAR(1024),
    expires_at TIMESTAMP,
    consumed_at TIMESTAMP,
    refresh_count INTEGER DEFAULT 0,
    storage_backend VARCHAR(10) DEFAULT 'local'
);

-- Indexes
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_worker ON transactions(worker_id);
CREATE INDEX idx_attachments_transaction ON attachments(transaction_id);
CREATE INDEX idx_download_urls_transaction ON download_urls(transaction_id);
CREATE INDEX idx_devices_adb_serial ON devices(adb_serial);