import type { ReactNode } from 'react';
import { Card } from './Card';

interface StatCardProps {
  title: string;
  value: string;
  detail?: string;
  children?: ReactNode;
}

/** Stat tile: one headline number with optional detail line and extra content. */
export function StatCard({ title, value, detail, children }: StatCardProps) {
  return (
    <Card title={title}>
      <div className="text-2xl font-semibold tabular-nums text-slate-100">{value}</div>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
      {children}
    </Card>
  );
}
