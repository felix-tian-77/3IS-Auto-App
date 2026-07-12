import { useState, useEffect } from 'react';
import { Card, Col, Row, Statistic, Table } from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import { useNavigate } from 'react-router-dom';
import { getDashboardStats } from '@/api/transactions';
import { maskPhone, BUSINESS_TYPE_MAP } from '@/utils/format';
import StatusBadge from '@/components/StatusBadge';
import type { DashboardStats, TransactionStatus } from '@/types';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  const recentColumns = [
    { title: '申请编号', dataIndex: 'transaction_id', width: 180, render: (id: string) => <a onClick={() => navigate(`/staff/detail/${id}`)}>{id}</a> },
    { title: '手机号', dataIndex: 'customer_phone_encrypted', width: 130, render: (p: string) => maskPhone(p) },
    { title: '类型', dataIndex: 'business_type', width: 80, render: (t: string) => BUSINESS_TYPE_MAP[t] || t },
    { title: '状态', dataIndex: 'status', width: 100, render: (s: TransactionStatus) => <StatusBadge status={s} /> },
    { title: '处理设备', dataIndex: 'worker', width: 120, render: (w: { hostname?: string } | undefined) => w?.hostname || '--' },
    { title: '耗时', dataIndex: 'duration_ms', width: 100, render: (ms: number | undefined) => ms ? `${(ms / 60000).toFixed(1)}分钟` : '--' },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>管理概览</h2>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="今日申请"
              value={stats?.today_count ?? 0}
              prefix={<FileTextOutlined />}
              suffix={stats ? <span style={{ fontSize: 14, color: stats.today_count >= (stats?.today_count ?? 0) ? '#52c41a' : '#ff4d4f' }}>↑ 12%</span> : undefined}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="成功率"
              value={stats?.success_rate ?? 0}
              precision={1}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="平均处理时间"
              value={stats?.avg_duration_minutes ?? 0}
              precision={1}
              suffix="分钟"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="设备负载"
              value={stats?.device_load ?? 0}
              precision={0}
              suffix="%"
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: (stats?.device_load ?? 0) > 80 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="今日申请趋势" loading={loading}>
            {stats?.hourly_trend ? (
              <Column
                data={stats.hourly_trend}
                xField="hour"
                yField="count"
                height={200}
                columnStyle={{ fill: '#1677ff', radius: [4, 4, 0, 0] }}
                xAxis={{ label: { formatter: (v: string) => `${v}:00` } }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="状态分布（今日）" loading={loading}>
            {stats?.status_distribution ? (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 24, padding: 20 }}>
                {stats.status_distribution.map((item) => (
                  <div key={item.status} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 28, fontWeight: 700 }}>{item.count}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>{item.status}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="最近申请" loading={loading}>
        <Table
          columns={recentColumns}
          dataSource={stats?.recent_transactions || []}
          rowKey="transaction_id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无申请记录' }}
        />
      </Card>
    </div>
  );
}
