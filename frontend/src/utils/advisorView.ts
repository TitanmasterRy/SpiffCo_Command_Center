import type { AdvisorFinding } from '../types/advisor';
import type { Severity } from '../types/dashboard';

/** Severities in display order (most urgent first). */
export const SEVERITY_ORDER: Severity[] = ['critical', 'warning', 'info'];

export interface SeverityGroup {
  severity: Severity;
  findings: AdvisorFinding[];
}

/**
 * Group findings by severity in urgency order, omitting empty groups. Preserves
 * the server's within-severity ordering.
 */
export function groupBySeverity(findings: AdvisorFinding[]): SeverityGroup[] {
  return SEVERITY_ORDER.map((severity) => ({
    severity,
    findings: findings.filter((f) => f.severity === severity),
  })).filter((group) => group.findings.length > 0);
}
