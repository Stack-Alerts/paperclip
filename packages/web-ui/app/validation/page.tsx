'use client';

import { ValidationReportWindow } from '@/components/strategy-builder/ValidationReportWindow';

export default function ValidationPage() {
  return (
    <ValidationReportWindow
      open
      standalone
      onClose={() => {
        if (typeof window !== 'undefined' && window.opener) {
          window.close();
        } else {
          window.history.back();
        }
      }}
    />
  );
}
