import React from 'react';

export interface StatusBadgeProps {
  status: string | boolean;
  variant?: 'neutral' | 'success' | 'warning' | 'danger';
  label?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  label,
  size = 'md',
}) => {
  let resolvedVariant: 'neutral' | 'success' | 'warning' | 'danger' = variant || 'neutral';

  const stringStatus = typeof status === 'boolean' ? (status ? 'TRUE' : 'FALSE') : String(status).toUpperCase();

  if (!variant) {
    if (['TRUE', 'ACTIVE', 'HEALTHY', 'CONNECTED', 'DELIVERED', 'COMPLETED', 'SUCCESS', 'AVAILABLE', 'LOW'].includes(stringStatus)) {
      resolvedVariant = 'success';
    } else if (['MEDIUM', 'PENDING', 'RUNNING', 'RETRYING', 'WARNING'].includes(stringStatus)) {
      resolvedVariant = 'warning';
    } else if (['FALSE', 'INACTIVE', 'DEGRADED', 'UNAVAILABLE', 'FAILED', 'ANOMALOUS', 'HIGH', 'CRITICAL', 'DISTRESS', 'EMERGENCY'].includes(stringStatus)) {
      resolvedVariant = 'danger';
    }
  }

  const displayText = label || (typeof status === 'boolean' ? (status ? 'Yes' : 'No') : String(status));

  return (
    <span
      className={`badge badge-${resolvedVariant}`}
      style={{ fontSize: size === 'sm' ? '10.5px' : '11.5px' }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: 'currentColor',
          display: 'inline-block',
          opacity: 0.8,
        }}
      />
      {displayText}
    </span>
  );
};

export interface MetricCardProps {
  label: string;
  value: string | number | React.ReactNode;
  desc?: string;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  desc,
  badge,
  icon,
  className = '',
}) => {
  return (
    <div className={`metric-card ${className}`}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <span className="metric-label">{label}</span>
        {icon && <span style={{ opacity: 0.7 }}>{icon}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <div className="metric-value">{value}</div>
        {badge}
      </div>
      {desc && <div className="metric-desc">{desc}</div>}
    </div>
  );
};
