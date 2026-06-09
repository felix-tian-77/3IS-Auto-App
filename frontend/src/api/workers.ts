import client from './client';
import type { WorkerListResponse } from '@/types';

export async function getWorkers(): Promise<WorkerListResponse> {
  const { data } = await client.get<WorkerListResponse>('/workers');
  return data;
}
