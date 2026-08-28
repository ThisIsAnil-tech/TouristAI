import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  PageHeader,
  Card,
  Input,
  Button,
  StatusBadge,
  ErrorMessage,
  DataTable,
  Column,
  LoadingState,
} from '../components';
import { gpsApi } from '../api/gps';
import { GpsAnalyzeResponse, GpsHistoryResponse, LocationResponse } from '../types';
import { getErrorMessage } from '../api/client';
import { MapPin, Navigation, AlertTriangle, RefreshCw, Send } from 'lucide-react';

export const GPSPage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  // Form state
  const [latitude, setLatitude] = useState<string>('10.5276');
  const [longitude, setLongitude] = useState<string>('76.2144');
  const [altitude, setAltitude] = useState<string>('15.0');
  const [accuracy, setAccuracy] = useState<string>('5.0');
  const [speed, setSpeed] = useState<string>('1.2');
  const [bearing, setBearing] = useState<string>('180.0');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [lastSubmission, setLastSubmission] = useState<LocationResponse | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<GpsAnalyzeResponse | null>(null);
  const [history, setHistory] = useState<GpsHistoryResponse[]>([]);

  const fetchHistory = async () => {
    if (!user?.id) return;
    setHistoryLoading(true);
    try {
      const data = await gpsApi.getGpsHistory(user.id, 50);
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch GPS history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && user?.id) {
      fetchHistory();
    }
  }, [isAuthenticated, user?.id]);

  const handleSendLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setError('Please sign in to submit GPS coordinates.');
      return;
    }

    const lat = parseFloat(latitude);
    const lon = parseFloat(longitude);
    if (isNaN(lat) || isNaN(lon)) {
      setError('Latitude and Longitude must be valid numbers.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setAnalyzeResult(null);

    try {
      const res = await gpsApi.submitLocation({
        latitude: lat,
        longitude: lon,
        altitude_m: altitude ? parseFloat(altitude) : undefined,
        accuracy_m: accuracy ? parseFloat(accuracy) : undefined,
        speed_ms: speed ? parseFloat(speed) : undefined,
        bearing_deg: bearing ? parseFloat(bearing) : undefined,
        recorded_at: new Date().toISOString(),
      });
      setLastSubmission(res);
      await fetchHistory();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeReading = async (readingId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await gpsApi.analyzeReading(readingId);
      setAnalyzeResult(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Quick preset test points for demonstration
  const setPresetLocation = (_name: string, lat: number, lon: number) => {
    setLatitude(lat.toString());
    setLongitude(lon.toString());
  };

  const columns: Column<GpsHistoryResponse>[] = [
    {
      header: 'Recorded At',
      accessor: (r) => new Date(r.recorded_at).toLocaleString(),
    },
    {
      header: 'Latitude',
      accessor: (r) => <span className="mono">{r.latitude.toFixed(5)}</span>,
    },
    {
      header: 'Longitude',
      accessor: (r) => <span className="mono">{r.longitude.toFixed(5)}</span>,
    },
    {
      header: 'Distance Prev (m)',
      accessor: (r) => (r.distance_from_previous_m != null ? `${r.distance_from_previous_m.toFixed(1)} m` : '—'),
    },
    {
      header: 'Anomaly',
      accessor: (r) => (
        <StatusBadge
          status={r.is_anomalous ? 'ANOMALOUS' : 'NORMAL'}
          size="sm"
        />
      ),
    },
    {
      header: 'Type',
      accessor: (r) => r.anomaly_type || 'None',
    },
    {
      header: 'Action',
      render: (r) => (
        <Button
          size="sm"
          onClick={() => handleAnalyzeReading(r.id)}
          disabled={isLoading}
        >
          Analyze
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="GPS Safety & Anomaly Detection"
        subtitle="Test real-time GPS telemetry ingestion, spatial jump algorithms, and zone containment"
        actions={
          <Button
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={fetchHistory}
            isLoading={historyLoading}
          >
            Refresh History
          </Button>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />

      {/* Research workflow tracker */}
      <div className="workflow-steps">
        <span className="workflow-step active">
          <MapPin size={14} /> 1. Input Coordinates
        </span>
        <span className="workflow-arrow">→</span>
        <span className="workflow-step active">
          <Send size={14} /> 2. POST /api/v1/gps/location
        </span>
        <span className="workflow-arrow">→</span>
        <span className="workflow-step active">
          <Navigation size={14} /> 3. Python Anomaly Detector
        </span>
        <span className="workflow-arrow">→</span>
        <span className="workflow-step active">
          <AlertTriangle size={14} /> 4. Evaluate Threshold / SOS
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Form */}
        <Card title="Submit GPS Location" subtitle="Send telemetry point directly to backend">
          <form onSubmit={handleSendLocation}>
            <div className="form-grid-2">
              <Input
                label="Latitude (-90 to 90) *"
                type="number"
                step="any"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                required
              />
              <Input
                label="Longitude (-180 to 180) *"
                type="number"
                step="any"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                required
              />
            </div>

            <div className="form-grid-2">
              <Input
                label="Altitude (m)"
                type="number"
                step="any"
                value={altitude}
                onChange={(e) => setAltitude(e.target.value)}
              />
              <Input
                label="Accuracy (m)"
                type="number"
                step="any"
                value={accuracy}
                onChange={(e) => setAccuracy(e.target.value)}
              />
            </div>

            <div className="form-grid-2">
              <Input
                label="Speed (m/s)"
                type="number"
                step="any"
                value={speed}
                onChange={(e) => setSpeed(e.target.value)}
              />
              <Input
                label="Bearing (°)"
                type="number"
                step="any"
                value={bearing}
                onChange={(e) => setBearing(e.target.value)}
              />
            </div>

            {/* Presets */}
            <div style={{ marginBottom: 16 }}>
              <span className="form-label">Research Test Presets:</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setPresetLocation('Standard Trail Point', 10.5276, 76.2144)}
                >
                  Standard Trail (10.5276, 76.2144)
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setPresetLocation('Spatial Jump / Teleport', 11.8500, 77.4000)}
                >
                  Spatial Jump (11.8500, 77.4000)
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setPresetLocation('Near Zone Boundary', 10.5310, 76.2200)}
                >
                  Near Boundary (10.5310, 76.2200)
                </Button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              icon={<Send size={15} />}
              style={{ width: '100%' }}
            >
              Send Location & Analyze
            </Button>
          </form>
        </Card>

        {/* Backend Response Output */}
        <div>
          <Card title="Backend Analysis Output" subtitle="Direct result from Python GpsAnomalyDetector">
            {lastSubmission ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Anomaly Detected:</span>
                  <StatusBadge
                    status={lastSubmission.is_anomalous ? 'ANOMALOUS' : 'NORMAL'}
                    label={lastSubmission.is_anomalous ? 'YES (Anomaly)' : 'NO (Normal)'}
                  />
                </div>

                {lastSubmission.anomaly_type && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Anomaly Type:</span>
                    <strong className="mono">{lastSubmission.anomaly_type}</strong>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Distance From Previous:</span>
                  <span className="mono">
                    {lastSubmission.distance_from_previous_m != null
                      ? `${lastSubmission.distance_from_previous_m.toFixed(2)} meters`
                      : 'Initial reading (0 m)'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Consecutive Anomalies:</span>
                  <span className="mono">{lastSubmission.consecutive_anomalies}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>In High-Risk Zone:</span>
                  <StatusBadge status={lastSubmission.in_high_risk_zone} size="sm" />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Should Trigger SOS:</span>
                  <StatusBadge status={lastSubmission.should_trigger_sos} size="sm" />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Evaluation Reason:</span>
                  <div className="code-block">{lastSubmission.reason || 'Normal movement registered.'}</div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '30px 0' }}>
                Submit GPS coordinates to inspect backend anomaly calculations.
              </div>
            )}
          </Card>

          {analyzeResult && (
            <Card title="Single Reading Re-Analysis" subtitle="Output from POST /api/v1/gps/analyze">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Is Anomalous:</span>
                  <StatusBadge status={analyzeResult.is_anomalous ? 'ANOMALOUS' : 'NORMAL'} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Should Trigger SOS:</span>
                  <StatusBadge status={analyzeResult.should_trigger_sos} />
                </div>
                <div className="code-block">{analyzeResult.reason}</div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* GPS History Table */}
      <div style={{ marginTop: 24 }}>
        <Card
          title="Recent GPS Telemetry Log"
          subtitle="Fetched from GET /api/v1/gps/history/{user_id}"
        >
          {historyLoading ? (
            <LoadingState message="Loading GPS history..." />
          ) : (
            <DataTable
              columns={columns}
              data={history}
              keyExtractor={(r) => r.id}
              emptyMessage="No GPS telemetry records found for this user in backend database."
            />
          )}
        </Card>
      </div>
    </div>
  );
};
