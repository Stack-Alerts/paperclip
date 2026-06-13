import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  children?: React.ReactNode;
}

export const Select: React.FC<SelectProps> = ({ className,  children, ...props }) => (
  <select
    className={`w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:border-transparent disabled:cursor-not-allowed ${className || ''}`}
    style={{
      backgroundColor: 'var(--bg-input)',
      border: '1px solid var(--border-default)',
      color: 'var(--text-primary)',
    }}
    {...props}
  >
    {children}
  </select>
);
