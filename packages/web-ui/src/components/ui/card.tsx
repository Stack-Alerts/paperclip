import React from 'react';

type CardProps = React.HTMLAttributes<HTMLDivElement>;
type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;
type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;
type CardContentProps = React.HTMLAttributes<HTMLDivElement>;

export const Card: React.FC<CardProps> = ({ className, style, ...props }) => (
  <div
    className={`rounded-lg shadow-sm ${className || ''}`}
    style={{
      background: 'var(--bg-panel)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 6,
      ...style,
    }}
    {...props}
  />
);

export const CardHeader: React.FC<CardHeaderProps> = ({ className, style, ...props }) => (
  <div
    className={`px-6 py-4 ${className || ''}`}
    style={{
      borderBottom: '1px solid var(--border-subtle)',
      ...style,
    }}
    {...props}
  />
);

export const CardTitle: React.FC<CardTitleProps> = ({ className, style, ...props }) => (
  <h3
    className={`text-lg font-semibold ${className || ''}`}
    style={{
      color: 'var(--text-primary)',
      ...style,
    }}
    {...props}
  />
);

export const CardContent: React.FC<CardContentProps> = ({ className, ...props }) => (
  <div className={`px-6 py-4 ${className || ''}`} {...props} />
);
