import React, { useState } from 'react';
import {
  PageHeader,
  Card,
  Input,
  Select,
  Button,
  StatusBadge,
  ErrorMessage,
} from '../components';
import { audioApi } from '../api/audio';
import { AudioClass, AudioDetectionResponse } from '../types';
import { getErrorMessage } from '../api/client';
import { Mic, Upload, Cpu, Smartphone } from 'lucide-react';

export const AudioPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'MODE_A' | 'MODE_B'>('MODE_A');

  // Mode A state (Edge Simulation)
  const [predictedClass, setPredictedClass] = useState<AudioClass>('SCREAM');
  const [confidence, setConfidence] = useState<string>('0.87');
  const [inferenceTime, setInferenceTime] = useState<string>('45.2');
  const [riskScore, setRiskScore] = useState<string>('6.5');

  // Mode B state (Audio File Upload)
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileRiskScore, setFileRiskScore] = useState<string>('5.0');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AudioDetectionResponse | null>(null);

  const handleModeASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const conf = parseFloat(confidence);
      const risk = parseFloat(riskScore);
      const timeMs = parseFloat(inferenceTime);

      const res = await audioApi.submitDetectionResult({
        predicted_class: predictedClass,
        confidence: conf,
        risk_score: isNaN(risk) ? 5.0 : risk,
        inference_time_ms: isNaN(timeMs) ? undefined : timeMs,
        model_version: 'MobileNetV2-Edge-v1.0',
      });
      setResult(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleModeBSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select an audio file (WAV/MP3/FLAC) to upload.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const risk = parseFloat(fileRiskScore);
      const res = await audioApi.inferAudioFile(selectedFile, isNaN(risk) ? 5.0 : risk);
      setResult(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const audioClassOptions = [
    { value: 'SCREAM', label: 'Scream (Distress)' },
    { value: 'GUNSHOT', label: 'Gunshot (Distress)' },
    { value: 'EXPLOSION', label: 'Explosion (Distress)' },
    { value: 'CALL_FOR_HELP', label: 'Call for Help (Distress)' },
    { value: 'GLASS_BREAK', label: 'Glass Break (Distress)' },
    { value: 'NORMAL', label: 'Normal Ambient Sound' },
    { value: 'UNKNOWN', label: 'Unknown Background Noise' },
  ];

  return (
    <div>
      <PageHeader
        title="Distress Audio Detection"
        subtitle="Edge vs Backend ML classification with dynamic risk-adjusted thresholding"
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />

      {/* Mode Switcher */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <button
          className={`btn ${activeTab === 'MODE_A' ? 'btn-primary' : ''}`}
          onClick={() => { setActiveTab('MODE_A'); setResult(null); setError(null); }}
          style={{ flex: 1, padding: '12px 16px', justifyContent: 'flex-start' }}
        >
          <Smartphone size={18} />
          <div style={{ textAlign: 'left', marginLeft: 8 }}>
            <div style={{ fontWeight: 600 }}>Mode A: Edge Detection Ingestion</div>
            <div style={{ fontSize: '11px', opacity: 0.8 }}>Mobile client runs local ML and transmits inference summary</div>
          </div>
        </button>

        <button
          className={`btn ${activeTab === 'MODE_B' ? 'btn-primary' : ''}`}
          onClick={() => { setActiveTab('MODE_B'); setResult(null); setError(null); }}
          style={{ flex: 1, padding: '12px 16px', justifyContent: 'flex-start' }}
        >
          <Cpu size={18} />
          <div style={{ textAlign: 'left', marginLeft: 8 }}>
            <div style={{ fontWeight: 600 }}>Mode B: Backend Raw Audio Inference</div>
            <div style={{ fontSize: '11px', opacity: 0.8 }}>Upload audio sample for server-side PyTorch MobileNetV2 inference</div>
          </div>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Left: Input Form according to Mode */}
        {activeTab === 'MODE_A' ? (
          <Card title="Edge Detection Simulation (Mode A)" subtitle="Simulates mobile edge inference telemetry">
            <form onSubmit={handleModeASubmit}>
              <Select
                label="Predicted Audio Class *"
                value={predictedClass}
                onChange={(e) => setPredictedClass(e.target.value as AudioClass)}
                options={audioClassOptions}
              />

              <div className="form-grid-2">
                <Input
                  label="Confidence (0.00 - 1.00) *"
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={confidence}
                  onChange={(e) => setConfidence(e.target.value)}
                  required
                />
                <Input
                  label="Inference Time (ms)"
                  type="number"
                  step="0.1"
                  value={inferenceTime}
                  onChange={(e) => setInferenceTime(e.target.value)}
                />
              </div>

              <Input
                label="Environmental Risk Score at Location (0 - 10)"
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={riskScore}
                onChange={(e) => setRiskScore(e.target.value)}
                helperText="Higher risk lowers the threshold θ required to declare distress"
              />

              <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
                <span className="form-label" style={{ width: '100%' }}>Quick Presets:</span>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => { setPredictedClass('SCREAM'); setConfidence('0.88'); setRiskScore('6.0'); }}
                >
                  High Risk Scream (0.88 conf, Risk 6.0)
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => { setPredictedClass('GLASS_BREAK'); setConfidence('0.55'); setRiskScore('2.0'); }}
                >
                  Low Risk Borderline (0.55 conf, Risk 2.0)
                </Button>
              </div>

              <Button
                type="submit"
                variant="primary"
                isLoading={isLoading}
                icon={<Mic size={15} />}
                style={{ width: '100%' }}
              >
                Submit Edge Result
              </Button>
            </form>
          </Card>
        ) : (
          <Card title="Raw Audio Upload (Mode B)" subtitle="Upload .wav / .mp3 for server-side PyTorch inference">
            <form onSubmit={handleModeBSubmit}>
              <div className="form-group">
                <label className="form-label">Select Audio File (WAV, MP3, FLAC) *</label>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="form-input"
                  required
                />
                {selectedFile && (
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: 4 }}>
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>

              <Input
                label="Ambient Risk Score (0 - 10)"
                type="number"
                step="0.1"
                min="0"
                max="10"
                value={fileRiskScore}
                onChange={(e) => setFileRiskScore(e.target.value)}
                helperText="Applied to the adaptive threshold decision formula"
              />

              <Button
                type="submit"
                variant="primary"
                isLoading={isLoading}
                icon={<Upload size={15} />}
                style={{ width: '100%' }}
              >
                Upload & Run Backend Inference
              </Button>
            </form>
          </Card>
        )}

        {/* Right: Decision Output */}
        <div>
          <Card title="Distress Classification Output" subtitle="Evaluated with adaptive threshold (θ)">
            {result ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Distress Verified:</span>
                  <StatusBadge
                    status={result.is_distress ? 'DISTRESS' : 'NORMAL'}
                    label={result.is_distress ? 'EMERGENCY DISTRESS' : 'NORMAL (No Distress)'}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Predicted Class:</span>
                  <strong className="mono">{result.predicted_class}</strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Model Confidence:</span>
                  <span className="mono">{(result.confidence * 100).toFixed(1)}%</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Adaptive Threshold Used (θ):</span>
                  <span className="mono">{result.adaptive_threshold_used != null ? result.adaptive_threshold_used.toFixed(3) : '—'}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Risk Score at Detection:</span>
                  <span className="mono">{result.risk_score_at_detection != null ? result.risk_score_at_detection.toFixed(1) : '5.0'}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Pipeline Mode:</span>
                  <StatusBadge status={result.mode} size="sm" />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Detection Record ID:</span>
                  <span className="mono" style={{ fontSize: '11px' }}>{result.detection_id}</span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>
                Run edge detection or upload an audio sample to evaluate classification.
              </div>
            )}
          </Card>

          <Card title="Adaptive Threshold Logic" subtitle="Research Decision Formula">
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              The threshold θ dynamically adjusts based on risk score <code>R ∈ [0, 10]</code>:
              <div className="code-block" style={{ margin: '8px 0' }}>
                θ(R) = θ_base - α × (R - 5.0)<br />
                Distress Condition: (Confidence ≥ θ(R)) AND (Class ∈ DistressClasses)
              </div>
              When environmental danger is high, lower confidence is required to trigger emergency alarms.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
