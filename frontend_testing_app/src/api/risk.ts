import apiClient from './client';
import {
  GeographicZoneResponse,
  IncidentResponse,
  NewsEventResponse,
  RiskScoreResponse,
  WeatherResponse,
  ZoneRequest,
} from '../types';

export const riskApi = {
  getZoneRisk: async (zoneId: string): Promise<RiskScoreResponse> => {
    const response = await apiClient.get<RiskScoreResponse>(`/api/v1/risk/zone/${zoneId}`);
    return response.data;
  },

  calculateZoneRisk: async (zoneId: string): Promise<RiskScoreResponse> => {
    const response = await apiClient.post<RiskScoreResponse>(`/api/v1/risk/calculate/${zoneId}`);
    return response.data;
  },

  listZones: async (): Promise<GeographicZoneResponse[]> => {
    const response = await apiClient.get<GeographicZoneResponse[]>('/api/v1/zones/');
    return response.data;
  },

  createZone: async (data: ZoneRequest): Promise<{ id: string; name: string }> => {
    const response = await apiClient.post<{ id: string; name: string }>('/api/v1/zones/', data);
    return response.data;
  },

  getWeatherForLocation: async (lat: number, lon: number): Promise<WeatherResponse> => {
    const response = await apiClient.get<WeatherResponse>('/api/v1/weather/location', {
      params: { lat, lon },
    });
    return response.data;
  },

  listNews: async (params?: { zone_id?: string; category?: string; severity?: string; hours?: number; limit?: number }): Promise<NewsEventResponse[]> => {
    const response = await apiClient.get<NewsEventResponse[]>('/api/v1/news/', { params });
    return response.data;
  },

  listIncidents: async (): Promise<IncidentResponse[]> => {
    const response = await apiClient.get<IncidentResponse[]>('/api/v1/incidents/');
    return response.data;
  },
};
