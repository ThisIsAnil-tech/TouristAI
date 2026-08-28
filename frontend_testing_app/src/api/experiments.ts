import apiClient from './client';
import { ExperimentListItem, ExperimentRunResponse } from '../types';

export const experimentsApi = {
  listExperiments: async (): Promise<ExperimentListItem[]> => {
    const response = await apiClient.get<ExperimentListItem[]>('/api/v1/experiments/');
    return response.data;
  },

  runExperiment: async (experimentName: string): Promise<ExperimentRunResponse> => {
    const response = await apiClient.post<ExperimentRunResponse>(`/api/v1/experiments/${experimentName}/run`);
    return response.data;
  },
};
