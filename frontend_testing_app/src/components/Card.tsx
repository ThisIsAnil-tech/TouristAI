import React from 'react';

export interface CardProps {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  icon,
  children,
  className = '',
  style,
}) => {
  return (
    <div className={`card ${className}`} style={style}>
      {(title || subtitle || action) && (
        <div className="card-header">
          <div>
            {title && (
              <h3 className="card-title">
                {icon && <span>{icon}</span>}
                {title}
              </h3>
            )}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
