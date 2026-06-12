import { useState } from 'react';
import { Form, Input, Segmented, Button, App } from 'antd';
import type { UploadFile } from 'antd';
import { AxiosError } from 'axios';
import FileUpload from '@/components/FileUpload';
import { createTransaction } from '@/api/transactions';

export default function SubmitApplication() {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const { message, notification } = App.useApp();

  const handleSubmit = async () => {
    let validated = false;
    try {
      const values = await form.validateFields();
      validated = true;
      if (fileList.length === 0) {
        message.error('请至少上传一个文件');
        return;
      }
      setSubmitting(true);
      const files = fileList
        .filter((f) => f.originFileObj)
        .map((f) => f.originFileObj as File);
      const businessType = values.business_type === '续保' ? 'RENEWAL' : 'NEW';
      const result = await createTransaction(values.phone, businessType, files);
      notification.success({
        title: '提交成功',
        description: `申请编号：${result.transaction_id}${result.estimated_wait ? `，预计等待 ${result.estimated_wait} 秒` : ''}`,
        duration: 6,
      });
      form.resetFields();
      setFileList([]);
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
    setFileList([]);
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <h2 style={{ marginBottom: 24 }}>提交申请</h2>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ business_type: '新保' }}
      >
        <Form.Item label="业务类型" name="business_type">
          <Segmented options={['新保', '续保']} />
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

        <Form.Item label="上传资料">
          <FileUpload fileList={fileList} onChange={setFileList} />
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
