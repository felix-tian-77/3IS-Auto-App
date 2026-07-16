import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Descriptions,
  Image,
  Timeline,
  Button,
  Spin,
  Result,
  Card,
  Modal,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import StatusBadge from '@/components/StatusBadge';
import { getTransaction } from '@/api/transactions';
import { formatDateTime, maskPhone, BUSINESS_TYPE_MAP, formatFileSize } from '@/utils/format';
import type { Transaction, Attachment } from '@/types';

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [txn, setTxn] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [previewImage, setPreviewImage] = useState<string>('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getTransaction(id)
      .then(setTxn)
      .catch((err) => {
        if (err?.response?.status === 404) setNotFound(true);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (notFound || !txn) {
    return (
      <Result
        status="404"
        title="申请不存在"
        extra={
          <Button type="primary" onClick={() => navigate('/staff/track')}>
            返回列表
          </Button>
        }
      />
    );
  }

  const isImage = (att: Attachment) =>
    att.file_format === 'JPG' || att.file_format === 'PNG';

  const timelineColor = (status: string) => {
    if (status === 'SUCCESS' || status === '申请已提交') return 'green';
    if (status === 'FAIL' || status === 'DLQ') return 'red';
    return 'blue';
  };

  return (
    <div>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/staff/track')}
        style={{ padding: 0, marginBottom: 16 }}
      >
        返回列表
      </Button>

      <h2 style={{ marginBottom: 16 }}>申请详情</h2>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="申请编号">
            {txn.transaction_id}
          </Descriptions.Item>
          <Descriptions.Item label="手机号码">
            {maskPhone(txn.customer_phone)}
          </Descriptions.Item>
          <Descriptions.Item label="业务类型">
            {BUSINESS_TYPE_MAP[txn.business_type] || txn.business_type}
          </Descriptions.Item>
          <Descriptions.Item label="当前状态">
            <StatusBadge status={txn.status} />
          </Descriptions.Item>
          <Descriptions.Item label="提交时间">
            {formatDateTime(txn.created_at)}
          </Descriptions.Item>
          <Descriptions.Item label="处理设备">
            {txn.worker?.hostname
              ? `${txn.worker.hostname} / ${txn.device?.model || '--'}`
              : '--'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <h3 style={{ marginBottom: 12 }}>上传资料</h3>
      {txn.attachments && txn.attachments.length > 0 ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: 12,
            marginBottom: 20,
          }}
        >
          {txn.attachments.map((att) => (
            <Card
              key={att.attachment_id}
              size="small"
              hoverable
              cover={
                isImage(att) && att.download_url ? (
                  <div
                    style={{
                      height: 120,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#fafafa',
                      cursor: 'pointer',
                    }}
                    onClick={() => setPreviewImage(att.download_url!)}
                  >
                    <Image
                      src={att.download_url}
                      alt={att.filename || att.attachment_id}
                      style={{ maxHeight: 120, maxWidth: '100%' }}
                      preview={false}
                    />
                  </div>
                ) : (
                  <div
                    style={{
                      height: 120,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#fafafa',
                      fontSize: 32,
                    }}
                  >
                    📄
                  </div>
                )
              }
            >
              <Card.Meta
                title={
                  <span
                    style={{
                      fontSize: 12,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'block',
                    }}
                  >
                    {att.filename || att.attachment_id}
                  </span>
                }
                description={
                  <span style={{ fontSize: 12, color: '#999' }}>
                    {formatFileSize(att.file_size)}
                  </span>
                }
              />
            </Card>
          ))}
        </div>
      ) : (
        <div
          style={{
            padding: 32,
            textAlign: 'center',
            color: '#999',
            background: '#fafafa',
            borderRadius: 8,
            marginBottom: 20,
          }}
        >
          暂无附件
        </div>
      )}

      <h3 style={{ marginBottom: 12 }}>处理时间线</h3>
      {txn.timeline && txn.timeline.length > 0 ? (
        <Timeline
          items={txn.timeline.map((event) => ({
            color: timelineColor(event.status),
            children: (
              <div>
                <div style={{ fontSize: 12, color: '#999' }}>{event.time}</div>
                <div style={{ fontWeight: 500 }}>{event.label}</div>
                <div style={{ fontSize: 13, color: '#666' }}>
                  {event.description}
                </div>
              </div>
            ),
          }))}
        />
      ) : (
        <div
          style={{
            padding: 32,
            textAlign: 'center',
            color: '#999',
            background: '#fafafa',
            borderRadius: 8,
          }}
        >
          暂无处理记录
        </div>
      )}

      <Modal
        open={!!previewImage}
        footer={null}
        onCancel={() => setPreviewImage('')}
        width="80%"
      >
        <Image
          src={previewImage}
          alt="preview"
          style={{ width: '100%' }}
          preview={false}
        />
      </Modal>
    </div>
  );
}
