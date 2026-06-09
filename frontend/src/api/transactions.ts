import client from './client';
import type {
  CreateTransactionResponse,
  PaginatedResponse,
  Transaction,
  TransactionListParams,
  DashboardStats,
} from '@/types';

export async function createTransaction(
  phone: string,
  businessType: string,
  files: File[]
): Promise<CreateTransactionResponse> {
  const formData = new FormData();
  formData.append('customer_phone', phone);
  formData.append('business_type', businessType);
  files.forEach((file) => {
    formData.append('files', file);
  });

  const { data } = await client.post<CreateTransactionResponse>(
    '/transactions',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function getTransactions(
  params: TransactionListParams
): Promise<PaginatedResponse<Transaction>> {
  const { data } = await client.get<PaginatedResponse<Transaction>>(
    '/transactions',
    { params }
  );
  return data;
}

export async function getTransaction(
  transactionId: string
): Promise<Transaction> {
  const { data } = await client.get<Transaction>(
    `/transactions/${transactionId}`
  );
  return data;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await client.get<DashboardStats>('/statistics/dashboard');
  return data;
}
