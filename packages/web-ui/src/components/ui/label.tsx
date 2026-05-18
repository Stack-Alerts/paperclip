import React from 'react';

type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;

export const Label: React.FC<LabelProps> = ({ className, style, ...props }) => (
  <label
    className={`block text-sm font-medium mb-1 ${className || ''}`}
    style={{
      color: 'var(--text-primary)',
      ...style,
    }}
    {...props}
  />
);
