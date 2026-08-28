import apiClient from './client';
import { UpdateProfileRequest, UserProfileResponse } from '../types';

export const usersApi = {
  getMyProfile: async (): Promise<UserProfileResponse> => {
    const response = await apiClient.get<UserProfileResponse>('/api/v1/users/me');
    return response.data;
  },

  updateMyProfile: async (data: UpdateProfileRequest): Promise<UserProfileResponse> => {
    const response = await apiClient.patch<UserProfileResponse>('/api/v1/users/me', data);
    return response.data;
  },

  getUserById: async (userId: string): Promise<UserProfileResponse> => {
    const response = await apiClient.get<UserProfileResponse>(`/api/v1/users/${userId}`);
    return response.data;
  },
};
