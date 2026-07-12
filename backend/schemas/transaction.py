from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class BusinessType(str, Enum):
    NEW_VEHICLE = "NEW_VEHICLE"
    OLD_VEHICLE = "OLD_VEHICLE"

class AttachmentMeta(BaseModel):
    file_type: str
    description: Optional[str] = None
    file_format: str

class TransactionCreateRequest(BaseModel):
    external_id: Optional[str] = None
    business_type: BusinessType
    customer_phone: Optional[str] = None
    customer_id_no: Optional[str] = None
    tax_exempt: bool = False
    is_transfer: bool = False
    holder_phone: Optional[str] = None
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
    tax_exempt: bool
    is_transfer: bool
    holder_phone: Optional[str] = None
    attachments: List[AttachmentResponse]
    estimated_wait: Optional[int] = None