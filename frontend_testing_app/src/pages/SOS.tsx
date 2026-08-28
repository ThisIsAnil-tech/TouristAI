import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  PageHeader,
  Card,
  Input,
  Button,
  StatusBadge,
  ErrorMessage,
  MessageBanner,
} from '../components';
import { sosApi } from '../api/sos';
import { SosEvaluateRequest, SosResponse } from '../types';
import { getErrorMessage } from '../api/client';
import {
  AlertOctagon,
  Radio,
  Sliders,
  Send,
} from 'lucide-react';

export const SOSPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // Manual SOS Form
  const [manualMessage, setManualMessage] = useState<string>('Tourist requested immediate assistance via manual button');
  const [manualLat, setManualLat] = useState<string>('10.5276');
  const [manualLon, setManualLon] = useState<string>('76.2144');

  // Automated Multi-modal Evaluation Form
  const [evalAudioConf, setEvalAudioConf] = useState<string>('0.85');
  const [evalAudioDistress, setEvalAudioDistress] = useState<boolean>(true);
  const [evalGpsAnomalous, setEvalGpsAnomalous] = useState<boolean>(true);
  const [evalGpsConsecutive, setEvalGpsConsecutive] = useState<string>('3');
  const [evalRiskScore, setEvalRiskScore] = useState<string>('7.2');

  const [activeSosResponse, setActiveSosResponse] = useState<SosResponse | null>(null);
  const [activeSosId, setActiveSosId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleManualSos = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setError('Please sign in to trigger an SOS event.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const res = await sosApi.triggerManualSos({
        message: manualMessage,
        latitude: manualLat ? parseFloat(manualLat) : undefined,
        longitude: manualLon ? parseFloat(manualLon) : undefined,
      });
      setActiveSosResponse(res);
      if (res.sos_event_id) {
        setActiveSosId(res.sos_event_id);
      }
      setSuccessMessage('Manual SOS successfully registered in emergency backend pipeline.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvaluateSos = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setError('Please sign in to evaluate emergency criteria.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const req: SosEvaluateRequest = {
        audio_confidence: evalAudioConf ? parseFloat(evalAudioConf) : undefined,
        audio_is_distress: evalAudioDistress,
        gps_is_anomalous: evalGpsAnomalous,
        gps_consecutive_anomalies: evalGpsConsecutive ? parseInt(evalGpsConsecutive, 10) : undefined,
        risk_score: evalRiskScore ? parseFloat(evalRiskScore) : undefined,
        latitude: manualLat ? parseFloat(manualLat) : undefined,
        longitude: manualLon ? parseFloat(manualLon) : undefined,
      };

      const res = await sosApi.evaluateSos(req);
      setActiveSosResponse(res);
      if (res.sos_event_id) {
        setActiveSosId(res.sos_event_id);
      }
      setSuccessMessage('Multi-modal emergency evaluation completed by backend DecisionEngine.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolveSos = async () => {
    if (!activeSosId) {
      setError('No active SOS ID to resolve.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await sosApi.resolveSos(activeSosId);
      setSuccessMessage(`SOS Event ${activeSosId} marked as RESOLVED.`);
      if (activeSosResponse) {
        setActiveSosResponse({
          ...activeSosResponse,
          details: 'Event marked RESOLVED in database.',
        });
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerAlerts = () => {
    if (activeSosId) {
      navigate('/communication', { state: { sosId: activeSosId } });
    }
  };

  return (
    <div>
      <PageHeader
        title="Emergency Decision & SOS"
        subtitle="Manual SOS triggers and multi-modal Bayesian/rule-based dispatch engine"
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {successMessage && (
        <MessageBanner
          type="success"
          message={successMessage}
          onDismiss={() => setSuccessMessage(null)}
        />
      )}

      {/* SOS Active Indicator Banner */}
      {activeSosResponse?.sos_triggered && (
        <div
          style={{
            backgroundColor: 'var(--badge-danger-bg)',
            border: '1px solid var(--badge-danger-border)',
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <AlertOctagon size={24} color="var(--badge-danger-text)" />
            <div>
              <strong style={{ fontSize: '15px', color: 'var(--badge-danger-text)', display: 'block' }}>
                SOS EVENT TRIGGERED: {activeSosResponse.trigger || 'EMERGENCY'}
              </strong>
              <span style={{ fontSize: '12.5px', color: 'var(--badge-danger-text)' }}>
                Reason: {activeSosResponse.reason} • ID: {activeSosId || 'Pending'}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="primary" size="sm" onClick={handleTriggerAlerts} icon={<Radio size={14} />}>
              Dispatch Alerts
            </Button>
            <Button size="sm" onClick={handleResolveSos} isLoading={isLoading}>
              Resolve SOS
            </Button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Manual SOS Trigger Card */}
        <Card
          title="Manual SOS Trigger"
          subtitle="Direct human emergency button (100% confidence override)"
          icon={<AlertOctagon size={16} />}
        >
          <form onSubmit={handleManualSos}>
            <Input
              label="Emergency Distress Message"
              value={manualMessage}
              onChange={(e) => setManualMessage(e.target.value)}
              placeholder="e.g. Tourist injured on trail, needs medical rescue"
            />
            <div className="form-grid-2">
              <Input
                label="Latitude"
                type="number"
                step="any"
                value={manualLat}
                onChange={(e) => setManualLat(e.target.value)}
              />
              <Input
                label="Longitude"
                type="number"
                step="any"
                value={manualLon}
                onChange={(e) => setManualLon(e.target.value)}
              />
            </div>

            <Button
              type="submit"
              variant="danger"
              isLoading={isLoading}
              icon={<AlertOctagon size={16} />}
              style={{ width: '100%', marginTop: 8 }}
            >
              TRIGGER MANUAL SOS NOW
            </Button>
          </form>
        </Card>

        {/* Multi-modal Evidence Evaluation */}
        <Card
          title="Multi-Modal Decision Engine Evaluation"
          subtitle="Tests joint decisioning: Audio Distress + GPS Anomalies + Risk Level"
          icon={<Sliders size={16} />}
        >
          <form onSubmit={handleEvaluateSos}>
            <div className="form-grid-2">
              <Input
                label="Audio Confidence (0.0 - 1.0)"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={evalAudioConf}
                onChange={(e) => setEvalAudioConf(e.target.value)}
              />
              <Input
                label="Environmental Risk (0 - 10)"
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={evalRiskScore}
                onChange={(e) => setEvalRiskScore(e.target.value)}
              />
            </div>

            <div className="form-grid-2">
              <Input
                label="Consecutive GPS Anomalies"
                type="number"
                min="0"
                value={evalGpsConsecutive}
                onChange={(e) => setEvalGpsConsecutive(e.target.value)}
              />
              <div style={{ paddingTop: 26 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={evalAudioDistress}
                    onChange={(e) => setEvalAudioDistress(e.target.checked)}
                  />
                  <span>Audio is Distress Class</span>
                </label>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={evalGpsAnomalous}
                  onChange={(e) => setEvalGpsAnomalous(e.target.checked)}
                />
                <span>GPS Reading Marked Anomalous</span>
              </label>
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              icon={<Send size={15} />}
              style={{ width: '100%' }}
            >
              Evaluate Emergency Decision Engine
            </Button>
          </form>
        </Card>
      </div>

      {/* Decision Output Summary */}
      <div style={{ marginTop: 24 }}>
        <Card title="Decision Engine Evaluation Log" subtitle="Real-time evaluation response from Python DecisionEngine">
          {activeSosResponse ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>SOS Decision:</span>
                <StatusBadge
                  status={activeSosResponse.sos_triggered ? 'DISTRESS' : 'NORMAL'}
                  label={activeSosResponse.sos_triggered ? 'TRIGGER SOS (Emergency Confirmed)' : 'DO NOT TRIGGER (Suppressed)'}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Trigger Channel:</span>
                <strong>{activeSosResponse.trigger || 'None'}</strong>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Decision Reason:</span>
                <span className="mono">{activeSosResponse.reason || '—'}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Computed Confidence:</span>
                <span className="mono">{activeSosResponse.confidence != null ? `${(activeSosResponse.confidence * 100).toFixed(1)}%` : '—'}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Adaptive Threshold θ:</span>
                <span className="mono">{activeSosResponse.adaptive_threshold != null ? activeSosResponse.adaptive_threshold.toFixed(3) : '—'}</span>
              </div>

              {activeSosResponse.sos_event_id && (
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>SOS Event UUID:</span>
                  <span className="mono" style={{ fontSize: '11.5px' }}>{activeSosResponse.sos_event_id}</span>
                </div>
              )}

              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '12px', display: 'block', marginBottom: 4 }}>
                  Engine Details:
                </span>
                <div className="code-block">{activeSosResponse.details}</div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px 0' }}>
              Trigger manual SOS or evaluate multi-modal parameters to inspect backend decisions.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
