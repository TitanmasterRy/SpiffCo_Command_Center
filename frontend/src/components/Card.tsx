import type { ReactNode } from 'react';

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

/** Standard raised panel used across all pages. */
export function Card({ title, children, className = '' }: CardProps) {
  return (
    <section
      className={`rounded-lg border border-surface-border bg-surface-raised p-4 ${className}`}
    >
      {title && (
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
