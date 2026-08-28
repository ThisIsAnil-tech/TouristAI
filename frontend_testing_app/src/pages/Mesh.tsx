import React, { useEffect, useState } from 'react';
import {
  PageHeader,
  Card,
  Input,
  Select,
  Button,
  StatusBadge,
  ErrorMessage,
  DataTable,
  Column,
  LoadingState,
  MetricCard,
  Modal,
} from '../components';
import { meshApi } from '../api/mesh';
import {
  MeshNodeResponse,
  MeshRouteResponse,
  MeshStatsResponse,
} from '../types';
import { getErrorMessage } from '../api/client';
import {
  Share2,
  Route,
  Plus,
  RefreshCw,
  Cpu,
  Radio,
} from 'lucide-react';

export const MeshPage: React.FC = () => {
  const [nodes, setNodes] = useState<MeshNodeResponse[]>([]);
  const [stats, setStats] = useState<MeshStatsResponse | null>(null);
  const [selectedSourceNodeId, setSelectedSourceNodeId] = useState<string>('');
  const [routeResult, setRouteResult] = useState<MeshRouteResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRouting, setIsRouting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Register Node Modal
  const [isNodeModalOpen, setIsNodeModalOpen] = useState<boolean>(false);
  const [deviceId, setDeviceId] = useState<string>('node-001');
  const [nodeType, setNodeType] = useState<any>('TOURIST_DEVICE');
  const [isGateway, setIsGateway] = useState<boolean>(false);
  const [batteryPct, setBatteryPct] = useState<string>('85');
  const [nodeLat, setNodeLat] = useState<string>('10.5276');
  const [nodeLon, setNodeLon] = useState<string>('76.2144');

  // Register Edge Modal
  const [isEdgeModalOpen, setIsEdgeModalOpen] = useState<boolean>(false);
  const [edgeSource, setEdgeSource] = useState<string>('');
  const [edgeTarget, setEdgeTarget] = useState<string>('');
  const [hopCost, setHopCost] = useState<string>('1.0');
  const [signalQuality, setSignalQuality] = useState<string>('0.9');

  const fetchMeshData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [nodesRes, statsRes] = await Promise.allSettled([
        meshApi.listNodes(),
        meshApi.getStats(),
      ]);

      if (nodesRes.status === 'fulfilled') {
        setNodes(nodesRes.value);
        if (nodesRes.value.length > 0 && !selectedSourceNodeId) {
          setSelectedSourceNodeId(nodesRes.value[0].id);
        }
      }
      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMeshData();
  }, []);

  const handleCalculateRoute = async () => {
    if (!selectedSourceNodeId) {
      setError('Please select a source node to compute A* routing to a mesh gateway.');
      return;
    }
    setIsRouting(true);
    setError(null);
    try {
      const res = await meshApi.findRouteToGateway(selectedSourceNodeId);
      setRouteResult(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsRouting(false);
    }
  };

  const handleRegisterNode = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await meshApi.registerNode({
        device_id: deviceId,
        node_type: nodeType,
        is_gateway: isGateway,
        battery_pct: batteryPct ? parseInt(batteryPct, 10) : undefined,
        latitude: nodeLat ? parseFloat(nodeLat) : undefined,
        longitude: nodeLon ? parseFloat(nodeLon) : undefined,
      });
      setIsNodeModalOpen(false);
      await fetchMeshData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleRegisterEdge = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await meshApi.registerEdge({
        source_node_id: edgeSource,
        target_node_id: edgeTarget,
        hop_cost: parseFloat(hopCost),
        signal_quality: signalQuality ? parseFloat(signalQuality) : undefined,
      });
      setIsEdgeModalOpen(false);
      await fetchMeshData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleHeartbeat = async (nodeId: string) => {
    try {
      await meshApi.updateHeartbeat(nodeId, { battery_pct: 95 });
      await fetchMeshData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const nodeColumns: Column<MeshNodeResponse>[] = [
    { header: 'Device ID', accessor: (n) => <strong>{n.device_id}</strong> },
    { header: 'Type', accessor: (n) => <span className="mono">{n.node_type}</span> },
    {
      header: 'Role',
      accessor: (n) => (
        <StatusBadge
          status={n.is_gateway ? 'ACTIVE' : 'NEUTRAL'}
          label={n.is_gateway ? 'Gateway Node' : 'Client / Relay'}
          size="sm"
        />
      ),
    },
    {
      header: 'Battery',
      accessor: (n) => (n.battery_pct != null ? `${n.battery_pct}%` : '—'),
    },
    {
      header: 'Location',
      accessor: (n) =>
        n.latitude && n.longitude ? (
          <span className="mono">{`${n.latitude.toFixed(3)}, ${n.longitude.toFixed(3)}`}</span>
        ) : (
          '—'
        ),
    },
    {
      header: 'Status',
      accessor: (n) => <StatusBadge status={n.is_active ? 'ACTIVE' : 'INACTIVE'} size="sm" />,
    },
    {
      header: 'Action',
      render: (n) => (
        <Button size="sm" onClick={() => handleHeartbeat(n.id)}>
          Send Heartbeat
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Mesh Network & A* Routing"
        subtitle="Decentralized multi-hop opportunistic mesh routing to edge gateways"
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setIsNodeModalOpen(true)}>
              Register Node
            </Button>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setIsEdgeModalOpen(true)}>
              Add Link (Edge)
            </Button>
            <Button size="sm" icon={<RefreshCw size={14} />} onClick={fetchMeshData} isLoading={isLoading}>
              Refresh Mesh
            </Button>
          </div>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />

      {/* Network Stats */}
      <div className="metrics-grid">
        <MetricCard
          label="Total Nodes"
          value={stats ? stats.total_nodes : nodes.length}
          desc={stats ? `${stats.active_nodes} currently active` : 'Network active'}
          icon={<Share2 size={18} />}
        />

        <MetricCard
          label="Gateway Nodes"
          value={stats ? stats.gateway_nodes : nodes.filter((n) => n.is_gateway).length}
          desc="Internet-uplink enabled gateways"
          icon={<Radio size={18} />}
        />

        <MetricCard
          label="Mesh Edges"
          value={stats ? stats.total_edges : '—'}
          desc={stats ? `Density: ${(stats.density * 100).toFixed(1)}%` : 'Link topology'}
          icon={<Cpu size={18} />}
        />
      </div>

      {/* A* Route Calculator */}
      <Card title="A* Mesh Route Calculation" subtitle="Execute server-side heuristic graph search to locate optimal gateway route">
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <Select
              label="Select Origin / Source Node *"
              value={selectedSourceNodeId}
              onChange={(e) => setSelectedSourceNodeId(e.target.value)}
              options={
                nodes.length > 0
                  ? nodes.map((n) => ({
                      value: n.id,
                      label: `${n.device_id} (${n.node_type}${n.is_gateway ? ' - GATEWAY' : ''})`,
                    }))
                  : [{ value: '', label: 'No mesh nodes registered' }]
              }
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <Button
              variant="primary"
              onClick={handleCalculateRoute}
              isLoading={isRouting}
              disabled={!selectedSourceNodeId}
              icon={<Route size={15} />}
            >
              Compute A* Optimal Path
            </Button>
          </div>
        </div>

        {/* Path Result Visualizer */}
        {routeResult && (
          <div
            style={{
              marginTop: 16,
              padding: 16,
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <StatusBadge status={routeResult.success ? 'SUCCESS' : 'FAILED'} label={routeResult.success ? 'Route Found' : 'No Route to Gateway'} />
                <span style={{ fontSize: '13px', fontWeight: 600 }}>
                  Hop Count: {routeResult.hop_count} • Cost: {routeResult.total_cost.toFixed(2)} • Quality: {(routeResult.route_quality * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {routeResult.path && routeResult.path.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                {routeResult.path.map((nodeId, idx) => (
                  <React.Fragment key={nodeId}>
                    <span
                      style={{
                        padding: '4px 8px',
                        backgroundColor: 'var(--bg-card)',
                        border: '1px solid var(--border-main)',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11.5px',
                      }}
                    >
                      {nodes.find((n) => n.id === nodeId)?.device_id || nodeId.substring(0, 8)}
                    </span>
                    {idx < routeResult.path.length - 1 && <span style={{ color: 'var(--text-muted)' }}>→</span>}
                  </React.Fragment>
                ))}
              </div>
            )}

            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              <strong>A* Details:</strong> {routeResult.details}
            </div>
          </div>
        )}
      </Card>

      {/* Nodes Table */}
      <div style={{ marginTop: 20 }}>
        <Card title="Registered Mesh Nodes" subtitle="List of active tourist devices, relay hops, and edge gateways">
          {isLoading ? (
            <LoadingState message="Fetching mesh topology..." />
          ) : (
            <DataTable
              columns={nodeColumns}
              data={nodes}
              keyExtractor={(n) => n.id}
              emptyMessage="No mesh nodes found in backend database."
            />
          )}
        </Card>
      </div>

      {/* Register Node Modal */}
      <Modal isOpen={isNodeModalOpen} onClose={() => setIsNodeModalOpen(false)} title="Register Mesh Node">
        <form onSubmit={handleRegisterNode}>
          <Input
            label="Device ID *"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            placeholder="e.g. node-lora-01"
            required
          />
          <Select
            label="Node Type"
            value={nodeType}
            onChange={(e) => setNodeType(e.target.value)}
            options={[
              { value: 'TOURIST_DEVICE', label: 'Tourist Mobile Device' },
              { value: 'RELAY_NODE', label: 'Dedicated Relay / Repeater' },
              { value: 'GATEWAY_NODE', label: 'Edge Gateway (Internet Connected)' },
            ]}
          />
          <div className="form-grid-2">
            <Input
              label="Battery Percentage (%)"
              type="number"
              min="0"
              max="100"
              value={batteryPct}
              onChange={(e) => setBatteryPct(e.target.value)}
            />
            <div style={{ paddingTop: 26 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={isGateway}
                  onChange={(e) => setIsGateway(e.target.checked)}
                />
                <span>Is Gateway Node</span>
              </label>
            </div>
          </div>
          <div className="form-grid-2">
            <Input
              label="Latitude"
              type="number"
              step="any"
              value={nodeLat}
              onChange={(e) => setNodeLat(e.target.value)}
            />
            <Input
              label="Longitude"
              type="number"
              step="any"
              value={nodeLon}
              onChange={(e) => setNodeLon(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
            <Button type="button" onClick={() => setIsNodeModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Register Node
            </Button>
          </div>
        </form>
      </Modal>

      {/* Register Edge Modal */}
      <Modal isOpen={isEdgeModalOpen} onClose={() => setIsEdgeModalOpen(false)} title="Register Mesh Edge (Link)">
        <form onSubmit={handleRegisterEdge}>
          <Select
            label="Source Node *"
            value={edgeSource}
            onChange={(e) => setEdgeSource(e.target.value)}
            options={[
              { value: '', label: 'Select source...' },
              ...nodes.map((n) => ({ value: n.id, label: n.device_id })),
            ]}
            required
          />
          <Select
            label="Target Node *"
            value={edgeTarget}
            onChange={(e) => setEdgeTarget(e.target.value)}
            options={[
              { value: '', label: 'Select target...' },
              ...nodes.map((n) => ({ value: n.id, label: n.device_id })),
            ]}
            required
          />
          <div className="form-grid-2">
            <Input
              label="Hop Cost (Weight)"
              type="number"
              step="0.1"
              value={hopCost}
              onChange={(e) => setHopCost(e.target.value)}
              required
            />
            <Input
              label="Signal Quality (0.0 - 1.0)"
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={signalQuality}
              onChange={(e) => setSignalQuality(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
            <Button type="button" onClick={() => setIsEdgeModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Register Link
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
