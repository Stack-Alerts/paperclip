import React from 'react';

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input: React.FC<InputProps> = ({ className, style, ...props }) => (
  <input
    className={`w-full px-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:border-transparent disabled:cursor-not-allowed ${className || ''}`}
    style={{
      backgroundColor: 'var(--bg-input)',
      border: '1px solid var(--border-default)',
      color: 'var(--text-primary)',
    }}
    {...props}
  />
);
