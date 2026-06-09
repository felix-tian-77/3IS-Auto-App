import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Table, Select, Space } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  HourglassOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getWorkers } from '@/api/workers';
import { formatDateTime } from '@/utils/format';
import type { Worker, WorkerListResponse } from '@/types';

export default function WorkerMonitor() {
  const [data, setData] = useState<WorkerListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    setLoading(true);
    getWorkers()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const workers = data?.workers || [];
  const filtered =
    statusFilter === 'all'
      ? workers
      : workers.filter((w) => w.status === statusFilter);

  const onlineCount = data?.stats?.online ?? 0;
  const offlineCount = data?.stats?.offline ?? 0;

  const columns: ColumnsType<Worker> = [
    {
      title: 'Worker',
      dataIndex: 'worker_id',
      width: 140,
      render: (id: string, record: Worker) => (
        <div>
          <div style={{ fontWeight: 600 }}>{id}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{record.ip_address || '--'}</div>
        </div>
      ),
    },
    {
      title: '绑定设备',
      width: 160,
      render: (_, record: Worker) =>
        record.device
          ? `${record.device.model || '--'} · Android ${record.device.android_version || '--'}`
          : '--',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (status: string) => {
        const isOnline = status === 'ONLINE';
        return (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 12,
              background: isOnline ? '#f6ffed' : '#fff1f0',
              color: isOnline ? '#52c41a' : '#ff4d4f',
            }}
          >
            {isOnline ? '在线' : '离线'}
          </span>
        );
      },
    },
    {
      title: 'CPU',
      dataIndex: 'cpu_usage',
      width: 70,
      render: (v: number, record: Worker) =>
        record.status === 'ONLINE' ? `${v.toFixed(0)}%` : <span style={{ color: '#ccc' }}>--</span>,
    },
    {
      title: '内存',
      dataIndex: 'memory_usage',
      width: 70,
      render: (v: number, record: Worker) =>
        record.status === 'ONLINE' ? `${v.toFixed(0)}%` : <span style={{ color: '#ccc' }}>--</span>,
    },
    {
      title: '设备电量',
      width: 80,
      render: (_, record: Worker) => {
        if (!record.device || record.status !== 'ONLINE')
          return <span style={{ color: '#ccc' }}>--</span>;
        const level = record.device.battery_level;
        return (
          <span style={{ color: level < 30 ? '#fa8c16' : '#52c41a' }}>
            {level}%
          </span>
        );
      },
    },
    {
      title: '存储',
      width: 120,
      render: (_, record: Worker) => {
        if (!record.device || record.status !== 'ONLINE')
          return <span style={{ color: '#ccc' }}>--</span>;
        const free = record.device.storage_free_mb;
        return `${free}MB`;
      },
    },
    {
      title: '最后心跳',
      dataIndex: 'last_heartbeat_at',
      width: 100,
      render: (t: string) => formatDateTime(t),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>设备监控</h2>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="在线设备"
              value={onlineCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="离线设备"
              value={offlineCount}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="处理中任务"
              value={data?.stats?.processing ?? 0}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="排队中任务"
              value={data?.stats?.queued ?? 0}
              prefix={<HourglassOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          style={{ width: 120 }}
          options={[
            { value: 'all', label: '全部' },
            { value: 'ONLINE', label: '在线' },
            { value: 'OFFLINE', label: '离线' },
          ]}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={filtered}
        rowKey="worker_id"
        loading={loading}
        locale={{ emptyText: '暂无设备' }}
        pagination={false}
      />
    </div>
  );
}
