import { Tag } from 'antd';
import type { TransactionStatus } from '@/types';
import { STATUS_MAP } from '@/utils/format';

interface StatusBadgeProps {
  status: TransactionStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_MAP[status] || { label: status, color: 'default' };
  return <Tag color={config.color}>{config.label}</Tag>;
}
