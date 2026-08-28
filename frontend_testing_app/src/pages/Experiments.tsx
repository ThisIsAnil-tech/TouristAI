import React, { useEffect, useState } from 'react';
import {
  PageHeader,
  Card,
  Button,
  StatusBadge,
  ErrorMessage,
  MessageBanner,
} from '../components';
import { experimentsApi } from '../api/experiments';
import { ExperimentListItem, ExperimentRunResponse } from '../types';
import { getErrorMessage } from '../api/client';
import {
  Play,
  RefreshCw,
} from 'lucide-react';

interface ExperimentMeta {
  key: string;
  title: string;
  category: string;
  description: string;
  metrics: string[];
}

const EXPERIMENT_DEFINITIONS: ExperimentMeta[] = [
  {
    key: 'audio_experiment',
    title: '1. Distress Sound Detection',
    category: 'Edge AI / Audio',
    description: 'Evaluates MobileNetV2 distress sound classification accuracy, precision, recall, and F1 on audio datasets.',
    metrics: ['Accuracy', 'F1-Score', 'Inference Latency (ms)', 'False Positive Rate'],
  },
  {
    key: 'gps_experiment',
    title: '2. GPS Anomaly Detection',
    category: 'Spatial Intelligence',
    description: 'Benchmarks spatial jump filtering, Kalman filter tracking, and boundary containment deviation.',
    metrics: ['Detection Rate', 'False Alarm Rate', 'Mean Distance Error (m)'],
  },
  {
    key: 'risk_experiment',
    title: '3. Environmental Risk Score',
    category: 'Risk Engine',
    description: 'Tests tri-factor multi-source weighted risk calculation and adaptive threshold (θ) tuning.',
    metrics: ['Dynamic Threshold Shift', 'Weight Sensitivity', 'Computation Time'],
  },
  {
    key: 'emergency_decision_experiment',
    title: '4. Emergency Decision Engine',
    category: 'Decision Engine',
    description: 'Evaluates multi-modal Bayesian/rule-based decision fusion for SOS suppression and escalation.',
    metrics: ['Decision Accuracy', 'Suppression Rate', 'Evaluation Latency (ms)'],
  },
  {
    key: 'internet_alert_experiment',
    title: '5. Internet Alerts',
    category: 'Communication',
    description: 'Measures internet alert delivery latency, throughput, and HTTP webhook reliability.',
    metrics: ['Delivery Latency (ms)', 'Success Rate (%)', 'Throughput (req/s)'],
  },
  {
    key: 'sms_alert_experiment',
    title: '6. SMS Alerts',
    category: 'Communication',
    description: 'Evaluates cellular SMS gateway latency, carrier delivery confirmation, and fallback timeout.',
    metrics: ['Carrier Delivery Time (s)', 'Success Rate (%)', 'Retry Latency'],
  },
  {
    key: 'mesh_experiment',
    title: '7. Mesh Communication',
    category: 'Mesh Network',
    description: 'Benchmarks A* heuristic multi-hop routing, hop count scaling, and packet delivery ratio.',
    metrics: ['Packet Delivery Ratio (PDR)', 'Mean Hop Count', 'Routing Overhead'],
  },
  {
    key: 'blockchain_experiment',
    title: '8. Blockchain Identity',
    category: 'Security & Identity',
    description: 'Evaluates smart contract gas consumption, block latency, and access revocation speed.',
    metrics: ['Gas Used', 'Transaction Latency (ms)', 'On-chain Verification Time'],
  },
  {
    key: 'mobile_performance_experiment',
    title: '9. Mobile Application Performance',
    category: 'Client Performance',
    description: 'Measures mobile UI rendering frame rate (FPS), memory footprint, and background thread load.',
    metrics: ['Frame Rate (FPS)', 'RAM Usage (MB)', 'CPU Utilization (%)'],
  },
  {
    key: 'edge_ai_experiment',
    title: '10. Edge AI Quantization',
    category: 'Edge AI',
    description: 'Compares INT8 quantized TFLite/PyTorch model size, memory bandwidth, and edge inference speed.',
    metrics: ['Model Size (MB)', 'Quantization Loss (%)', 'Inference Speedup'],
  },
  {
    key: 'battery_experiment',
    title: '11. Battery Drain Analysis',
    category: 'Power Efficiency',
    description: 'Quantifies battery drain (% per hour) across continuous GPS tracking and audio listening modes.',
    metrics: ['Drain Rate (%/hr)', 'Power Consumption (mW)', 'Projected Lifetime (hrs)'],
  },
  {
    key: 'emergency_response_experiment',
    title: '12. Emergency Response End-to-End',
    category: 'System Integration',
    description: 'Measures total time from audio/GPS trigger to responder notification confirmation.',
    metrics: ['End-to-End Latency (s)', 'Pipeline Reliability (%)'],
  },
  {
    key: 'field_test_experiment',
    title: '13. Field Test Benchmark',
    category: 'Field Validation',
    description: 'Aggregates empirical trail test readings across remote forest and mountainous terrains.',
    metrics: ['Field Coverage (%)', 'Connectivity Loss Recovery Time'],
  },
  {
    key: 'scalability_experiment',
    title: '14. System Scalability',
    category: 'Scalability',
    description: 'Load tests backend API under high concurrency (100 to 10,000 concurrent tourist sessions).',
    metrics: ['Peak Throughput (RPS)', '95th Percentile Latency', 'Error Rate'],
  },
  {
    key: 'overall_system_experiment',
    title: '15. Overall System Evaluation',
    category: 'System Integration',
    description: 'Full comparative benchmark matrix synthesizing all 14 subsystem evaluation metrics.',
    metrics: ['Comprehensive Score', 'Comparative Baseline Delta'],
  },
];

