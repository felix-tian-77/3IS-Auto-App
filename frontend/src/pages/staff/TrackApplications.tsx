import { useState, useEffect, useCallback } from 'react';
import { Table, Input, Select, Button, Space } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import StatusBadge from '@/components/StatusBadge';
import { getTransactions } from '@/api/transactions';
import { formatDateTime, maskPhone, BUSINESS_TYPE_MAP } from '@/utils/format';
import type { Transaction, TransactionStatus, BusinessType } from '@/types';

export default function TrackApplications() {
  const navigate = useNavigate();
  const [data, setData] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<TransactionStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<BusinessType | ''>('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      };
      if (searchText) params.search = searchText;
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.business_type = typeFilter;
      const result = await getTransactions(params as never);
      setData(result.items);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchText, statusFilter, typeFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns: ColumnsType<Transaction> = [
    {
      title: '申请编号',
      dataIndex: 'transaction_id',
      width: 180,
      render: (id: string) => (
        <a onClick={() => navigate(`/staff/detail/${id}`)}>{id}</a>
      ),
    },
    {
      title: '手机号码',
      dataIndex: 'customer_phone_encrypted',
      width: 140,
      render: (phone: string) => maskPhone(phone),
    },
    {
      title: '业务类型',
      dataIndex: 'business_type',
      width: 100,
      render: (type: string) => BUSINESS_TYPE_MAP[type] || type,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: TransactionStatus) => <StatusBadge status={status} />,
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      width: 180,
      render: (t: string) => formatDateTime(t),
    },
    {
      title: '操作',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/staff/detail/${record.transaction_id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>申请跟踪</h2>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索手机号或申请编号"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 220 }}
          allowClear
        />
        <Select
          placeholder="全部状态"
          value={statusFilter || undefined}
          onChange={(v) => setStatusFilter(v || '')}
          allowClear
          style={{ width: 120 }}
          options={[
            { value: 'PENDING', label: '待处理' },
            { value: 'DISPATCHED', label: '已派发' },
            { value: 'RUNNING', label: '处理中' },
            { value: 'SUCCESS', label: '已完成' },
            { value: 'FAIL', label: '失败' },
          ]}
        />
        <Select
          placeholder="全部类型"
          value={typeFilter || undefined}
          onChange={(v) => setTypeFilter(v || '')}
          allowClear
          style={{ width: 120 }}
          options={[
            { value: 'NEW', label: '新保' },
            { value: 'RENEWAL', label: '续保' },
          ]}
        />
        <Button type="primary" onClick={() => { setPage(1); fetchData(); }}>
          查询
        </Button>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>
          刷新
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="transaction_id"
        loading={loading}
        locale={{ emptyText: '暂无申请记录' }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
      />
    </div>
  );
}
