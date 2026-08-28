import React, { useEffect, useState } from 'react';
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
  MetricCard,
  MessageBanner,
} from '../components';
import { systemApi } from '../api/system';
import { HealthResponse, ResponderResponse, TelemetryRequest } from '../types';
import { getErrorMessage } from '../api/client';
import {
  Database,
  Server,
  RefreshCw,
  Send,
  UserCheck,
} from 'lucide-react';

export const SystemStatusPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [responders, setResponders] = useState<ResponderResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [telemetryMsg, setTelemetryMsg] = useState<string | null>(null);

  // Telemetry simulation form
  const [fps, setFps] = useState<string>('58.5');
  const [cpuPct, setCpuPct] = useState<string>('14.2');
  const [ramMb, setRamMb] = useState<string>('82.4');
  const [batteryPct, setBatteryPct] = useState<string>('78');
  const [batteryDrain, setBatteryDrain] = useState<string>('4.2');
  const [inferTime, setInferTime] = useState<string>('42.0');
  const [deviceModel, setDeviceModel] = useState<string>('Pixel 7a (Android 14)');
  const [isSubmittingTelemetry, setIsSubmittingTelemetry] = useState<boolean>(false);

  const fetchStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [hRes, rRes] = await Promise.allSettled([
        systemApi.getHealth(),
        systemApi.listResponders(),
      ]);

      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      else setHealth(null);

      if (rRes.status === 'fulfilled') setResponders(rRes.value);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleToggleAvailability = async (responderId: string, currentStatus: boolean) => {
    try {
      await systemApi.updateResponderAvailability(responderId, !currentStatus);
      await fetchStatus();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleSubmitTelemetry = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingTelemetry(true);
    setError(null);
    setTelemetryMsg(null);
    try {
      const payload: TelemetryRequest = {
        fps: fps ? parseFloat(fps) : undefined,
        cpu_pct: cpuPct ? parseFloat(cpuPct) : undefined,
        ram_mb: ramMb ? parseFloat(ramMb) : undefined,
        battery_pct: batteryPct ? parseFloat(batteryPct) : undefined,
        battery_drain_per_hour: batteryDrain ? parseFloat(batteryDrain) : undefined,
        inference_time_ms: inferTime ? parseFloat(inferTime) : undefined,
        device_model: deviceModel,
        app_version: '1.0.0-research',
        os_version: 'Android 14',
      };
      const res = await systemApi.submitTelemetry(payload);
      setTelemetryMsg(`Telemetry recorded: ${res.message}`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmittingTelemetry(false);
    }
  };

  const responderColumns: Column<ResponderResponse>[] = [
    { header: 'Organization / Agency', accessor: (r) => <strong>{r.organization}</strong> },
    {
      header: 'Availability',
      accessor: (r) => (
        <StatusBadge
          status={r.is_available ? 'AVAILABLE' : 'UNAVAILABLE'}
          size="sm"
        />
      ),
    },
    { header: 'Responder UUID', accessor: (r) => <span className="mono" style={{ fontSize: '11px' }}>{r.id}</span> },
    {
      header: 'Action',
      render: (r) => (
        <Button
          size="sm"
          onClick={() => handleToggleAvailability(r.id, r.is_available)}
        >
          {r.is_available ? 'Set Unavailable' : 'Set Available'}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="System Status & Health Telemetry"
        subtitle="Infrastructure health, responder availability, and mobile diagnostic telemetry"
        actions={
          <Button size="sm" icon={<RefreshCw size={14} />} onClick={fetchStatus} isLoading={isLoading}>
            Refresh Health
          </Button>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {telemetryMsg && <MessageBanner type="success" message={telemetryMsg} onDismiss={() => setTelemetryMsg(null)} />}

      {/* Health Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="FastAPI Service"
          value={health ? health.status.toUpperCase() : 'UNAVAILABLE'}
          badge={health ? <StatusBadge status={health.status} /> : <StatusBadge status="UNAVAILABLE" />}
          desc={health ? `Environment: ${health.environment}` : 'Service not responding'}
          icon={<Server size={18} />}
        />

        <MetricCard
          label="PostgreSQL Database"
          value={health?.database ? health.database.toUpperCase() : 'UNKNOWN'}
          badge={health?.database === 'connected' ? <StatusBadge status="ACTIVE" label="Connected" /> : <StatusBadge status="INACTIVE" label="Disconnected" />}
          desc={health ? 'Connection pool operational' : 'Database offline'}
          icon={<Database size={18} />}
        />

        <MetricCard
          label="Active Responders"
          value={responders.filter((r) => r.is_available).length}
          desc={`Out of ${responders.length} registered agencies`}
          icon={<UserCheck size={18} />}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Responder Management */}
        <Card title="Emergency Responders" subtitle="Registered disaster and search-and-rescue teams">
          {isLoading ? (
            <LoadingState message="Loading responders list..." />
          ) : (
            <DataTable
              columns={responderColumns}
              data={responders}
              keyExtractor={(r) => r.id}
              emptyMessage="No responders registered in backend."
            />
          )}
        </Card>

        {/* Telemetry Simulator Form */}
        <Card title="Simulate Mobile Telemetry Submission" subtitle="POST /api/v1/telemetry/mobile (battery, CPU, memory benchmark)">
          <form onSubmit={handleSubmitTelemetry}>
            <div className="form-grid-2">
              <Input
                label="UI Frame Rate (FPS)"
                type="number"
                step="0.1"
                value={fps}
                onChange={(e) => setFps(e.target.value)}
              />
              <Input
                label="CPU Usage (%)"
                type="number"
                step="0.1"
                value={cpuPct}
                onChange={(e) => setCpuPct(e.target.value)}
              />
            </div>

            <div className="form-grid-2">
              <Input
                label="RAM Usage (MB)"
                type="number"
                step="0.1"
                value={ramMb}
                onChange={(e) => setRamMb(e.target.value)}
              />
              <Input
                label="Battery Level (%)"
                type="number"
                value={batteryPct}
                onChange={(e) => setBatteryPct(e.target.value)}
              />
            </div>

            <div className="form-grid-2">
              <Input
                label="Battery Drain Rate (% / hr)"
                type="number"
                step="0.1"
                value={batteryDrain}
                onChange={(e) => setBatteryDrain(e.target.value)}
              />
              <Input
                label="Audio Inference Time (ms)"
                type="number"
                step="0.1"
                value={inferTime}
                onChange={(e) => setInferTime(e.target.value)}
              />
            </div>

            <Input
              label="Simulated Device Model"
              value={deviceModel}
              onChange={(e) => setDeviceModel(e.target.value)}
            />

            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmittingTelemetry}
              icon={<Send size={14} />}
              style={{ width: '100%' }}
            >
              Submit Mobile Diagnostic Telemetry
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
};
