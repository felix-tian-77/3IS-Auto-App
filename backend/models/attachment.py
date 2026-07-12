from sqlalchemy import Column, String, Enum, DateTime, Boolean, BigInteger, ForeignKey
from backend.db.database import Base
import enum

class FileType(str, enum.Enum):
    ID_CARD_FRONT = "ID_CARD_FRONT"
    ID_CARD_BACK = "ID_CARD_BACK"
    DRIVING_LICENSE_FRONT = "DRIVING_LICENSE_FRONT"
    DRIVING_LICENSE_BACK = "DRIVING_LICENSE_BACK"
    ELECTRONIC_INVOICE = "ELECTRONIC_INVOICE"
    CERTIFICATE = "CERTIFICATE"
    TAX_EXEMPT_CERT = "TAX_EXEMPT_CERT"
    INSURER_ID_CARD_FRONT = "INSURER_ID_CARD_FRONT"
    INSURER_ID_CARD_BACK = "INSURER_ID_CARD_BACK"
    OTHER = "OTHER"

class FileFormat(str, enum.Enum):
    JPG = "JPG"
    PNG = "PNG"
    PDF = "PDF"

class StorageBackendType(str, enum.Enum):
    LOCAL = "local"
    OSS = "oss"
    MINIO = "minio"

class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id = Column(String(32), primary_key=True)
    transaction_id = Column(String(32), ForeignKey("transactions.transaction_id"))
    customer_id = Column(String(64), nullable=True)
    file_type = Column(String(20), nullable=False)
    description = Column(String(128), nullable=True)
    file_format = Column(String(10), nullable=False)
    file_size = Column(BigInteger, default=0)
    storage_backend = Column(String(16), default=StorageBackendType.LOCAL.value)
    storage_path = Column(String(512), nullable=True)
    local_path = Column(String(512), nullable=True)
    is_orphan = Column(Boolean, default=False)
    md5 = Column(String(32), nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)