import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Info, Inbox } from 'lucide-react';

// Loading State
export const LoadingState: React.FC<{ message?: string; inline?: boolean }> = ({
  message = 'Loading backend data...',
  inline = false,
}) => {
  if (inline) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '13px' }}>
        <svg
          style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" />
        </svg>
        <span>{message}</span>
      </div>
    );
  }

  return (
    <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
      <svg
        style={{ width: 24, height: 24, animation: 'spin 1s linear infinite', margin: '0 auto 12px auto', display: 'block' }}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" />
      </svg>
      <p style={{ fontSize: '13.5px' }}>{message}</p>
    </div>
  );
};

// Error / Success / Info Message
export const MessageBanner: React.FC<{
  type?: 'error' | 'success' | 'info' | 'warning';
  title?: string;
  message: string;
  onDismiss?: () => void;
}> = ({ type = 'error', title, message, onDismiss }) => {
  const isError = type === 'error';
  const isSuccess = type === 'success';
  const isWarning = type === 'warning';

  const containerClass = isError
    ? 'state-message state-message-error'
    : isSuccess
    ? 'state-message state-message-success'
    : 'state-message state-message-info';

  const icon = isError ? (
    <AlertCircle size={18} />
  ) : isSuccess ? (
    <CheckCircle size={18} />
  ) : isWarning ? (
    <AlertTriangle size={18} />
  ) : (
    <Info size={18} />
  );

  return (
    <div className={containerClass}>
      <div style={{ flexShrink: 0, marginTop: 1 }}>{icon}</div>
      <div style={{ flex: 1 }}>
        {title && <strong style={{ display: 'block', marginBottom: 2 }}>{title}</strong>}
        <div>{message}</div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', opacity: 0.7 }}
        >
          ×
        </button>
      )}
    </div>
  );
};

export const ErrorMessage: React.FC<{ error: string | null | undefined; onDismiss?: () => void }> = ({
  error,
  onDismiss,
}) => {
  if (!error) return null;
  return <MessageBanner type="error" message={error} onDismiss={onDismiss} />;
};

// Empty State
export const EmptyState: React.FC<{
  title?: string;
  message?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}> = ({
  title = 'No Data Available',
  message = 'No records returned from backend API.',
  action,
  icon = <Inbox size={32} />,
}) => {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
        {title}
      </h4>
      <p className="empty-state-text" style={{ marginBottom: action ? 16 : 0 }}>
        {message}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
};

// Page Header
export const PageHeader: React.FC<{
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}> = ({ title, subtitle, badge, actions }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 16 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h1 style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            {title}
          </h1>
          {badge}
        </div>
        {subtitle && (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 4 }}>
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{actions}</div>}
    </div>
  );
};

// Data Table
export interface Column<T> {
  header: string;
  accessor?: keyof T | ((row: T) => React.ReactNode);
  render?: (row: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T, index: number) => string | number;
  emptyMessage?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = 'No data available',
}: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} className={col.className}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={keyExtractor(row, rowIndex)}>
              {columns.map((col, colIndex) => {
                let cellContent: React.ReactNode = null;
                if (col.render) {
                  cellContent = col.render(row);
                } else if (typeof col.accessor === 'function') {
                  cellContent = col.accessor(row);
                } else if (col.accessor) {
                  cellContent = (row[col.accessor] as any)?.toString() ?? '—';
                }
                return (
                  <td key={colIndex} className={col.className}>
                    {cellContent}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Modal
export const Modal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}> = ({ isOpen, onClose, title, children, footer }) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(41, 37, 31, 0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 999,
        padding: 20,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-main)',
          boxShadow: 'var(--shadow-lg)',
          maxWidth: 520,
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: '20px', overflowY: 'auto' }}>{children}</div>
        {footer && (
          <div
            style={{
              padding: '12px 20px',
              borderTop: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-secondary)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 8,
              borderBottomLeftRadius: 'var(--radius-md)',
              borderBottomRightRadius: 'var(--radius-md)',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
