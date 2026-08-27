import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  PageHeader,
  Card,
  MetricCard,
  StatusBadge,
  LoadingState,
  ErrorMessage,
  Button,
} from '../components';
import { systemApi } from '../api/system';
import { gpsApi } from '../api/gps';
import { riskApi } from '../api/risk';
import { meshApi } from '../api/mesh';
import { communicationApi } from '../api/communication';
import {
  HealthResponse,
  GpsHistoryResponse,
  GeographicZoneResponse,
  MeshNodeResponse,
  ContactResponse,
} from '../types';
import { getErrorMessage } from '../api/client';
import {
  Activity,
  MapPin,
  Shield,
  Share2,
  Cpu,
  RefreshCw,
  ArrowRight,
  AlertOctagon,
} from 'lucide-react';

export const Overview: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [recentGps, setRecentGps] = useState<GpsHistoryResponse[]>([]);
  const [zones, setZones] = useState<GeographicZoneResponse[]>([]);
  const [meshNodes, setMeshNodes] = useState<MeshNodeResponse[]>([]);
  const [contacts, setContacts] = useState<ContactResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Health
      try {
        const h = await systemApi.getHealth();
        setHealth(h);
      } catch {
        setHealth(null);
      }

      // If authenticated, fetch user-specific backend state
      if (isAuthenticated && user?.id) {
        const [gpsRes, zonesRes, meshRes, contactsRes] = await Promise.allSettled([
          gpsApi.getGpsHistory(user.id, 5),
          riskApi.listZones(),
          meshApi.listNodes(),
          communicationApi.listContacts(),
        ]);

        if (gpsRes.status === 'fulfilled') setRecentGps(gpsRes.value);
        if (zonesRes.status === 'fulfilled') setZones(zonesRes.value);
        if (meshRes.status === 'fulfilled') setMeshNodes(meshRes.value);
        if (contactsRes.status === 'fulfilled') setContacts(contactsRes.value);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, [isAuthenticated, user?.id]);

  const lastReading = recentGps.length > 0 ? recentGps[0] : null;

  return (
    <div>
      <PageHeader
        title="Tourist Safety Overview"
        subtitle="Real-time status of edge AI anomaly detection, risk assessment, and communication channels"
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={fetchOverviewData}
            isLoading={isLoading}
          >
            Refresh System State
          </Button>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />

      {/* Metrics Row */}
      <div className="metrics-grid">
        <MetricCard
          label="Backend Status"
          value={health?.status ? health.status.toUpperCase() : 'UNKNOWN'}
          badge={health ? <StatusBadge status={health.status} size="sm" /> : undefined}
          desc={health ? `Version ${health.version} • DB: ${health.database}` : 'Not reachable'}
          icon={<Activity size={18} />}
        />

        <MetricCard
          label="Last Known Location"
          value={
            lastReading
              ? `${lastReading.latitude.toFixed(4)}, ${lastReading.longitude.toFixed(4)}`
              : user?.last_latitude && user?.last_longitude
              ? `${user.last_latitude.toFixed(4)}, ${user.last_longitude.toFixed(4)}`
              : 'Not available'
          }
          desc={
            lastReading
              ? `Logged at ${new Date(lastReading.recorded_at).toLocaleTimeString()}`
              : 'No coordinates logged'
          }
          badge={
            lastReading ? (
              <StatusBadge
                status={lastReading.is_anomalous ? 'ANOMALOUS' : 'NORMAL'}
                size="sm"
              />
            ) : undefined
          }
          icon={<MapPin size={18} />}
        />

        <MetricCard
          label="Monitored Zones"
          value={zones.length > 0 ? zones.length : '0'}
          desc={
            zones.some((z) => z.is_high_risk)
              ? `${zones.filter((z) => z.is_high_risk).length} high-risk zones`
              : 'All zones standard'
          }
          icon={<Shield size={18} />}
        />

        <MetricCard
          label="Active Mesh Nodes"
          value={meshNodes.length > 0 ? meshNodes.length : '0'}
          desc={
            meshNodes.some((n) => n.is_gateway)
              ? `${meshNodes.filter((n) => n.is_gateway).length} gateway nodes`
              : 'No gateways registered'
          }
          icon={<Share2 size={18} />}
        />
      </div>

      {isLoading ? (
        <LoadingState message="Fetching system telemetry and backend status..." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
          {/* User & Identity State */}
          <Card
            title="Authenticated Session"
            subtitle="Current user identity & permissions"
            icon={<Cpu size={16} />}
            action={
              <Button size="sm" onClick={() => navigate('/profile')}>
                Profile Details
              </Button>
            }
          >
            {user ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Full Name:</span>
                  <strong>{user.full_name}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Email:</span>
                  <span className="mono">{user.email}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Role:</span>
                  <StatusBadge status={user.role} size="sm" />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Blockchain Identity:</span>
                  <StatusBadge status={user.blockchain_registered ? 'ACTIVE' : 'NOT_RUN'} label={user.blockchain_registered ? 'Registered' : 'Not Registered'} size="sm" />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Emergency Contacts:</span>
                  <span>{contacts.length} configured</span>
                </div>
              </div>
            ) : (
              <div style={{ padding: '16px 0', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
                  Not signed in. Sign in to access user-specific research endpoints.
                </p>
                <Button variant="primary" size="sm" onClick={() => navigate('/login')}>
                  Go to Login
                </Button>
              </div>
            )}
          </Card>

          {/* Research Modules Quick Navigation */}
          <Card title="System Testing Modules" subtitle="Direct access to algorithm verification pages">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/gps')}
              >
                <div>
                  <strong style={{ fontSize: '13px', display: 'block' }}>GPS Anomaly Detection</strong>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Verify spatial jump & route deviation filters
                  </span>
                </div>
                <ArrowRight size={16} color="var(--text-secondary)" />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/risk')}
              >
                <div>
                  <strong style={{ fontSize: '13px', display: 'block' }}>Environmental Risk & AI Threshold</strong>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Weather, news intelligence, and incident scoring
                  </span>
                </div>
                <ArrowRight size={16} color="var(--text-secondary)" />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/audio')}
              >
                <div>
                  <strong style={{ fontSize: '13px', display: 'block' }}>Audio Distress Inference</strong>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Edge MobileNetV2 classification & backend inference
                  </span>
                </div>
                <ArrowRight size={16} color="var(--text-secondary)" />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/sos')}
              >
                <div>
                  <strong style={{ fontSize: '13px', display: 'block' }}>Emergency Decision & SOS</strong>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Multi-modal Bayesian/rule-based dispatch engine
                  </span>
                </div>
                <AlertOctagon size={16} color="var(--badge-danger-text)" />
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/experiments')}
              >
                <div>
                  <strong style={{ fontSize: '13px', display: 'block' }}>Research Paper Experiments</strong>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    15 evaluation suites with benchmark metrics
                  </span>
                </div>
                <ArrowRight size={16} color="var(--text-secondary)" />
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
