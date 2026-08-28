import apiClient from './client';
import {
  MeshEdgeCreate,
  MeshNodeCreate,
  MeshNodeResponse,
  MeshRouteResponse,
  MeshStatsResponse,
} from '../types';

export const meshApi = {
  listNodes: async (): Promise<MeshNodeResponse[]> => {
    const response = await apiClient.get<MeshNodeResponse[]>('/api/v1/mesh/nodes');
    return response.data;
  },

  registerNode: async (data: MeshNodeCreate): Promise<MeshNodeResponse> => {
    const response = await apiClient.post<MeshNodeResponse>('/api/v1/mesh/nodes', data);
    return response.data;
  },

  updateHeartbeat: async (
    nodeId: string,
    data: { battery_pct?: number; latitude?: number; longitude?: number }
  ): Promise<{ node_id: string; last_seen_at: string }> => {
    const response = await apiClient.patch<{ node_id: string; last_seen_at: string }>(
      `/api/v1/mesh/nodes/${nodeId}/heartbeat`,
      null,
      { params: data }
    );
    return response.data;
  },

  registerEdge: async (data: MeshEdgeCreate): Promise<{ edge_id: string; source: string; target: string }> => {
    const response = await apiClient.post<{ edge_id: string; source: string; target: string }>(
      '/api/v1/mesh/edges',
      data
    );
    return response.data;
  },

  findRouteToGateway: async (sourceNodeId: string): Promise<MeshRouteResponse> => {
    const response = await apiClient.get<MeshRouteResponse>(`/api/v1/mesh/route/${sourceNodeId}`);
    return response.data;
  },

  getStats: async (): Promise<MeshStatsResponse> => {
    const response = await apiClient.get<MeshStatsResponse>('/api/v1/mesh/stats');
    return response.data;
  },
};
