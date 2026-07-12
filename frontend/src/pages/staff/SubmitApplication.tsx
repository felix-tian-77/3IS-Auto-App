import { useState } from 'react';
import { Form, Input, Radio, Button, App, Switch, Row, Col } from 'antd';
import type { UploadFile } from 'antd';
import { AxiosError } from 'axios';
import { SingleFileUpload } from '@/components/FileUpload';
import { createTransaction } from '@/api/transactions';

const FILE_NAMES: Record<string, string> = {
  ID_CARD_FRONT: '身份证正面',
  ID_CARD_BACK: '身份证反面',
  DRIVING_LICENSE_FRONT: '行驶证正面',
  DRIVING_LICENSE_BACK: '行驶证反面',
  ELECTRONIC_INVOICE: '电子发票',
  CERTIFICATE: '合格证',
  TAX_EXEMPT_CERT: '车船税减免税证明',
  INSURER_ID_CARD_FRONT: '投保人身份证正面',
  INSURER_ID_CARD_BACK: '投保人身份证反面',
};

const REQUIRED_FILES: Record<string, string[]> = {
  NEW_VEHICLE: ['ID_CARD_FRONT', 'ID_CARD_BACK', 'ELECTRONIC_INVOICE', 'CERTIFICATE'],
  OLD_VEHICLE: ['ID_CARD_FRONT', 'ID_CARD_BACK', 'DRIVING_LICENSE_FRONT', 'DRIVING_LICENSE_BACK'],
};

const ADDITIONAL_FILES: Record<string, string[]> = {
  tax_exempt: ['TAX_EXEMPT_CERT'],
  is_transfer: ['INSURER_ID_CARD_FRONT', 'INSURER_ID_CARD_BACK'],
};

export default function SubmitApplication() {
  const [form] = Form.useForm();
  const [fileMap, setFileMap] = useState<Record<string, UploadFile | null>>({});
  const [submitting, setSubmitting] = useState(false);
  const { message, notification } = App.useApp();

  const getRequiredFiles = (businessType: string, taxExempt: boolean, isTransfer: boolean) => {
    const base = REQUIRED_FILES[businessType] || [];
    const additional: string[] = [];
    if (taxExempt && ADDITIONAL_FILES.tax_exempt) {
      additional.push(...ADDITIONAL_FILES.tax_exempt);
    }
    if (isTransfer && ADDITIONAL_FILES.is_transfer) {
      additional.push(...ADDITIONAL_FILES.is_transfer);
    }
    return [...base, ...additional];
  };

  const handleFileChange = (fileType: string, file: UploadFile | null) => {
    setFileMap(prev => ({ ...prev, [fileType]: file }));
  };

  const handleSubmit = async () => {
    let validated = false;
    try {
      const values = await form.validateFields();
      validated = true;

      const requiredFiles = getRequiredFiles(
        values.business_type,
        values.tax_exempt,
        values.is_transfer
      );

      const missingFiles = requiredFiles.filter(f => !fileMap[f]);
      if (missingFiles.length > 0) {
        message.error(`请上传所有必填文件：${missingFiles.map(f => FILE_NAMES[f] || f).join('、')}`);
        return;
      }

      setSubmitting(true);
      const files: File[] = [];
      const fileTypes: string[] = [];
      for (const f of requiredFiles) {
        const uploadedFile = fileMap[f];
        if (uploadedFile?.originFileObj) {
          files.push(uploadedFile.originFileObj as File);
          fileTypes.push(f);
        }
      }

      const result = await createTransaction(
        values.phone,
        values.business_type,
        files,
        fileTypes,
        values.tax_exempt,
        values.is_transfer,
        values.is_transfer ? values.holder_phone : undefined
      );
      notification.success({
        title: '提交成功',
        description: `申请编号：${result.transaction_id}${result.estimated_wait ? `，预计等待 ${result.estimated_wait} 秒` : ''}`,
        duration: 6,
      });
      form.resetFields();
      setFileMap({});
    } catch (err) {
      if (!validated) {
        return;
      }
      let description = '请稍后重试';
      if (err instanceof AxiosError) {
        description =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          description;
      } else if (err instanceof Error) {
        description = err.message;
      }
      notification.error({ title: '提交失败', description, duration: 6 });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setFileMap({});
  };

  const businessType = Form.useWatch('business_type', form);
  const taxExempt = Form.useWatch('tax_exempt', form);
  const isTransfer = Form.useWatch('is_transfer', form);
  const requiredFiles = getRequiredFiles(businessType || 'NEW_VEHICLE', taxExempt || false, isTransfer || false);

  return (
    <div style={{ maxWidth: 800 }}>
      <h2 style={{ marginBottom: 24 }}>提交申请</h2>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ business_type: 'NEW_VEHICLE', tax_exempt: false, is_transfer: false }}
      >
        <Form.Item label="投保类型" name="business_type" rules={[{ required: true }]}>
          <Radio.Group options={[
            { label: '新车投保', value: 'NEW_VEHICLE' },
            { label: '旧车投保', value: 'OLD_VEHICLE' },
          ]} />
        </Form.Item>

        <Form.Item
          label="手机号码"
          name="phone"
          rules={[
            { required: true, message: '请输入手机号码' },
            { pattern: /^1\d{10}$/, message: '请输入正确的手机号码' },
          ]}
        >
          <Input placeholder="请输入客户手机号码" maxLength={11} />
        </Form.Item>

        <div style={{ display: 'flex', gap: 128 }}>
          <Form.Item label="免税投保" name="tax_exempt" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item label="转保" name="is_transfer" valuePropName="checked">
            <Switch />
          </Form.Item>
        </div>

        {isTransfer && (
          <Form.Item
            label="投保人手机号"
            name="holder_phone"
            rules={[
              { required: true, message: '请输入投保人手机号码' },
              { pattern: /^1\d{10}$/, message: '请输入正确的手机号码' },
            ]}
          >
            <Input placeholder="请输入投保人手机号码" maxLength={11} />
          </Form.Item>
        )}

        <Form.Item label="上传资料">
          <Row gutter={[16, 16]}>
            {requiredFiles.map(fileType => (
              <Col span={6} key={fileType}>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>{FILE_NAMES[fileType] || fileType}</div>
                <SingleFileUpload
                  file={fileMap[fileType] || null}
                  onChange={(file) => handleFileChange(fileType, file)}
                />
              </Col>
            ))}
          </Row>
        </Form.Item>

        <Form.Item style={{ textAlign: 'right' }}>
          <Button onClick={handleReset} style={{ marginRight: 8 }}>
            重置
          </Button>
          <Button
            type="primary"
            onClick={handleSubmit}
            loading={submitting}
          >
            提交申请
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}
