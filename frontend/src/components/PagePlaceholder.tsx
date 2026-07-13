import { Card } from './Card';

interface PagePlaceholderProps {
  title: string;
  phase: string;
  description: string;
}

/** Stub body for pages whose functionality arrives in a later phase. */
export function PagePlaceholder({ title, phase, description }: PagePlaceholderProps) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-100">{title}</h1>
      <Card>
        <p className="text-sm text-slate-400">{description}</p>
        <p className="mt-2 text-xs font-medium uppercase tracking-widest text-accent">
          Arrives in {phase}
        </p>
      </Card>
    </div>
  );
}
