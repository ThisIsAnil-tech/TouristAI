import apiClient from './client';
import { CommAttemptResponse, ContactRequest, ContactResponse } from '../types';

export const communicationApi = {
  getAttemptsForSos: async (sosEventId: string): Promise<CommAttemptResponse[]> => {
    const response = await apiClient.get<CommAttemptResponse[]>(`/api/v1/communication/sos/${sosEventId}`);
    return response.data;
  },

  sendEmergencyAlert: async (sosEventId: string): Promise<{ notified: number; results: Array<{ contact: string; state: string }> }> => {
    const response = await apiClient.post<{ notified: number; results: Array<{ contact: string; state: string }> }>(
      `/api/v1/communication/sos/${sosEventId}/send`
    );
    return response.data;
  },

  retryFailedAttempts: async (sosEventId: string): Promise<{ retrying: number }> => {
    const response = await apiClient.post<{ retrying: number }>(`/api/v1/communication/sos/${sosEventId}/retry`);
    return response.data;
  },

  listContacts: async (): Promise<ContactResponse[]> => {
    const response = await apiClient.get<ContactResponse[]>('/api/v1/contacts/');
    return response.data;
  },

  addContact: async (data: ContactRequest): Promise<ContactResponse> => {
    const response = await apiClient.post<ContactResponse>('/api/v1/contacts/', data);
    return response.data;
  },

  removeContact: async (contactId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/contacts/${contactId}`);
  },
};
