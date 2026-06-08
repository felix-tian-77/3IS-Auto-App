from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum
from backend.db.database import Base
import enum

class DownloadStorageBackend(str, enum.Enum):
    LOCAL = "local"
    OSS = "oss"
    MINIO = "minio"

class DownloadUrl(Base):
    __tablename__ = "download_urls"

    url_id = Column(String(32), primary_key=True)
    transaction_id = Column(String(32), ForeignKey("transactions.transaction_id"))
    attachment_id = Column(String(32), ForeignKey("attachments.attachment_id"))
    signed_url = Column(String(1024), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    refresh_count = Column(Integer, default=0)
    storage_backend = Column(Enum(DownloadStorageBackend), default=DownloadStorageBackend.LOCAL)