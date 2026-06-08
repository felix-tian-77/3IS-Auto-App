from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Enum
from backend.db.database import Base
import enum

class WorkerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"

class Worker(Base):
    __tablename__ = "workers"

    worker_id = Column(String(32), primary_key=True)
    fingerprint = Column(String(64), unique=True, nullable=True)
    hostname = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    version = Column(String(32), nullable=True)
    tags = Column(String, nullable=True)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    bound_device_id = Column(String(32), ForeignKey("devices.device_id"), nullable=True)
    port = Column(Integer, default=8765)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.OFFLINE)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    registered_at = Column(DateTime(timezone=True), nullable=True)