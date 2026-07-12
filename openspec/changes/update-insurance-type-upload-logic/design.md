# Design: Update Insurance Type Upload Logic

## Overview

This document describes the technical design for updating the insurance type terminology, file type enums, dynamic form validation, and storage path structure.

## 1. Enum Changes

### BusinessType Enum (`backend/models/transaction.py`, `backend/schemas/transaction.py`)

**Before:**
```python
class BusinessType(str, Enum):
    NEW = "NEW"        # 新保
    RENEWAL = "RENEWAL"  # 续保
```

**After:**
```python
class BusinessType(str, Enum):
    NEW_VEHICLE = "NEW_VEHICLE"    # 新车投保
    OLD_VEHICLE = "OLD_VEHICLE"    # 旧车投保
```

### FileType Enum (`backend/models/attachment.py`)

**Before:**
```python
class FileType(str, enum.Enum):
    ID_CARD = "ID_CARD"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    CERTIFICATE = "CERTIFICATE"
    INVOICE = "INVOICE"
    OTHER = "OTHER"
```

**After:**
```python
class FileType(str, enum.Enum):
    ID_CARD_FRONT = "ID_CARD_FRONT"                        # 身份证正面
    ID_CARD_BACK = "ID_CARD_BACK"                          # 身份证反面
    DRIVING_LICENSE_FRONT = "DRIVING_LICENSE_FRONT"        # 行驶证正面
    DRIVING_LICENSE_BACK = "DRIVING_LICENSE_BACK"          # 行驶证反面
    ELECTRONIC_INVOICE = "ELECTRONIC_INVOICE"              # 电子发票
    CERTIFICATE = "CERTIFICATE"                            # 合格证
    TAX_EXEMPT_CERT = "TAX_EXEMPT_CERT"                    # 车船税减免税证明
    INSURER_ID_CARD_FRONT = "INSURER_ID_CARD_FRONT"        # 投保人身份证正面
    INSURER_ID_CARD_BACK = "INSURER_ID_CARD_BACK"          # 投保人身份证反面
    OTHER = "OTHER"
```

## 2. Schema Changes

### TransactionCreateRequest (`backend/schemas/transaction.py`)

Add `holder_phone` field for transfer insurance:

```python
class TransactionCreateRequest(BaseModel):
    external_id: Optional[str] = None
    business_type: BusinessType
    customer_phone: Optional[str] = None
    customer_id_no: Optional[str] = None
    tax_exempt: bool = False
    is_transfer: bool = False
    holder_phone: Optional[str] = None  # 新增：投保人手机号(转保场景)
    attachments_meta: List[AttachmentMeta]
```

## 3. Transaction Model (`backend/models/transaction.py`)

Add `holder_phone` field:

```python
class Transaction(Base):
    # ... existing fields ...
    holder_phone = Column(String(20), nullable=True)  # 投保人手机号(转保场景)
```

## 4. Storage Path Structure

**Before:**
```
{date}/{transaction_id}/{filename}
```

**After:**
```
{transaction_id}/{file_type}{ext}
```

**Example:**
```
TXN-20260712-xxx/ID_CARD_FRONT.jpg
TXN-20260712-yyy/DRIVING_LICENSE_FRONT.jpg
```

## 5. Required Files Validation

### Backend Validation Rules (`backend/services/transaction_service.py`)

```python
REQUIRED_FILES = {
    BusinessType.NEW_VEHICLE: [
        FileType.ID_CARD_FRONT,
        FileType.ID_CARD_BACK,
        FileType.ELECTRONIC_INVOICE,
        FileType.CERTIFICATE,
    ],
    BusinessType.OLD_VEHICLE: [
        FileType.ID_CARD_FRONT,
        FileType.ID_CARD_BACK,
        FileType.DRIVING_LICENSE_FRONT,
        FileType.DRIVING_LICENSE_BACK,
    ],
}

ADDITIONAL_FILES = {
    "tax_exempt": [FileType.TAX_EXEMPT_CERT],
    "is_transfer": [FileType.INSURER_ID_CARD_FRONT, FileType.INSURER_ID_CARD_BACK],
}
```

## 6. Frontend Changes

### SubmitApplication.tsx

Change from Segmented (multi-select style) to RadioGroup (single-select):

```tsx
<Form.Item label="投保类型" name="business_type" rules={[{ required: true }]}>
  <RadioGroup options={[
    { label: '新车投保', value: 'NEW_VEHICLE' },
    { label: '旧车投保', value: 'OLD_VEHICLE' },
  ]} />
</Form.Item>
```

Dynamic file list display based on business_type:

```tsx
const getRequiredFiles = (businessType: string, taxExempt: boolean, isTransfer: boolean) => {
  const baseFiles = businessType === 'NEW_VEHICLE'
    ? ['身份证正面', '身份证反面', '电子发票', '合格证']
    : ['身份证正面', '身份证反面', '行驶证正面', '行驶证反面'];

  const additional = [];
  if (taxExempt) additional.push('车船税减免税证明');
  if (isTransfer) additional.push('投保人身份证正面', '投保人身份证反面');

  return [...baseFiles, ...additional];
};
```

### FileUpload Component (`frontend/src/components/FileUpload.tsx`)

Add `requiredFiles` prop and validation:

```tsx
interface FileUploadProps {
  fileList: UploadFile[];
  onChange: (files: UploadFile[]) => void;
  requiredFiles?: string[];  // 新增：必填文件清单
}
```

### Type Definition (`frontend/src/types/index.ts`)

Update BusinessType and add holder_phone:

```typescript
export type BusinessType = 'NEW_VEHICLE' | 'OLD_VEHICLE';

export interface Transaction {
  // ... existing fields ...
  holder_phone?: string;
}

export interface CreateTransactionRequest {
  business_type: BusinessType;
  customer_phone: string;
  tax_exempt: boolean;
  is_transfer: boolean;
  holder_phone?: string;  // 转保场景
  attachments_meta: AttachmentMeta[];
}
```

## 7. File Changes Summary

| File | Change |
|------|--------|
| `backend/models/transaction.py` | BusinessType枚举值修改，新增holder_phone字段 |
| `backend/models/attachment.py` | FileType枚举新增多种文件类型 |
| `backend/schemas/transaction.py` | 新增holder_phone到请求Schema |
| `backend/services/transaction_service.py` | 修改存储路径规则，添加必填文件校验 |
| `backend/api/v1/transactions.py` | 更新list_transactions返回holder_phone |
| `frontend/src/types/index.ts` | 更新BusinessType，添加holder_phone |
| `frontend/src/api/transactions.ts` | 更新createTransaction支持新参数 |
| `frontend/src/pages/staff/SubmitApplication.tsx` | 改为Radio单选，动态显示必填文件 |
| `frontend/src/components/FileUpload.tsx` | 添加requiredFiles prop和校验提示 |

## 8. Migration Notes

- This change replaces `NEW`/`RENEWAL` with `NEW_VEHICLE`/`OLD_VEHICLE`
- This change replaces `ID_CARD`/`DRIVING_LICENSE`/`INVOICE` with more specific types
- No backward compatibility is required - old enum values are not supported
