import type { ReactNode } from "react";

interface PageHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  /** Small chip next to the title, e.g. a role or scope badge. */
  badge?: ReactNode;
  /** Right-side slot: account/status badges or action buttons. Stacks below on mobile. */
  actions?: ReactNode;
  className?: string;
}

/**
 * Standard workspace page header card: title + optional badge and subtitle on
 * the left, actions/status on the right, stacking vertically on phones.
 */
export function PageHeader({ title, subtitle, badge, actions, className = "" }: PageHeaderProps) {
  return (
    <header className={`rounded-2xl border border-border bg-surface px-4 py-4 shadow-card sm:px-5 ${className}`}>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h1 className="font-display min-w-0 break-words text-lg font-black leading-tight text-foreground sm:text-xl">
              {title}
            </h1>
            {badge}
          </div>
          {subtitle ? (
            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}
