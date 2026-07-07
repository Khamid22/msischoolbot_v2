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
    <header className={`rounded-lg border border-border/80 bg-card/95 px-4 py-4 shadow-card sm:px-5 ${className}`}>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h1 className="font-display min-w-0 text-balance break-words text-lg font-black leading-tight text-foreground sm:text-xl">
              {title}
            </h1>
            {badge}
          </div>
          {subtitle ? (
            <p className="mt-1.5 max-w-3xl text-pretty text-sm leading-6 text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2 md:justify-end">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
