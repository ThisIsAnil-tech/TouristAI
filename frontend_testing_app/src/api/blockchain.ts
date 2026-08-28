import apiClient from './client';
import {
  BlockchainTxResponse,
  GrantAccessResponse,
  RegisterIdentityResponse,
  VerifyIdentityResponse,
} from '../types';

export const blockchainApi = {
  registerIdentity: async (): Promise<RegisterIdentityResponse> => {
    const response = await apiClient.post<RegisterIdentityResponse>('/api/v1/blockchain/register');
    return response.data;
  },

  grantEmergencyAccess: async (sosEventId: string, responderId: string): Promise<GrantAccessResponse> => {
    const response = await apiClient.post<GrantAccessResponse>(
      `/api/v1/blockchain/grant-access/${sosEventId}/${responderId}`
    );
    return response.data;
  },

  revokeEmergencyAccess: async (grantId: string, reason = 'SOS resolved'): Promise<{ success: boolean; grant_id: string; tx_hash?: string }> => {
    const response = await apiClient.post<{ success: boolean; grant_id: string; tx_hash?: string }>(
      `/api/v1/blockchain/revoke-access/${grantId}`,
      null,
      { params: { reason } }
    );
    return response.data;
  },

  verifyIdentity: async (userId: string): Promise<VerifyIdentityResponse> => {
    const response = await apiClient.get<VerifyIdentityResponse>(`/api/v1/blockchain/verify/${userId}`);
    return response.data;
  },

  listTransactions: async (limit = 50): Promise<BlockchainTxResponse[]> => {
    const response = await apiClient.get<BlockchainTxResponse[]>('/api/v1/blockchain/transactions', {
      params: { limit },
    });
    return response.data;
  },
};
