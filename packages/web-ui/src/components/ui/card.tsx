import React from 'react';

type CardProps = React.HTMLAttributes<HTMLDivElement>;
type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;
type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;
type CardContentProps = React.HTMLAttributes<HTMLDivElement>;

export const Card: React.FC<CardProps> = ({ className, ...props }) => (
  <div
    className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className || ''}`}
    {...props}
  />
);

export const CardHeader: React.FC<CardHeaderProps> = ({ className, ...props }) => (
  <div className={`border-b border-gray-200 px-6 py-4 ${className || ''}`} {...props} />
);

export const CardTitle: React.FC<CardTitleProps> = ({ className, ...props }) => (
  <h3 className={`text-lg font-semibold text-gray-900 ${className || ''}`} {...props} />
);

export const CardContent: React.FC<CardContentProps> = ({ className, ...props }) => (
  <div className={`px-6 py-4 ${className || ''}`} {...props} />
);
