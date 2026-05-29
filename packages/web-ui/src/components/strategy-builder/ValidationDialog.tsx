'use client';

import React from 'react';
import { ValidationReportWindow } from './ValidationReportWindow';

export interface ValidationDialogProps {
  open: boolean;
  onClose: () => void;
}

export const ValidationDialog: React.FC<ValidationDialogProps> = ({ open, onClose }) => {
  return <ValidationReportWindow open={open} onClose={onClose} />;
};

export default ValidationDialog;
