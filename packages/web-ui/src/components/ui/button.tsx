import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  className,
  variant = 'default',
  size = 'md',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      backgroundColor: 'var(--accent-blue)',
      color: 'white',
    },
    destructive: {
      backgroundColor: 'transparent',
      color: 'var(--color-bearish)',
      border: '1px solid var(--color-bearish)',
    },
    secondary: {
      backgroundColor: 'var(--bg-panel)',
      color: 'var(--text-secondary)',
      border: '1px solid var(--border-default)',
    },
    ghost: {
      backgroundColor: 'transparent',
      color: 'var(--text-secondary)',
      border: '1px solid var(--border-default)',
    },
  };

  const sizeStyles = {
    sm: 'px-2 py-1 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${className || ''}`}
      style={variantStyles[variant]}
      {...props}
    />
  );
};
