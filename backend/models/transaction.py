from sqlalchemy import Column, String, Enum, DateTime, Integer, Text, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from backend.db.database import Base
import enum

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PENDING_TIMEOUT = "PENDING_TIMEOUT"
    DISPATCHED = "DISPATCHED"
    ADB_CONNECTING = "ADB_CONNECTING"
    DOWNLOADING = "DOWNLOADING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    DLQ = "DLQ"

class BusinessType(str, enum.Enum):
    NEW_VEHICLE = "NEW_VEHICLE"
    OLD_VEHICLE = "OLD_VEHICLE"

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(32), primary_key=True)
    external_id = Column(String(64), nullable=True)
    business_type = Column(String(16), nullable=False)
    status = Column(String(20), default=TransactionStatus.PENDING.value)
    customer_phone = Column(String(20), nullable=True, index=True)
    customer_id_no_encrypted = Column(String(256), nullable=True)
    submitted_by = Column(String, nullable=True)
    flow_id = Column(String, ForeignKey("flows.flow_id"), nullable=True)
    worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)
    retry_count = Column(Integer, default=0)
    failure_reason = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    tax_exempt = Column(Boolean, default=False, nullable=False)
    is_transfer = Column(Boolean, default=False, nullable=False)
    holder_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())