import apiClient from './client';
import { LoginRequest, RegisterRequest, TokenResponse, UserPublicResponse } from '../types';

export const authApi = {
  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', credentials);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<UserPublicResponse> => {
    const response = await apiClient.post<UserPublicResponse>('/api/v1/auth/register', data);
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/api/v1/auth/logout');
  },
};
