export type TransactionStatus =
  | 'PENDING'
  | 'PENDING_TIMEOUT'
  | 'DISPATCHED'
  | 'ADB_CONNECTING'
  | 'DOWNLOADING'
  | 'READY'
  | 'RUNNING'
  | 'SUCCESS'
  | 'FAIL'
  | 'DLQ';

export type BusinessType = 'NEW' | 'RENEWAL';

export type WorkerStatus = 'ONLINE' | 'OFFLINE' | 'BUSY';

export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'BUSY' | 'DISABLED';

export interface Transaction {
  transaction_id: string;
  external_id?: string;
  business_type: BusinessType;
  status: TransactionStatus;
  customer_phone_encrypted?: string;
  customer_id_no_encrypted?: string;
  submitted_by?: string;
  flow_id?: string;
  worker_id?: string;
  device_id?: string;
  retry_count: number;
  failure_reason?: string;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  created_at: string;
  updated_at?: string;
  worker?: Worker;
  device?: Device;
  attachments?: Attachment[];
  timeline?: TimelineEvent[];
}

export interface Attachment {
  attachment_id: string;
  transaction_id: string;
  customer_id?: string;
  file_type: string;
  description?: string;
  file_format: 'JPG' | 'PNG' | 'PDF';
  file_size: number;
  storage_backend: string;
  storage_path?: string;
  is_orphan: boolean;
  md5?: string;
  sha256?: string;
  uploaded_at?: string;
  filename?: string;
  download_url?: string;
}

export interface TimelineEvent {
  time: string;
  status: string;
  label: string;
  description: string;
}

export interface Worker {
  worker_id: string;
  fingerprint?: string;
  hostname?: string;
  ip_address?: string;
  version?: string;
  cpu_usage: number;
  memory_usage: number;
  bound_device_id?: string;
  status: WorkerStatus;
  last_heartbeat_at?: string;
  registered_at?: string;
  device?: Device;
}

export interface Device {
  device_id: string;
  sn?: string;
  worker_id?: string;
  adb_serial?: string;
  model?: string;
  android_version?: string;
  battery_level: number;
  storage_free_mb: number;
  screen_locked: boolean;
  status: DeviceStatus;
  current_transaction_id?: string;
  last_seen_at?: string;
}

export interface TransactionListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: TransactionStatus | '';
  business_type?: BusinessType | '';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardStats {
  today_count: number;
  yesterday_count: number;
  success_rate: number;
  yesterday_success_rate: number;
  avg_duration_minutes: number;
  yesterday_avg_duration_minutes: number;
  device_load: number;
  online_devices: number;
  busy_devices: number;
  hourly_trend: { hour: number; count: number }[];
  // status_distribution[i].status is a localized Chinese label
  // (成功/处理中/待处理/失败) — backend authoritative, do not localize again
  status_distribution: { status: string; count: number }[];
  recent_transactions: Transaction[];
}

export interface WorkerListResponse {
  workers: Worker[];
  stats: {
    online: number;
    offline: number;
    processing: number;
    queued: number;
  };
}

export interface CreateTransactionResponse {
  transaction_id: string;
  status: TransactionStatus;
  estimated_wait?: number;
  message?: string;
}
