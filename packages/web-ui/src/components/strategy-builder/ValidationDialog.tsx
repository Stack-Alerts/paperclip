'use client';

import React from 'react';
import { ValidationReportWindow } from './ValidationReportWindow';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

export interface ValidationDialogProps {
  open: boolean;
  onClose: () => void;
}

export const ValidationDialog: React.FC<ValidationDialogProps> = ({ open, onClose }) => {
  const validationReport = useStrategyStore((state) => state.validationReport);

  return <ValidationReportWindow open={open} onClose={onClose} report={validationReport ?? undefined} />;
};

export default ValidationDialog;
