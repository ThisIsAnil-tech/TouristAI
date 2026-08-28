import apiClient from './client';
import { HealthResponse, ResponderResponse, TelemetryRequest } from '../types';

export const systemApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  listResponders: async (): Promise<ResponderResponse[]> => {
    const response = await apiClient.get<ResponderResponse[]>('/api/v1/responders/');
    return response.data;
  },

  updateResponderAvailability: async (responderId: string, available: boolean): Promise<{ responder_id: string; is_available: boolean }> => {
    const response = await apiClient.patch<{ responder_id: string; is_available: boolean }>(
      `/api/v1/responders/${responderId}/availability`,
      null,
      { params: { available } }
    );
    return response.data;
  },

  submitTelemetry: async (data: TelemetryRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/api/v1/telemetry/mobile', data);
    return response.data;
  },
};
