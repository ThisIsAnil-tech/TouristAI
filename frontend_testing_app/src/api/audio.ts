import apiClient from './client';
import { AudioDetectionRequest, AudioDetectionResponse } from '../types';

export const audioApi = {
  submitDetectionResult: async (data: AudioDetectionRequest): Promise<AudioDetectionResponse> => {
    const response = await apiClient.post<AudioDetectionResponse>('/api/v1/detection/audio', data);
    return response.data;
  },

  inferAudioFile: async (file: File, riskScore = 5.0): Promise<AudioDetectionResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<AudioDetectionResponse>('/api/v1/detection/audio/infer', formData, {
      params: { risk_score: riskScore },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
