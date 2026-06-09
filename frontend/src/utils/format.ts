import type { TransactionStatus } from '@/types';

export function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export const STATUS_MAP: Record<
  TransactionStatus,
  { label: string; color: string }
> = {
  PENDING: { label: '待处理', color: 'orange' },
  PENDING_TIMEOUT: { label: '超时', color: 'red' },
  DISPATCHED: { label: '已派发', color: 'blue' },
  ADB_CONNECTING: { label: '连接中', color: 'blue' },
  DOWNLOADING: { label: '下载中', color: 'blue' },
  READY: { label: '就绪', color: 'blue' },
  RUNNING: { label: '处理中', color: 'processing' },
  SUCCESS: { label: '已完成', color: 'success' },
  FAIL: { label: '失败', color: 'error' },
  DLQ: { label: '死信', color: 'error' },
};

export const BUSINESS_TYPE_MAP: Record<string, string> = {
  NEW: '新保',
  RENEWAL: '续保',
};

export function maskPhone(phone?: string): string {
  if (!phone) return '--';
  if (phone.length === 11) {
    return phone.slice(0, 3) + '****' + phone.slice(7);
  }
  return phone;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
