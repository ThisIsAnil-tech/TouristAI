import apiClient from './client';
import { GpsAnalyzeResponse, GpsHistoryResponse, LocationRequest, LocationResponse } from '../types';

export const gpsApi = {
  submitLocation: async (data: LocationRequest): Promise<LocationResponse> => {
    const response = await apiClient.post<LocationResponse>('/api/v1/gps/location', data);
    return response.data;
  },

  getGpsHistory: async (userId: string, limit = 50): Promise<GpsHistoryResponse[]> => {
    const response = await apiClient.get<GpsHistoryResponse[]>(`/api/v1/gps/history/${userId}`, {
      params: { limit },
    });
    return response.data;
  },

  analyzeReading: async (readingId: string): Promise<GpsAnalyzeResponse> => {
    const response = await apiClient.post<GpsAnalyzeResponse>('/api/v1/gps/analyze', null, {
      params: { reading_id: readingId },
    });
    return response.data;
  },
};
