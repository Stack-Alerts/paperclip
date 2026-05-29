'use client';

import { ValidationReportWindow } from '@/components/strategy-builder/ValidationReportWindow';

export default function ValidationPage() {
  return <ValidationReportWindow open={true} onClose={() => window.history.back()} />;
}
