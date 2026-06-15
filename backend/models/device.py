from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum
from backend.db.database import Base
import enum

class DeviceStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"
    DISABLED = "DISABLED"

class ADBStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"

class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String(32), primary_key=True)
    sn = Column(String(64), unique=True, nullable=True)
    worker_id = Column(String(32), ForeignKey("workers.worker_id"), nullable=True)
    adb_serial = Column(String(128), nullable=True)
    sandbox_path = Column(String(256), default="/sdcard/3is/")
    model = Column(String(128), nullable=True)
    android_version = Column(String(32), nullable=True)
    battery_level = Column(Integer, default=100)
    storage_free_mb = Column(Integer, default=0)
    screen_locked = Column(Boolean, default=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.OFFLINE)
    adb_status = Column(Enum(ADBStatus), default=ADBStatus.DISCONNECTED)
    current_transaction_id = Column(String(32), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)