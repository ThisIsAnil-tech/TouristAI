import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  id,
  className = '',
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={inputId} className="form-label">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`form-input ${error ? 'border-danger' : ''} ${className}`}
        {...props}
      />
      {helperText && !error && (
        <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
          {helperText}
        </p>
      )}
      {error && (
        <p style={{ fontSize: '11.5px', color: 'var(--badge-danger-text)', marginTop: '4px' }}>
          {error}
        </p>
      )}
    </div>
  );
};

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options: Array<{ value: string | number; label: string }>;
}

export const Select: React.FC<SelectProps> = ({
  label,
  error,
  helperText,
  options,
  id,
  className = '',
  ...props
}) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={selectId} className="form-label">
          {label}
        </label>
      )}
      <select id={selectId} className={`form-select ${className}`} {...props}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {helperText && !error && (
        <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
          {helperText}
        </p>
      )}
      {error && (
        <p style={{ fontSize: '11.5px', color: 'var(--badge-danger-text)', marginTop: '4px' }}>
          {error}
        </p>
      )}
    </div>
  );
};
