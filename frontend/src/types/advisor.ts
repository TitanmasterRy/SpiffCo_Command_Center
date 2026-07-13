/** Mirrors of backend/app/schemas/advisor.py (Phase 10 — AI advisor). */

import type { Severity } from './dashboard';

export type FindingCategory =
  | 'power'
  | 'machines'
  | 'production'
  | 'storage'
  | 'logistics'
  | 'uptime'
  | 'general';

export interface AdvisorFinding {
  id: string;
  severity: Severity;
  category: FindingCategory;
  title: string;
  explanation: string;
  suggestion: string;
}

export interface AdvisorReport {
  generated_at: string;
  source: 'simulation' | 'frm';
  findings: AdvisorFinding[];
  counts: Record<string, number>;
}
