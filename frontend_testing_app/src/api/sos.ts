import apiClient from './client';
import { ManualSosRequest, SosEvaluateRequest, SosResponse } from '../types';

export const sosApi = {
  triggerManualSos: async (data: ManualSosRequest, idempotencyKey?: string): Promise<SosResponse> => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['X-Idempotency-Key'] = idempotencyKey;
    }
    const response = await apiClient.post<SosResponse>('/api/v1/sos/manual', data, { headers });
    return response.data;
  },

  evaluateSos: async (data: SosEvaluateRequest, idempotencyKey?: string): Promise<SosResponse> => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['X-Idempotency-Key'] = idempotencyKey;
    }
    const response = await apiClient.post<SosResponse>('/api/v1/sos/evaluate', data, { headers });
    return response.data;
  },

  resolveSos: async (sosId: string): Promise<{ status: string; sos_id: string }> => {
    const response = await apiClient.post<{ status: string; sos_id: string }>(`/api/v1/sos/${sosId}/resolve`);
    return response.data;
  },
};
