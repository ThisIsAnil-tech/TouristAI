import React, { useEffect, useState } from 'react';
import {
  PageHeader,
  Card,
  Button,
  StatusBadge,
  ErrorMessage,
  DataTable,
  Column,
  LoadingState,
  Select,
  Input,
  Modal,
  MetricCard,
} from '../components';
import { riskApi } from '../api/risk';
import {
  GeographicZoneResponse,
  IncidentResponse,
  NewsEventResponse,
  RiskScoreResponse,
  WeatherResponse,
} from '../types';
import { getErrorMessage } from '../api/client';
import {
  ShieldAlert,
  CloudSun,
  Newspaper,
  History,
  Calculator,
  Plus,
  RefreshCw,
  Gauge,
} from 'lucide-react';

export const RiskPage: React.FC = () => {
  const [zones, setZones] = useState<GeographicZoneResponse[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('');
  const [riskScore, setRiskScore] = useState<RiskScoreResponse | null>(null);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [news, setNews] = useState<NewsEventResponse[]>([]);
  const [incidents, setIncidents] = useState<IncidentResponse[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRecalculating, setIsRecalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modal for new zone creation
  const [isZoneModalOpen, setIsZoneModalOpen] = useState<boolean>(false);
  const [newZoneName, setNewZoneName] = useState<string>('');
  const [minLat, setMinLat] = useState<string>('10.5000');
  const [maxLat, setMaxLat] = useState<string>('10.5500');
  const [minLon, setMinLon] = useState<string>('76.2000');
  const [maxLon, setMaxLon] = useState<string>('76.2500');
  const [centerLat, setCenterLat] = useState<string>('10.5250');
  const [centerLon, setCenterLon] = useState<string>('76.2250');
  const [isHighRisk, setIsHighRisk] = useState<boolean>(false);

  const fetchZonesAndIntelligence = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [zonesRes, newsRes, incidentsRes] = await Promise.allSettled([
        riskApi.listZones(),
        riskApi.listNews({ limit: 10 }),
        riskApi.listIncidents(),
      ]);

      if (zonesRes.status === 'fulfilled') {
        setZones(zonesRes.value);
        if (zonesRes.value.length > 0 && !selectedZoneId) {
          setSelectedZoneId(zonesRes.value[0].id);
        }
      }
      if (newsRes.status === 'fulfilled') setNews(newsRes.value);
      if (incidentsRes.status === 'fulfilled') setIncidents(incidentsRes.value);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchZoneRisk = async (zoneId: string) => {
    if (!zoneId) return;
    try {
      const score = await riskApi.getZoneRisk(zoneId);
      setRiskScore(score);
    } catch (err: any) {
      // 404 means not yet calculated for this zone
      setRiskScore(null);
    }
  };

  const fetchWeather = async () => {
    try {
      // Default coordinates or selected zone center
      const lat = centerLat ? parseFloat(centerLat) : 10.5276;
      const lon = centerLon ? parseFloat(centerLon) : 76.2144;
      const w = await riskApi.getWeatherForLocation(lat, lon);
      setWeather(w);
    } catch (err) {
      console.warn('Weather fetch failed', err);
    }
  };

  useEffect(() => {
    fetchZonesAndIntelligence();
    fetchWeather();
  }, []);

  useEffect(() => {
    if (selectedZoneId) {
      fetchZoneRisk(selectedZoneId);
    }
  }, [selectedZoneId]);

  const handleCalculateRisk = async () => {
    if (!selectedZoneId) {
      setError('Please select a zone to calculate risk.');
      return;
    }
    setIsRecalculating(true);
    setError(null);
    try {
      const score = await riskApi.calculateZoneRisk(selectedZoneId);
      setRiskScore(score);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsRecalculating(false);
    }
  };

  const handleCreateZone = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await riskApi.createZone({
        name: newZoneName,
        min_latitude: parseFloat(minLat),
        max_latitude: parseFloat(maxLat),
        min_longitude: parseFloat(minLon),
        max_longitude: parseFloat(maxLon),
        center_latitude: centerLat ? parseFloat(centerLat) : undefined,
        center_longitude: centerLon ? parseFloat(centerLon) : undefined,
        is_high_risk: isHighRisk,
      });
      setIsZoneModalOpen(false);
      await fetchZonesAndIntelligence();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const newsColumns: Column<NewsEventResponse>[] = [
    { header: 'Title', accessor: (n) => <strong>{n.title}</strong> },
    { header: 'Category', accessor: (n) => <span className="mono">{n.category}</span> },
    { header: 'Severity', accessor: (n) => <StatusBadge status={n.severity} size="sm" /> },
    { header: 'Score', accessor: (n) => <span className="mono">{n.severity_score.toFixed(1)}</span> },
    { header: 'Source', accessor: (n) => n.source || 'Local Feed' },
  ];

  const incidentColumns: Column<IncidentResponse>[] = [
    { header: 'Incident Title', accessor: (i) => i.title },
    { header: 'Severity', accessor: (i) => <StatusBadge status={i.severity} size="sm" /> },
    { header: 'Occurred At', accessor: (i) => new Date(i.occurred_at).toLocaleDateString() },
  ];

  return (
    <div>
      <PageHeader
        title="Environmental Risk & Adaptive AI Threshold"
        subtitle="Tri-factor weighted intelligence: Weather (30%) + News (40%) + Historical Incidents (30%)"
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => setIsZoneModalOpen(true)}
            >
              Add Zone
            </Button>
            <Button
              size="sm"
              icon={<RefreshCw size={14} />}
              onClick={() => {
                fetchZonesAndIntelligence();
                fetchWeather();
                if (selectedZoneId) fetchZoneRisk(selectedZoneId);
              }}
              isLoading={isLoading}
            >
              Refresh Data
            </Button>
          </div>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />

      {/* Zone Selector & Controls */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <Select
              label="Selected Geographic Zone"
              value={selectedZoneId}
              onChange={(e) => setSelectedZoneId(e.target.value)}
              options={
                zones.length > 0
                  ? zones.map((z) => ({
                      value: z.id,
                      label: `${z.name} (${z.risk_level || 'STANDARD'}${z.is_high_risk ? ' - High Risk' : ''})`,
                    }))
                  : [{ value: '', label: 'No zones registered in backend' }]
              }
            />
          </div>
          <div style={{ display: 'flex', gap: 10, alignSelf: 'flex-end', marginBottom: 16 }}>
            <Button
              variant="primary"
              onClick={handleCalculateRisk}
              isLoading={isRecalculating}
              disabled={!selectedZoneId}
              icon={<Calculator size={15} />}
            >
              Calculate Zone Risk Score
            </Button>
          </div>
        </div>
      </Card>

      {/* Risk Metrics Summary */}
      <div className="metrics-grid">
        <MetricCard
          label="Composite Risk Score"
          value={riskScore ? `${riskScore.final_score.toFixed(2)} / 10` : 'Not Calculated'}
          badge={riskScore ? <StatusBadge status={riskScore.risk_level} /> : undefined}
          desc={riskScore ? `Level: ${riskScore.risk_level}` : 'Execute calculation above'}
          icon={<ShieldAlert size={18} />}
        />

        <MetricCard
          label="Adaptive AI Threshold (θ)"
          value={riskScore ? riskScore.adaptive_threshold.toFixed(2) : '0.70 (Base)'}
          desc={
            riskScore
              ? riskScore.final_score > 6.0
                ? 'Lower threshold (higher sensitivity due to environmental risk)'
                : 'Standard baseline sensitivity'
              : 'Base threshold before risk weighting'
          }
          icon={<Gauge size={18} />}
        />

        <MetricCard
          label="Weather Component"
          value={riskScore ? `${riskScore.weather_score.toFixed(1)} / 10` : weather ? `${weather.weather_risk_score.toFixed(1)} / 10` : '—'}
          desc={weather?.weather_main ? `${weather.weather_main} • ${weather.temperature_c}°C` : 'No live observation'}
          icon={<CloudSun size={18} />}
        />

        <MetricCard
          label="News & Incidents"
          value={
            riskScore
              ? `News: ${riskScore.news_score.toFixed(1)} | Hist: ${riskScore.historical_score.toFixed(1)}`
              : `${news.length} news events`
          }
          desc={`${incidents.length} historical incidents on record`}
          icon={<Newspaper size={18} />}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Weather Intelligence Details */}
        <Card title="Weather Intelligence" subtitle="Provider: OpenWeatherMap / Real-time Station" icon={<CloudSun size={16} />}>
          {weather ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Condition:</span>
                <strong>{weather.weather_main || 'Clear'} ({weather.weather_description || 'No severe warnings'})</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Temperature:</span>
                <span className="mono">{weather.temperature_c != null ? `${weather.temperature_c}°C` : 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Humidity:</span>
                <span className="mono">{weather.humidity_pct != null ? `${weather.humidity_pct}%` : 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Wind Speed:</span>
                <span className="mono">{weather.wind_speed_ms != null ? `${weather.wind_speed_ms} m/s` : 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Calculated Weather Risk Score:</span>
                <strong className="mono">{weather.weather_risk_score.toFixed(2)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Data Source:</span>
                <StatusBadge status={weather.is_mock ? 'Mock Fallback' : 'Live API'} size="sm" />
              </div>
            </div>
          ) : (
            <LoadingState message="Fetching live weather feed..." />
          )}
        </Card>

        {/* Historical Incidents */}
        <Card title="Historical Incidents" subtitle="Regional safety records (30% weight)" icon={<History size={16} />}>
          <DataTable
            columns={incidentColumns}
            data={incidents}
            keyExtractor={(i) => i.id}
            emptyMessage="No historical safety incidents logged for this zone."
          />
        </Card>
      </div>

      {/* News Intelligence Table */}
      <div style={{ marginTop: 20 }}>
        <Card title="News & Safety Intelligence Feed" subtitle="Categorized threat events (40% weight)" icon={<Newspaper size={16} />}>
          <DataTable
            columns={newsColumns}
            data={news}
            keyExtractor={(n) => n.id}
            emptyMessage="No safety news events reported in the selected time window."
          />
        </Card>
      </div>

      {/* Modal for Zone Creation */}
      <Modal
        isOpen={isZoneModalOpen}
        onClose={() => setIsZoneModalOpen(false)}
        title="Add Geographic Zone"
      >
        <form onSubmit={handleCreateZone}>
          <Input
            label="Zone Name *"
            value={newZoneName}
            onChange={(e) => setNewZoneName(e.target.value)}
            placeholder="e.g. Munnar Forest Trail"
            required
          />
          <div className="form-grid-2">
            <Input
              label="Min Latitude *"
              type="number"
              step="any"
              value={minLat}
              onChange={(e) => setMinLat(e.target.value)}
              required
            />
            <Input
              label="Max Latitude *"
              type="number"
              step="any"
              value={maxLat}
              onChange={(e) => setMaxLat(e.target.value)}
              required
            />
          </div>
          <div className="form-grid-2">
            <Input
              label="Min Longitude *"
              type="number"
              step="any"
              value={minLon}
              onChange={(e) => setMinLon(e.target.value)}
              required
            />
            <Input
              label="Max Longitude *"
              type="number"
              step="any"
              value={maxLon}
              onChange={(e) => setMaxLon(e.target.value)}
              required
            />
          </div>
          <div className="form-grid-2">
            <Input
              label="Center Latitude"
              type="number"
              step="any"
              value={centerLat}
              onChange={(e) => setCenterLat(e.target.value)}
            />
            <Input
              label="Center Longitude"
              type="number"
              step="any"
              value={centerLon}
              onChange={(e) => setCenterLon(e.target.value)}
            />
          </div>
          <div style={{ marginTop: 8, marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: '13px' }}>
              <input
                type="checkbox"
                checked={isHighRisk}
                onChange={(e) => setIsHighRisk(e.target.checked)}
              />
              <span>Mark as High Risk Zone</span>
            </label>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button type="button" onClick={() => setIsZoneModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create Zone
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
