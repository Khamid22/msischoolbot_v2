import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  detail?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ title, detail, icon, action, className = "" }: EmptyStateProps) {
  return (
    <section className={`rounded-xl border border-dashed border-border bg-surface px-4 py-8 text-center shadow-sm ${className}`}>
      {icon ? <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-muted-foreground">{icon}</div> : null}
      <h2 className="mt-4 text-base font-black text-foreground">{title}</h2>
      {detail ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{detail}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </section>
  );
}
