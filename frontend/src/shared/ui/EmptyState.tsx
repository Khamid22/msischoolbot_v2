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
    <section className={`rounded-lg border border-dashed border-border/90 bg-card/80 px-4 py-9 text-center shadow-sm ${className}`}>
      {icon ? (
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground shadow-sm">
          {icon}
        </div>
      ) : null}
      <h2 className="mx-auto mt-4 max-w-lg text-balance break-words text-base font-black text-foreground">{title}</h2>
      {detail ? <p className="mx-auto mt-2 max-w-md text-pretty text-sm leading-6 text-muted-foreground">{detail}</p> : null}
      {action ? <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div> : null}
    </section>
  );
}