export const ExperimentsPage: React.FC = () => {
  const [runs, setRuns] = useState<ExperimentListItem[]>([]);
  const [runningKey, setRunningKey] = useState<string | null>(null);
  const [lastRunResponse, setLastRunResponse] = useState<ExperimentRunResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchExperimentRuns = async () => {
    setIsLoading(true);
    try {
      const res = await experimentsApi.listExperiments();
      setRuns(res);
    } catch (err) {
      console.warn('Could not fetch experiment runs', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchExperimentRuns();
  }, []);

  const handleRunExperiment = async (expKey: string) => {
    setRunningKey(expKey);
    setError(null);
    try {
      const res = await experimentsApi.runExperiment(expKey);
      setLastRunResponse(res);
      await fetchExperimentRuns();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRunningKey(null);
    }
  };

  const getRunStatus = (key: string): string => {
    const run = runs.find((r) => r.name === key);
    return run ? run.status : 'NOT_RUN';
  };

  return (
    <div>
      <PageHeader
        title="Research Paper Evaluation Suite"
        subtitle="15 empirical experiments for academic evaluation & performance benchmarking"
        actions={
          <Button size="sm" icon={<RefreshCw size={14} />} onClick={fetchExperimentRuns} isLoading={isLoading}>
            Refresh Runs
          </Button>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {lastRunResponse && (
        <MessageBanner
          type="info"
          title={`Experiment ${lastRunResponse.experiment_name} Triggered`}
          message={`${lastRunResponse.message} (ID: ${lastRunResponse.experiment_id})`}
          onDismiss={() => setLastRunResponse(null)}
        />
      )}

      {/* Grid of 15 Experiments */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 16 }}>
        {EXPERIMENT_DEFINITIONS.map((exp) => {
          const status = getRunStatus(exp.key);
          const isCurrentlyRunning = runningKey === exp.key;

          return (
            <Card key={exp.key} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {exp.category}
                  </span>
                  <h4 style={{ fontSize: '14.5px', fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                    {exp.title}
                  </h4>
                </div>
                <StatusBadge
                  status={status}
                  label={status === 'NOT_RUN' ? 'Not Run — Dataset/Device Required' : status}
                  size="sm"
                />
              </div>

              <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', flex: 1, marginBottom: 12 }}>
                {exp.description}
              </p>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 10, marginTop: 'auto' }}>
                <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: 8 }}>
                  <strong>Target Metrics:</strong> {exp.metrics.join(' • ')}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {exp.key}
                  </span>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => handleRunExperiment(exp.key)}
                    isLoading={isCurrentlyRunning}
                    icon={<Play size={12} />}
                  >
                    Execute Suite
                  </Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
