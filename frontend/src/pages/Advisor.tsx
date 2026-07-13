import { Card } from '../components/Card';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useAdvisor } from '../hooks/useAdvisor';
import type { AdvisorFinding } from '../types/advisor';
import type { Severity } from '../types/dashboard';
import { groupBySeverity } from '../utils/advisorView';

const SEVERITY_META: Record<Severity, { kind: StatusKind; label: string }> = {
  info: { kind: 'ok', label: 'Info' },
  warning: { kind: 'warn', label: 'Warning' },
  critical: { kind: 'error', label: 'Critical' },
};

const CATEGORY_ICON: Record<string, string> = {
  power: '⚡',
  machines: '🏭',
  production: '⚙',
  storage: '📦',
  logistics: '🚆',
  uptime: '📈',
  general: '✓',
};

function FindingCard({ finding }: { finding: AdvisorFinding }) {
  const meta = SEVERITY_META[finding.severity];
  return (
    <li className="rounded-lg border border-surface-border bg-surface-raised p-4">
      <div className="flex items-start gap-3">
        <span className="text-lg" aria-hidden>
          {CATEGORY_ICON[finding.category] ?? '•'}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-slate-100">{finding.title}</h3>
            <StatusBadge kind={meta.kind} label={meta.label} />
            <span className="text-[10px] uppercase tracking-widest text-slate-600">
              {finding.category}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">{finding.explanation}</p>
          <p className="mt-1 text-sm text-slate-300">
            <span className="text-slate-500">Suggested fix: </span>
            {finding.suggestion}
          </p>
        </div>
      </div>
    </li>
  );
}

/** AI Advisor (Phase 10): ranked, explained bottleneck/shortage findings. */
export default function Advisor() {
  const { data: report, isLoading } = useAdvisor();

  if (isLoading || !report) {
    return <p className="text-sm text-slate-500">Analyzing factory…</p>;
  }

  const groups = groupBySeverity(report.findings);
  const critical = report.counts.critical ?? 0;
  const warning = report.counts.warning ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Advisor</h1>
        <div className="flex items-center gap-2">
          {report.source === 'simulation' && (
            <StatusBadge kind="idle" label="Simulated — FRM arrives in Phase 11" />
          )}
          {critical > 0 && <StatusBadge kind="error" label={`${critical} critical`} />}
          {warning > 0 && <StatusBadge kind="warn" label={`${warning} warning`} />}
          {critical === 0 && warning === 0 && <StatusBadge kind="ok" label="All clear" />}
        </div>
      </div>

      {groups.map((group) => (
        <Card key={group.severity} title={`${SEVERITY_META[group.severity].label} (${group.findings.length})`}>
          <ul className="space-y-3">
            {group.findings.map((f) => (
              <FindingCard key={f.id} finding={f} />
            ))}
          </ul>
        </Card>
      ))}
    </div>
  );
}
