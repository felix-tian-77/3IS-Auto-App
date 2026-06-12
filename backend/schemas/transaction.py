from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class BusinessType(str, Enum):
    NEW = "NEW"
    RENEWAL = "RENEWAL"

class AttachmentMeta(BaseModel):
    file_type: str
    description: Optional[str] = None
    file_format: str

class TransactionCreateRequest(BaseModel):
    external_id: Optional[str] = None
    business_type: BusinessType
    customer_phone: Optional[str] = None
    customer_id_no: Optional[str] = None
    attachments_meta: List[AttachmentMeta]

class AttachmentResponse(BaseModel):
    attachment_id: str
    file_type: str
    description: Optional[str] = None
    file_size: int
    md5: str
    sha256: str
    storage_backend: str
    storage_path: str

class TransactionResponse(BaseModel):
    transaction_id: str
    status: str
    submitted_at: datetime
    attachments: List[AttachmentResponse]
    estimated_wait: Optional[int] = None